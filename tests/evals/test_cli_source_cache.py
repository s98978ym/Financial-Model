import json
import subprocess
import sys
from pathlib import Path


def test_source_cache_cli_show_outputs_metadata(tmp_path: Path) -> None:
    registry_path = tmp_path / "source_cache.json"
    registry_path.write_text(
        json.dumps(
            {
                "metadata": {"version": "test", "update_scope": ["sales_efficiency_analysis"]},
                "refs": {"sales_efficiency_analysis": []},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.cli.main",
            "eval",
            "source-cache",
            "show",
            "--registry-path",
            str(registry_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["version"] == "test"
    assert "sales_efficiency_analysis" in payload["source_types"]


def test_source_cache_cli_upsert_writes_entry(tmp_path: Path) -> None:
    registry_path = tmp_path / "source_cache.json"
    registry_path.write_text(
        json.dumps(
            {
                "metadata": {"version": "test", "update_scope": []},
                "refs": {},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.cli.main",
            "eval",
            "source-cache",
            "upsert",
            "--source-type",
            "sales_efficiency_analysis",
            "--title",
            "Benchmarks",
            "--url",
            "https://example.com/benchmarks",
            "--publisher",
            "Example",
            "--quote",
            "Benchmark quote",
            "--registry-path",
            str(registry_path),
        ],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    refs = payload["refs"]["sales_efficiency_analysis"]
    assert refs[0]["quote"] == "Benchmark quote"
