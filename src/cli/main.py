"""CLI interface for PL Generator."""
import sys
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

try:
    import typer
    app = typer.Typer(help="PL Generator - Auto-generate P&L Excel from business plans")
    eval_app = typer.Typer(help="Reference evaluation workflows")
    source_cache_app = typer.Typer(help="Manage the FAM source cache")
    app.add_typer(eval_app, name="eval")
    eval_app.add_typer(source_cache_app, name="source-cache")
except ImportError:
    # Fallback: we'll use argparse
    app = None
    eval_app = None
    source_cache_app = None

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fam_reference_eval(
    plan_pdf: str,
    reference_workbook: str,
    artifact_root: str = "artifacts/fam-eval",
    runner: str = "fixture",
) -> dict:
    """Run the FAM reference-driven PDCA evaluation loop."""
    from ..evals.pdca_loop import run_reference_pdca

    result = run_reference_pdca(
        plan_pdf=Path(plan_pdf),
        reference_workbook=Path(reference_workbook),
        artifact_root=Path(artifact_root),
        runner=runner,
    )
    run_root = Path(artifact_root) / result.run_id

    return {
        "run_id": result.run_id,
        "baseline_score": result.baseline_score,
        "best_candidate_id": result.best_candidate_id,
        "best_candidate_score": result.best_candidate_score,
        "summary_path": str(run_root / "summary.md"),
        "scores_path": str(run_root / "scores.json"),
    }


def source_cache_show(registry_path: Optional[str] = None) -> dict:
    """Show source-cache metadata."""
    from ..evals.source_registry import source_registry_metadata

    return source_registry_metadata(Path(registry_path) if registry_path else None)


def source_cache_upsert(
    source_type: str,
    title: str,
    url: str,
    publisher: str,
    quote: str,
    registry_path: Optional[str] = None,
) -> dict:
    """Insert or update one source-cache entry."""
    from ..evals.source_registry import upsert_analysis_source_ref

    updated = upsert_analysis_source_ref(
        source_type,
        title=title,
        url=url,
        publisher=publisher,
        quote=quote,
        registry_path=Path(registry_path) if registry_path else None,
    )
    return {
        "source_type": source_type,
        "updated_ref": updated,
        "registry_path": str(Path(registry_path)) if registry_path else None,
    }

_PDCA_PHASE_DEFAULTS = {
    5: {
        "provider": "anthropic",
        "model": "claude-sonnet-4-5-20250929",
        "system_key": "param_extractor_system",
        "user_key": "param_extractor_user",
    },
}


def _load_config(config_path: Optional[str] = None) -> dict:
    """Load configuration from YAML or JSON file."""
    if config_path is None:
        return {}
    path = Path(config_path)
    if path.suffix in ('.yaml', '.yml'):
        try:
            import yaml
            with open(path) as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            logger.warning("PyYAML not installed, trying JSON")
    with open(path) as f:
        return json.load(f)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _pdca_artifact_root(artifact_root: Optional[str] = None) -> Path:
    root = artifact_root or os.environ.get("PLGEN_PDCA_ARTIFACT_ROOT") or "artifacts/llm-pdca"
    return Path(root)


def _pdca_defaults(phase: int) -> dict:
    if phase not in _PDCA_PHASE_DEFAULTS:
        raise ValueError(f"Unsupported PDCA phase: {phase}")
    return _PDCA_PHASE_DEFAULTS[phase]


