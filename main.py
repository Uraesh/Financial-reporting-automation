"""CLI entrypoint for the consolidation pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.aggregation import aggregate_by_flow, aggregate_by_region, compute_kpis
from scripts.cleaning import clean_dataframe
from scripts.ingestion import consolidate_files, load_sources_from_directory
from scripts.reporting import generate_pdf_report_now


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Consolider, nettoyer et exporter des rapports financiers."
    )
    parser.add_argument(
        "--input-dir",
        default="data/inputs",
        help="Dossier contenant les fichiers CSV/XLSX a consolider.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/outputs",
        help="Dossier de sortie des exports consolides.",
    )
    return parser.parse_args()


def run_pipeline(input_dir: Path, output_dir: Path) -> None:
    """Execute full consolidation pipeline on local files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    sources = load_sources_from_directory(input_dir)
    if not sources:
        raise ValueError(f"Aucun fichier CSV/XLSX trouve dans {input_dir}.")

    consolidated, warnings = consolidate_files(sources)
    cleaned, mapping = clean_dataframe(consolidated)

    metrics = compute_kpis(cleaned, mapping)
    region_summary = aggregate_by_region(cleaned, mapping)
    flow_summary = aggregate_by_flow(cleaned, mapping)

    cleaned.to_csv(output_dir / "consolidated_data.csv", index=False)
    region_summary.to_csv(output_dir / "summary_by_region.csv", index=False)
    flow_summary.to_csv(output_dir / "summary_by_flow.csv", index=False)

    pdf_bytes = generate_pdf_report_now(
        metrics=metrics,
        region_summary=region_summary,
        flow_summary=flow_summary,
    )
    (output_dir / "report_summary.pdf").write_bytes(pdf_bytes)

    if warnings:
        print("Avertissements:")
        for warning in warnings:
            print(f"- {warning}")

    print(f"Consolidation terminee. Fichiers generes dans: {output_dir}")


def main() -> None:
    """CLI runtime wrapper."""
    args = parse_arguments()
    run_pipeline(input_dir=Path(args.input_dir), output_dir=Path(args.output_dir))


if __name__ == "__main__":
    main()
