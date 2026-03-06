"""PDF reporting helpers."""

from __future__ import annotations

from datetime import datetime
from typing import cast

from fpdf import FPDF
from fpdf.enums import XPos, YPos
import pandas as pd

from scripts.aggregation import format_currency
from scripts.types import KpiMetrics


def generate_pdf_report(
    metrics: KpiMetrics,
    region_summary: pd.DataFrame,
    flow_summary: pd.DataFrame,
    generated_at: datetime,
) -> bytes:
    """Build a PDF synthesis report and return bytes."""
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    _write_header(pdf, generated_at)
    _write_global_metrics(pdf, metrics)
    _write_table(pdf, "Montants par region", region_summary, label_column="region")
    _write_table(pdf, "Repartition des flux", flow_summary, label_column="flow")

    return bytes(pdf.output())


def generate_pdf_report_now(
    metrics: KpiMetrics,
    region_summary: pd.DataFrame,
    flow_summary: pd.DataFrame,
) -> bytes:
    """Build a synthesis report with the current timestamp."""
    return generate_pdf_report(
        metrics=metrics,
        region_summary=region_summary,
        flow_summary=flow_summary,
        generated_at=datetime.now(),
    )


def _write_header(pdf: FPDF, generated_at: datetime) -> None:
    pdf.set_fill_color(11, 31, 58)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(
        w=0,
        h=12,
        text=_to_latin1("Rapport de synthese - Consolidation financiere"),
        border=0,
        fill=True,
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(4)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", size=11)
    timestamp = generated_at.strftime("%Y-%m-%d %H:%M:%S")
    pdf.cell(
        0,
        8,
        text=_to_latin1(f"Date de generation: {timestamp}"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(2)


def _write_global_metrics(pdf: FPDF, metrics: KpiMetrics) -> None:
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(
        0,
        8,
        text=_to_latin1("Statistiques globales"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.set_font("Helvetica", size=11)

    lines = [
        f"Montant total des engagements: {format_currency(metrics.total_engagements)}",
        f"Nombre de PME traitees: {metrics.pme_count}",
        f"Nombre de transactions: {metrics.transaction_count}",
        f"Nombre de regions couvertes: {metrics.region_count}",
    ]
    for line in lines:
        pdf.cell(0, 7, text=_to_latin1(line), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)


def _write_table(
    pdf: FPDF,
    title: str,
    dataframe: pd.DataFrame,
    label_column: str,
) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, text=_to_latin1(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if dataframe.empty:
        pdf.set_font("Helvetica", size=10)
        pdf.cell(
            0,
            7,
            text=_to_latin1("Aucune donnee disponible."),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.ln(2)
        return

    clipped = dataframe.head(10)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(110, 7, text=_to_latin1("Categorie"), border=1, align="L")
    pdf.cell(
        70,
        7,
        text=_to_latin1("Montant total"),
        border=1,
        align="R",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    pdf.set_font("Helvetica", size=10)
    for _, row in clipped.iterrows():
        label = str(cast(object, row[label_column]))
        amount = float(cast(float | int | str, row["total_amount"]))
        pdf.cell(110, 7, text=_to_latin1(label[:45]), border=1, align="L")
        pdf.cell(
            70,
            7,
            text=_to_latin1(format_currency(amount)),
            border=1,
            align="R",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

    pdf.ln(3)


def _to_latin1(text: str) -> str:
    """Ensure text is safe for FPDF latin-1 rendering."""
    return text.encode("latin-1", "replace").decode("latin-1")
