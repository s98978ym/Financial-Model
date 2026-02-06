"""CLI interface for PL Generator."""
import sys
import json
import logging
from pathlib import Path
from typing import Optional, List

try:
    import typer
    app = typer.Typer(help="PL Generator - Auto-generate P&L Excel from business plans")
except ImportError:
    # Fallback: we'll use argparse
    app = None

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


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

        args = parser.parse_args()
        if args.command == "analyze":
            analyze(args.input_file, args.template, args.config, args.out, args.industry, args.business_model, args.strictness)
        elif args.command == "generate":
            generate(args.input_file, args.template, args.config, args.out, args.cases, args.industry, args.business_model, args.strictness, args.simulation)
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