def _load_json_file(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_text_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def analyze(
    input_file: str,
    template: str = "templates/base.xlsx",
    config: Optional[str] = None,
    output_dir: str = "output",
    industry: str = "SaaS",
    business_model: str = "B2B",
    strictness: str = "normal",
):
    """Analyze a business plan and generate analysis report (Phase A+B)."""
    from ..config.models import PhaseAConfig, ColorConfig
    from ..ingest.reader import read_document
    from ..catalog.scanner import scan_template, export_catalog_json
    from ..modelmap.analyzer import analyze_model, generate_model_report_md
    from ..extract.extractor import ParameterExtractor
    from ..extract.llm_client import LLMClient

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Load config
    cfg_data = _load_config(config)
    phase_a = PhaseAConfig(
        industry=cfg_data.get("industry", industry),
        business_model=cfg_data.get("business_model", business_model),
        strictness=cfg_data.get("strictness", strictness),
        cases=cfg_data.get("cases", ["base", "worst"]),
        simulation=cfg_data.get("simulation", False),
        colors=ColorConfig(**cfg_data.get("colors", {})),
    )

    print(f"[1/4] Reading document: {input_file}")
    document = read_document(input_file)
    print(f"  → {document.total_pages} pages extracted")

    print(f"[2/4] Scanning template: {template}")
    catalog = scan_template(template, phase_a.colors.input_color)
    export_catalog_json(catalog, str(out / "input_catalog.json"))
    print(f"  → {len(catalog.items)} input cells found")

    print(f"[3/4] Analyzing model structure...")
    report = analyze_model(template, catalog)
    report_md = generate_model_report_md(report)
    with open(out / "analysis_report.md", "w", encoding="utf-8") as f:
        f.write(report_md)
    print(f"  → Model report generated")

    print(f"[4/4] Extracting parameters from document...")
    extractor = ParameterExtractor(phase_a)
    parameters = extractor.extract_parameters(document, catalog)

    # Save extraction results
    params_data = []
    for p in parameters:
        params_data.append({
            "key": p.key,
            "label": p.label,
            "value": p.value,
            "unit": p.unit,
            "confidence": p.confidence,
            "source": p.source,
            "evidence": {
                "quote": p.evidence.quote,
                "page_or_slide": p.evidence.page_or_slide,
                "rationale": p.evidence.rationale,
            },
            "mapped_targets": [{"sheet": t.sheet, "cell": t.cell} for t in p.mapped_targets],
        })

    with open(out / "extraction_log.json", "w", encoding="utf-8") as f:
        json.dump(params_data, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Analysis complete! Output saved to {output_dir}/")
    print(f"  - input_catalog.json")
    print(f"  - analysis_report.md")
    print(f"  - extraction_log.json")
    print(f"  - {len(parameters)} parameters extracted")

    return parameters, report, catalog


def generate(
    input_file: str,
    template: str = "templates/base.xlsx",
    config: Optional[str] = None,
    output_dir: str = "output",
    cases: str = "base,worst",
    industry: str = "SaaS",
    business_model: str = "B2B",
    strictness: str = "normal",
    simulation: bool = False,
):
    """Generate PL Excel files from a business plan (Phase A+B+C without interactive customization)."""
    from ..config.models import PhaseAConfig, ColorConfig
    from ..excel.writer import PLWriter
    from ..excel.validator import PLValidator, generate_needs_review_csv
    from ..excel.case_generator import CaseGenerator
    from ..simulation.engine import SimulationEngine, export_simulation_summary

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Parse cases
    case_list = [c.strip() for c in cases.split(",")]

    cfg_data = _load_config(config)
    phase_a = PhaseAConfig(
        industry=cfg_data.get("industry", industry),
        business_model=cfg_data.get("business_model", business_model),
        strictness=cfg_data.get("strictness", strictness),
        cases=case_list,
        simulation=cfg_data.get("simulation", simulation),
        colors=ColorConfig(**cfg_data.get("colors", {})),
    )

    # Run analysis first
    parameters, report, catalog = analyze(
        input_file, template, config, output_dir, industry, business_model, strictness
    )

    # Generate cases
    print(f"\n[Generating] Creating case variants: {case_list}")
    case_gen = CaseGenerator(phase_a)
    case_params = case_gen.generate_cases(parameters)

    # Write diff report
    diff_report = case_gen.get_case_diff_report(case_params)
    with open(out / "case_diff_report.md", "w", encoding="utf-8") as f:
        f.write(diff_report)

    generated_files = []
    for case_name, case_parameters in case_params.items():
        # Determine template for this case
        case_template = template
        case_specific = Path(f"templates/{case_name}.xlsx")
        if case_specific.exists():
            case_template = str(case_specific)

        output_file = str(out / f"PL_{case_name}.xlsx")
        print(f"  → Generating {case_name} case: {output_file}")

        writer = PLWriter(case_template, output_file, phase_a)
        writer.generate(case_parameters)

        # Validate
        validator = PLValidator(case_template, output_file, phase_a.colors.input_color)
        result = validator.validate()

        if result.passed:
            print(f"    ✓ Validation passed ({len(result.changed_cells)} cells changed)")
        else:
            print(f"    ✗ Validation issues: {len(result.errors_found)} errors")
            for err in result.errors_found[:5]:
                print(f"      - {err}")

        generated_files.append(output_file)

    # Generate needs_review.csv
    generate_needs_review_csv(parameters, str(out / "needs_review.csv"))

    # Simulation
    if phase_a.simulation:
        print(f"\n[Simulation] Running Monte Carlo simulation...")
        sim_engine = SimulationEngine(iterations=500)
        sim_result = sim_engine.run(parameters, template_path=template)
        export_simulation_summary(sim_result, str(out / "simulation_summary.xlsx"))
        print(f"  → Simulation summary saved")

    print(f"\n✓ Generation complete!")
    print(f"  Generated files:")
    for f in generated_files:
        print(f"    - {f}")
    print(f"    - needs_review.csv")
    if phase_a.simulation:
        print(f"    - simulation_summary.xlsx")


def pdca_campaign_create(
    *,
    artifact_root: Optional[str],
    campaign_id: str,
    name: str,
    phase: int,
    goal: str = "",
) -> str:
    from ..pdca.models import Campaign
    from ..pdca.storage import create_campaign

    root = _pdca_artifact_root(artifact_root)
    campaign = Campaign(
        campaign_id=campaign_id,
        name=name,
        target_phase=phase,
        goal=goal,
    )
    path = create_campaign(root, campaign) / "campaign.json"
    return str(path)


def pdca_campaign_list(*, artifact_root: Optional[str]) -> list[str]:
    from ..pdca.storage import list_campaigns

    root = _pdca_artifact_root(artifact_root)
    return [
        f"{campaign.campaign_id}\tphase={campaign.target_phase}\tstatus={campaign.status}\t{campaign.name}"
        for campaign in list_campaigns(root)
    ]


def pdca_init(
    *,
    artifact_root: Optional[str],
    experiment_id: str,
    campaign_id: str,
    phase: int,
    hypothesis: str,
    baseline_source: str = "default",
    parent_experiment_id: Optional[str] = None,
    project_id: Optional[str] = None,
    document_hash: Optional[str] = None,
    filename: str = "",
) -> str:
    from ..pdca.models import ExperimentManifest, InputDocumentRef, LLMConfigSnapshot, PromptPairInfo
    from ..pdca.storage import create_experiment, load_campaign

    root = _pdca_artifact_root(artifact_root)
    load_campaign(root, campaign_id)
    defaults = _pdca_defaults(phase)
    manifest = ExperimentManifest(
        experiment_id=experiment_id,
        campaign_id=campaign_id,
        parent_experiment_id=parent_experiment_id,
        baseline_source=baseline_source,
        target_phase=phase,
        hypothesis=hypothesis,
        llm_config=LLMConfigSnapshot(
            provider=defaults["provider"],
            model=defaults["model"],
            temperature=0.1,
            max_tokens=32768,
        ),
        prompt_pair=PromptPairInfo(
            system_key=defaults["system_key"],
            user_key=defaults["user_key"],
            changed="system",
        ),
        input_document=InputDocumentRef(
            project_id=project_id,
            document_hash=document_hash,
            filename=filename,
        ),
    )
    create_experiment(
        root,
        manifest,
        hypothesis_markdown=f"# Hypothesis\n\n{hypothesis}\n",
    )
    return str(root / "experiments" / experiment_id / "manifest.json")


def pdca_list(
    *,
    artifact_root: Optional[str],
    status: Optional[str] = None,
    campaign_id: Optional[str] = None,
) -> list[str]:
    from ..pdca.storage import list_experiments

    root = _pdca_artifact_root(artifact_root)
    experiments = list_experiments(root, status=status, campaign_id=campaign_id)
    return [
        f"{manifest.experiment_id}\tphase={manifest.target_phase}\tstatus={manifest.status}\tdecision={manifest.decision or '-'}"
        for manifest in experiments
    ]


def pdca_show(*, artifact_root: Optional[str], experiment_id: str) -> str:
    from ..pdca.storage import load_experiment_manifest

    root = _pdca_artifact_root(artifact_root)
    manifest = load_experiment_manifest(root, experiment_id)
    return json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2)


def pdca_snapshot(
    *,
    artifact_root: Optional[str],
    experiment_id: str,
    baseline_system_file: str,
    baseline_user_file: str,
    candidate_system_file: str,
    candidate_user_file: str,
    context_file: Optional[str] = None,
) -> str:
    from ..pdca.importer import save_prompt_snapshots
    from ..pdca.models import PromptSnapshot
    from ..pdca.storage import load_experiment_manifest, save_experiment_manifest

    root = _pdca_artifact_root(artifact_root)
    manifest = load_experiment_manifest(root, experiment_id)
    prompt_key = f"{manifest.prompt_pair.system_key}|{manifest.prompt_pair.user_key}"
    inputs_dir = save_prompt_snapshots(
        root,
        experiment_id,
        baseline=PromptSnapshot(
            system_prompt=_load_text_file(baseline_system_file),
            user_prompt=_load_text_file(baseline_user_file),
            prompt_key=prompt_key,
            source="baseline_file",
        ),
        candidate=PromptSnapshot(
            system_prompt=_load_text_file(candidate_system_file),
            user_prompt=_load_text_file(candidate_user_file),
            prompt_key=prompt_key,
            source="candidate_file",
        ),
        context=_load_json_file(context_file) if context_file else None,
    )
    save_experiment_manifest(root, manifest.model_copy(update={"status": "ready"}))
    return str(inputs_dir / "candidate_prompt_snapshot.json")


def pdca_import_output_command(
    *,
    artifact_root: Optional[str],
    experiment_id: str,
    role: str,
    payload_file: str,
    meta_file: Optional[str] = None,
) -> str:
    from ..pdca.importer import import_output
    from ..pdca.models import ImportedOutputMeta
    from ..pdca.storage import load_experiment_manifest, save_experiment_manifest

    root = _pdca_artifact_root(artifact_root)
    meta = None
    if meta_file:
        meta = ImportedOutputMeta.model_validate(_load_json_file(meta_file))
    outputs_dir = import_output(
        root,
        experiment_id,
        role=role,
        payload=_load_json_file(payload_file),
        meta=meta,
    )
    manifest = load_experiment_manifest(root, experiment_id)
    save_experiment_manifest(root, manifest.model_copy(update={"status": "imported"}))
    return str(outputs_dir / f"{role}_output.json")


def pdca_compare_command(
    *,
    artifact_root: Optional[str],
    experiment_id: str,
    phase: Optional[int] = None,
) -> str:
    from ..pdca.compare import compare_experiment
    from ..pdca.storage import load_experiment_manifest, save_experiment_manifest

    root = _pdca_artifact_root(artifact_root)
    manifest = load_experiment_manifest(root, experiment_id)
    compare_experiment(root, experiment_id, phase=phase or manifest.target_phase)
    save_experiment_manifest(root, manifest.model_copy(update={"status": "compared"}))
    return str(root / "experiments" / experiment_id / "compare" / "summary.json")


def pdca_report_command(
    *,
    artifact_root: Optional[str],
    experiment_id: str,
) -> str:
    from ..pdca.report import write_report
    from ..pdca.storage import load_experiment_manifest, save_experiment_manifest

    root = _pdca_artifact_root(artifact_root)
    path = write_report(root, experiment_id)
    manifest = load_experiment_manifest(root, experiment_id)
    save_experiment_manifest(root, manifest.model_copy(update={"status": "reported"}))
    return str(path)


def pdca_promote(
    *,
    artifact_root: Optional[str],
    experiment_id: str,
    decision: str,
    reason: str = "",
) -> str:
    from ..pdca.storage import load_experiment_manifest, save_experiment_manifest

    root = _pdca_artifact_root(artifact_root)
    manifest = load_experiment_manifest(root, experiment_id)
    updated = manifest.model_copy(
        update={
            "status": "completed",
            "decision": decision,
            "decision_reason": reason or manifest.decision_reason,
            "completed_at": _now_iso(),
        }
    )
    path = save_experiment_manifest(root, updated)
    return str(path)


if app is not None:
    # Typer CLI
    @app.command()
    def cli_analyze(
        input_file: str = typer.Argument(..., help="Path to business plan (PDF/DOCX/PPTX)"),
        template: str = typer.Option("templates/base.xlsx", help="Path to Excel template"),
        config: Optional[str] = typer.Option(None, help="Path to config YAML/JSON"),
        output_dir: str = typer.Option("output", "--out", help="Output directory"),
        industry: str = typer.Option("SaaS", help="Industry type"),
        business_model: str = typer.Option("B2B", help="Business model"),
        strictness: str = typer.Option("normal", help="Strictness mode (strict/normal)"),
    ):
        """Analyze a business plan and generate analysis report."""
        analyze(input_file, template, config, output_dir, industry, business_model, strictness)

    @app.command()
    def cli_generate(
        input_file: str = typer.Argument(..., help="Path to business plan (PDF/DOCX/PPTX)"),
        template: str = typer.Option("templates/base.xlsx", help="Path to Excel template"),
        config: Optional[str] = typer.Option(None, help="Path to config YAML/JSON"),
        output_dir: str = typer.Option("output", "--out", help="Output directory"),
        cases: str = typer.Option("base,worst", help="Cases to generate (comma-separated)"),
        industry: str = typer.Option("SaaS", help="Industry type"),
        business_model: str = typer.Option("B2B", help="Business model"),
        strictness: str = typer.Option("normal", help="Strictness mode"),
        simulation: bool = typer.Option(False, "--simulation", help="Enable simulation"),
    ):
        """Generate PL Excel files from a business plan."""
        generate(input_file, template, config, output_dir, cases, industry, business_model, strictness, simulation)

    @eval_app.command("fam-reference")
    def cli_fam_reference(
        plan_pdf: str = typer.Option(..., help="Business plan PDF"),
        reference_workbook: str = typer.Option(..., help="Reference workbook (.xlsx)"),
        artifact_root: str = typer.Option("artifacts/fam-eval", help="Artifact output directory"),
        runner: str = typer.Option("fixture", help="fixture or live"),
    ):
        """Run the FAM reference evaluation loop."""
        payload = fam_reference_eval(plan_pdf, reference_workbook, artifact_root, runner)
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    @source_cache_app.command("show")
    def cli_source_cache_show(
        registry_path: Optional[str] = typer.Option(None, help="Override source cache JSON path"),
    ):
        """Show source-cache metadata."""
        payload = source_cache_show(registry_path)
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    @source_cache_app.command("upsert")
    def cli_source_cache_upsert(
        source_type: str = typer.Option(..., help="Analysis source type"),
        title: str = typer.Option(..., help="Source title"),
        url: str = typer.Option(..., help="Source URL"),
        publisher: str = typer.Option(..., help="Source publisher"),
        quote: str = typer.Option(..., help="Curated short quote"),
        registry_path: Optional[str] = typer.Option(None, help="Override source cache JSON path"),
    ):
        """Insert or update one source-cache entry."""
        payload = source_cache_upsert(source_type, title, url, publisher, quote, registry_path)
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    pdca_app = typer.Typer(help="LLM improvement PDCA tools")
    pdca_campaign_app = typer.Typer(help="Manage PDCA campaigns")
    pdca_app.add_typer(pdca_campaign_app, name="campaign")
    app.add_typer(pdca_app, name="pdca")

    @pdca_campaign_app.command("create")
    def cli_pdca_campaign_create(
        campaign_id: str = typer.Option(..., help="Campaign ID"),
        name: str = typer.Option(..., help="Campaign name"),
        phase: int = typer.Option(..., help="Target phase"),
        goal: str = typer.Option("", help="Campaign goal"),
        artifact_root: Optional[str] = typer.Option(None, help="Artifact root override"),
    ):
        print(pdca_campaign_create(
            artifact_root=artifact_root,
            campaign_id=campaign_id,
            name=name,
            phase=phase,
            goal=goal,
        ))

    @pdca_campaign_app.command("list")
    def cli_pdca_campaign_list(
        artifact_root: Optional[str] = typer.Option(None, help="Artifact root override"),
    ):
        for line in pdca_campaign_list(artifact_root=artifact_root):
            print(line)

    @pdca_app.command("init")
    def cli_pdca_init(
        experiment_id: str = typer.Option(..., help="Experiment ID"),
        campaign_id: str = typer.Option(..., help="Campaign ID"),
        phase: int = typer.Option(..., help="Target phase"),
        hypothesis: str = typer.Option(..., help="Hypothesis text"),
        baseline_source: str = typer.Option("default", help="Baseline source"),
        parent_experiment_id: Optional[str] = typer.Option(None, help="Parent experiment"),
        project_id: Optional[str] = typer.Option(None, help="Project ID"),
        document_hash: Optional[str] = typer.Option(None, help="Document hash"),
        filename: str = typer.Option("", help="Document filename"),
        artifact_root: Optional[str] = typer.Option(None, help="Artifact root override"),
    ):
        print(pdca_init(
            artifact_root=artifact_root,
            experiment_id=experiment_id,
            campaign_id=campaign_id,
            phase=phase,
            hypothesis=hypothesis,
            baseline_source=baseline_source,
            parent_experiment_id=parent_experiment_id,
            project_id=project_id,
            document_hash=document_hash,
            filename=filename,
        ))

    @pdca_app.command("list")
    def cli_pdca_list(
        artifact_root: Optional[str] = typer.Option(None, help="Artifact root override"),
        status: Optional[str] = typer.Option(None, help="Status filter"),
        campaign_id: Optional[str] = typer.Option(None, help="Campaign filter"),
    ):
        for line in pdca_list(artifact_root=artifact_root, status=status, campaign_id=campaign_id):
            print(line)

    @pdca_app.command("show")
    def cli_pdca_show(
        experiment_id: str = typer.Option(..., help="Experiment ID"),
        artifact_root: Optional[str] = typer.Option(None, help="Artifact root override"),
    ):
        print(pdca_show(artifact_root=artifact_root, experiment_id=experiment_id))

    @pdca_app.command("snapshot")
    def cli_pdca_snapshot(
        experiment_id: str = typer.Option(..., help="Experiment ID"),
        baseline_system_file: str = typer.Option(..., help="Baseline system prompt file"),
        baseline_user_file: str = typer.Option(..., help="Baseline user prompt file"),
        candidate_system_file: str = typer.Option(..., help="Candidate system prompt file"),
        candidate_user_file: str = typer.Option(..., help="Candidate user prompt file"),
        context_file: Optional[str] = typer.Option(None, help="Context JSON file"),
        artifact_root: Optional[str] = typer.Option(None, help="Artifact root override"),
    ):
        print(pdca_snapshot(
            artifact_root=artifact_root,
            experiment_id=experiment_id,
            baseline_system_file=baseline_system_file,
            baseline_user_file=baseline_user_file,
            candidate_system_file=candidate_system_file,
            candidate_user_file=candidate_user_file,
            context_file=context_file,
        ))

    @pdca_app.command("import-output")
    def cli_pdca_import_output(
        experiment_id: str = typer.Option(..., help="Experiment ID"),
        role: str = typer.Option(..., help="baseline or candidate"),
        payload_file: str = typer.Option(..., help="Output JSON file"),
        meta_file: Optional[str] = typer.Option(None, help="Optional metadata JSON file"),
        artifact_root: Optional[str] = typer.Option(None, help="Artifact root override"),
    ):
        print(pdca_import_output_command(
            artifact_root=artifact_root,
            experiment_id=experiment_id,
            role=role,
            payload_file=payload_file,
            meta_file=meta_file,
        ))

    @pdca_app.command("compare")
    def cli_pdca_compare(
        experiment_id: str = typer.Option(..., help="Experiment ID"),
        phase: Optional[int] = typer.Option(None, help="Phase override"),
        artifact_root: Optional[str] = typer.Option(None, help="Artifact root override"),
    ):
        print(pdca_compare_command(
            artifact_root=artifact_root,
            experiment_id=experiment_id,
            phase=phase,
        ))

    @pdca_app.command("report")
    def cli_pdca_report(
        experiment_id: str = typer.Option(..., help="Experiment ID"),
        artifact_root: Optional[str] = typer.Option(None, help="Artifact root override"),
    ):
        print(pdca_report_command(
            artifact_root=artifact_root,
            experiment_id=experiment_id,
        ))

    @pdca_app.command("promote")
    def cli_pdca_promote(
        experiment_id: str = typer.Option(..., help="Experiment ID"),
        decision: str = typer.Option(..., help="adopted, rejected, or hold"),
        reason: str = typer.Option("", help="Decision reason"),
        artifact_root: Optional[str] = typer.Option(None, help="Artifact root override"),
    ):
        print(pdca_promote(
            artifact_root=artifact_root,
            experiment_id=experiment_id,
            decision=decision,
            reason=reason,
        ))


def main():
    """Entry point."""
    if app is not None:
        app()
    else:
        # Argparse fallback
        import argparse
        parser = argparse.ArgumentParser(description="PL Generator")
        sub = parser.add_subparsers(dest="command")

        analyze_p = sub.add_parser("analyze", help="Analyze business plan")
        analyze_p.add_argument("input_file", help="Business plan file")
        analyze_p.add_argument("--template", default="templates/base.xlsx")
        analyze_p.add_argument("--config", default=None)
        analyze_p.add_argument("--out", default="output")
        analyze_p.add_argument("--industry", default="SaaS")
        analyze_p.add_argument("--business-model", default="B2B")
        analyze_p.add_argument("--strictness", default="normal")

        gen_p = sub.add_parser("generate", help="Generate PL Excel")
        gen_p.add_argument("input_file", help="Business plan file")
        gen_p.add_argument("--template", default="templates/base.xlsx")
        gen_p.add_argument("--config", default=None)
        gen_p.add_argument("--out", default="output")
        gen_p.add_argument("--cases", default="base,worst")
        gen_p.add_argument("--industry", default="SaaS")
        gen_p.add_argument("--business-model", default="B2B")
        gen_p.add_argument("--strictness", default="normal")
        gen_p.add_argument("--simulation", action="store_true")

        eval_p = sub.add_parser("eval", help="Run reference evaluation workflows")
        eval_sub = eval_p.add_subparsers(dest="eval_command")
        fam_ref_p = eval_sub.add_parser("fam-reference", help="Run FAM reference evaluation")
        fam_ref_p.add_argument("--plan-pdf", required=True)
        fam_ref_p.add_argument("--reference-workbook", required=True)
        fam_ref_p.add_argument("--artifact-root", default="artifacts/fam-eval")
        fam_ref_p.add_argument("--runner", default="fixture")
        source_cache_p = eval_sub.add_parser("source-cache", help="Manage the FAM source cache")
        source_cache_sub = source_cache_p.add_subparsers(dest="source_cache_command")
        source_cache_show_p = source_cache_sub.add_parser("show", help="Show source-cache metadata")
        source_cache_show_p.add_argument("--registry-path", default=None)
        source_cache_upsert_p = source_cache_sub.add_parser("upsert", help="Insert or update one source-cache entry")
        source_cache_upsert_p.add_argument("--source-type", required=True)
        source_cache_upsert_p.add_argument("--title", required=True)
        source_cache_upsert_p.add_argument("--url", required=True)
        source_cache_upsert_p.add_argument("--publisher", required=True)
        source_cache_upsert_p.add_argument("--quote", required=True)
        source_cache_upsert_p.add_argument("--registry-path", default=None)

        pdca_p = sub.add_parser("pdca", help="LLM PDCA tools")
        pdca_sub = pdca_p.add_subparsers(dest="pdca_command")

        pdca_campaign_p = pdca_sub.add_parser("campaign", help="Campaign tools")
        pdca_campaign_sub = pdca_campaign_p.add_subparsers(dest="pdca_campaign_command")

        campaign_create_p = pdca_campaign_sub.add_parser("create", help="Create campaign")
        campaign_create_p.add_argument("--campaign-id", required=True)
        campaign_create_p.add_argument("--name", required=True)
        campaign_create_p.add_argument("--phase", required=True, type=int)
        campaign_create_p.add_argument("--goal", default="")
        campaign_create_p.add_argument("--artifact-root", default=None)

        campaign_list_p = pdca_campaign_sub.add_parser("list", help="List campaigns")
        campaign_list_p.add_argument("--artifact-root", default=None)

        pdca_init_p = pdca_sub.add_parser("init", help="Create experiment")
        pdca_init_p.add_argument("--experiment-id", required=True)
        pdca_init_p.add_argument("--campaign-id", required=True)
        pdca_init_p.add_argument("--phase", required=True, type=int)
        pdca_init_p.add_argument("--hypothesis", required=True)
        pdca_init_p.add_argument("--baseline-source", default="default")
        pdca_init_p.add_argument("--parent-experiment-id", default=None)
        pdca_init_p.add_argument("--project-id", default=None)
        pdca_init_p.add_argument("--document-hash", default=None)
        pdca_init_p.add_argument("--filename", default="")
        pdca_init_p.add_argument("--artifact-root", default=None)

        pdca_list_p = pdca_sub.add_parser("list", help="List experiments")
        pdca_list_p.add_argument("--status", default=None)
        pdca_list_p.add_argument("--campaign-id", default=None)
        pdca_list_p.add_argument("--artifact-root", default=None)

        pdca_show_p = pdca_sub.add_parser("show", help="Show experiment")
        pdca_show_p.add_argument("--experiment-id", required=True)
        pdca_show_p.add_argument("--artifact-root", default=None)

        pdca_snapshot_p = pdca_sub.add_parser("snapshot", help="Save prompt snapshots")
        pdca_snapshot_p.add_argument("--experiment-id", required=True)
        pdca_snapshot_p.add_argument("--baseline-system-file", required=True)
        pdca_snapshot_p.add_argument("--baseline-user-file", required=True)
        pdca_snapshot_p.add_argument("--candidate-system-file", required=True)
        pdca_snapshot_p.add_argument("--candidate-user-file", required=True)
        pdca_snapshot_p.add_argument("--context-file", default=None)
        pdca_snapshot_p.add_argument("--artifact-root", default=None)

        pdca_import_p = pdca_sub.add_parser("import-output", help="Import comparison output")
        pdca_import_p.add_argument("--experiment-id", required=True)
        pdca_import_p.add_argument("--role", required=True)
        pdca_import_p.add_argument("--payload-file", required=True)
        pdca_import_p.add_argument("--meta-file", default=None)
        pdca_import_p.add_argument("--artifact-root", default=None)

        pdca_compare_p = pdca_sub.add_parser("compare", help="Compare imported outputs")
        pdca_compare_p.add_argument("--experiment-id", required=True)
        pdca_compare_p.add_argument("--phase", default=None, type=int)
        pdca_compare_p.add_argument("--artifact-root", default=None)

        pdca_report_p = pdca_sub.add_parser("report", help="Write experiment report")
        pdca_report_p.add_argument("--experiment-id", required=True)
        pdca_report_p.add_argument("--artifact-root", default=None)

        pdca_promote_p = pdca_sub.add_parser("promote", help="Record experiment decision")
        pdca_promote_p.add_argument("--experiment-id", required=True)
        pdca_promote_p.add_argument("--decision", required=True)
        pdca_promote_p.add_argument("--reason", default="")
        pdca_promote_p.add_argument("--artifact-root", default=None)

        args = parser.parse_args()
        if args.command == "analyze":
            analyze(args.input_file, args.template, args.config, args.out, args.industry, args.business_model, args.strictness)
        elif args.command == "generate":
            generate(args.input_file, args.template, args.config, args.out, args.cases, args.industry, args.business_model, args.strictness, args.simulation)
        elif args.command == "eval" and args.eval_command == "fam-reference":
            payload = fam_reference_eval(args.plan_pdf, args.reference_workbook, args.artifact_root, args.runner)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        elif args.command == "eval" and args.eval_command == "source-cache" and args.source_cache_command == "show":
            payload = source_cache_show(args.registry_path)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        elif args.command == "eval" and args.eval_command == "source-cache" and args.source_cache_command == "upsert":
            payload = source_cache_upsert(
                args.source_type,
                args.title,
                args.url,
                args.publisher,
                args.quote,
                args.registry_path,
            )
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        elif args.command == "pdca":
            if args.pdca_command == "campaign":
                if args.pdca_campaign_command == "create":
                    print(pdca_campaign_create(
                        artifact_root=args.artifact_root,
                        campaign_id=args.campaign_id,
                        name=args.name,
                        phase=args.phase,
                        goal=args.goal,
                    ))
                elif args.pdca_campaign_command == "list":
                    for line in pdca_campaign_list(artifact_root=args.artifact_root):
                        print(line)
                else:
                    pdca_campaign_p.print_help()
            elif args.pdca_command == "init":
                print(pdca_init(
                    artifact_root=args.artifact_root,
                    experiment_id=args.experiment_id,
                    campaign_id=args.campaign_id,
                    phase=args.phase,
                    hypothesis=args.hypothesis,
                    baseline_source=args.baseline_source,
                    parent_experiment_id=args.parent_experiment_id,
                    project_id=args.project_id,
                    document_hash=args.document_hash,
                    filename=args.filename,
                ))
            elif args.pdca_command == "list":
                for line in pdca_list(
                    artifact_root=args.artifact_root,
                    status=args.status,
                    campaign_id=args.campaign_id,
                ):
                    print(line)
            elif args.pdca_command == "show":
                print(pdca_show(artifact_root=args.artifact_root, experiment_id=args.experiment_id))
            elif args.pdca_command == "snapshot":
                print(pdca_snapshot(
                    artifact_root=args.artifact_root,
                    experiment_id=args.experiment_id,
                    baseline_system_file=args.baseline_system_file,
                    baseline_user_file=args.baseline_user_file,
                    candidate_system_file=args.candidate_system_file,
                    candidate_user_file=args.candidate_user_file,
                    context_file=args.context_file,
                ))
            elif args.pdca_command == "import-output":
                print(pdca_import_output_command(
                    artifact_root=args.artifact_root,
                    experiment_id=args.experiment_id,
                    role=args.role,
                    payload_file=args.payload_file,
                    meta_file=args.meta_file,
                ))
            elif args.pdca_command == "compare":
                print(pdca_compare_command(
                    artifact_root=args.artifact_root,
                    experiment_id=args.experiment_id,
                    phase=args.phase,
                ))
            elif args.pdca_command == "report":
                print(pdca_report_command(
                    artifact_root=args.artifact_root,
                    experiment_id=args.experiment_id,
                ))
            elif args.pdca_command == "promote":
                print(pdca_promote(
                    artifact_root=args.artifact_root,
                    experiment_id=args.experiment_id,
                    decision=args.decision,
                    reason=args.reason,
                ))
            else:
                pdca_p.print_help()
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
