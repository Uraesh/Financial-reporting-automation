"""Streamlit dashboard for financial report consolidation."""
# pylint: disable=wrong-import-position,too-many-instance-attributes

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import sys
from typing import Any, cast

import pandas as pd
import streamlit as st

# â”€â”€ Paths â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_DASHBOARD_DIR = Path(__file__).resolve().parent
_STREAMLIT_CONFIG = _DASHBOARD_DIR.parent / ".streamlit" / "config.toml"
_THEMES_DIR = _DASHBOARD_DIR.parent / "themes"

_THEME_CONFIG_FILES: dict[str, str] = {
    "Finance Pro":    "config_finance_pro.toml",
    "Dark Mode":      "config_dark_mode.toml",
    "Executive Mode": "config_executive_mode.toml",
}


def _apply_streamlit_config(theme_name: str) -> None:
    """Copy the matching config.toml so Streamlit picks it up on next rerun.

    The file is only written when the theme actually changes, avoiding
    unnecessary disk writes on every rerun.
    """
    src = _THEMES_DIR / _THEME_CONFIG_FILES[theme_name]
    if not src.exists():
        return  # themes folder not deployed â€“ skip silently
    _STREAMLIT_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, _STREAMLIT_CONFIG)

PROJECT_ROOT = _DASHBOARD_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.aggregation import (
    aggregate_by_flow,
    aggregate_by_region,
    compute_kpis,
)
from scripts.charts import (
    CHART_THEME_NAMES,
    DISTRIBUTION_CHART_TYPES,
    NUMERIC_CHART_TYPES,
    set_chart_theme,
)
from scripts.cleaning import clean_dataframe
from scripts.dashboard_profiles import (
    DASHBOARD_OPTIONS,
    PRINCIPAL_DASHBOARDS,
    DashboardBundle,
    build_dashboard_bundle,
)
from scripts.ingestion import build_sources_from_uploads, consolidate_files
from scripts.reporting import generate_pdf_report_now
from scripts.types import ColumnMapping, SourceFile, UploadedFileLike


@dataclass(frozen=True)
class ThemePalette:
    """Color palette for dashboard themes."""

    primary: str
    secondary: str
    accent: str
    success: str
    alert: str
    background: str
    text: str
    text_secondary: str
    sidebar_background: str
    sidebar_text: str
    card_background: str
    border: str
    button_text: str
    shadow_color: str
    series: tuple[str, ...]


THEMES: dict[str, ThemePalette] = {
    # â”€â”€ Finance Pro â”€â”€ Bleu institutionnel / vert / fond clair â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "Finance Pro": ThemePalette(
        primary="#1E40AF",        # Bleu institutionnel
        secondary="#059669",      # Vert finance
        accent="#0EA5E9",         # Bleu ciel (hover / focus)
        success="#10B981",        # Vert Ã©meraude (hausse)
        alert="#EF4444",          # Rouge corail (baisse)
        background="#F8FAFC",     # Blanc cassÃ© (fond principal)
        text="#0F2044",           # Bleu marine foncÃ© (texte principal)
        text_secondary="#64748B", # Gris ardoise (texte secondaire)
        sidebar_background="#FFFFFF",
        sidebar_text="#0F2044",
        card_background="#FFFFFF",
        border="#E2E8F0",         # Gris clair
        button_text="#FFFFFF",
        shadow_color="rgba(15, 32, 68, 0.10)",
        series=("#1E40AF", "#059669", "#0EA5E9", "#8B5CF6", "#F59E0B"),
    ),
    # â”€â”€ Dark Mode â”€â”€ Fond noir graphite / accents bleu & vert nÃ©on â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "Dark Mode": ThemePalette(
        primary="#58A6FF",        # Bleu Ã©lectrique
        secondary="#3FB950",      # Vert nÃ©on doux
        accent="#79C0FF",         # Bleu clair (hover / focus)
        success="#3FB950",        # Vert nÃ©on (hausse)
        alert="#F85149",          # Rouge vif (baisse)
        background="#0D1117",     # Noir graphite (fond principal)
        text="#E6EDF3",           # Blanc doux (texte principal)
        text_secondary="#8B949E", # Gris clair (texte secondaire)
        sidebar_background="#161B22",
        sidebar_text="#E6EDF3",
        card_background="#161B22",
        border="#30363D",         # Gris subtil
        button_text="#0D1117",    # Texte sombre sur fond clair nÃ©on
        shadow_color="rgba(0, 0, 0, 0.40)",
        series=("#58A6FF", "#3FB950", "#D2A8FF", "#FFA657", "#FF7B72"),
    ),
    # â”€â”€ Executive Mode â”€â”€ Minimaliste noir & or / fond blanc â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    "Executive Mode": ThemePalette(
        primary="#1F2937",        # Anthracite (titres / accent fort)
        secondary="#B45309",      # Or discret (boutons secondaires)
        accent="#374151",         # Gris foncÃ© (hover / focus)
        success="#047857",        # Vert sobre (hausse)
        alert="#B91C1C",          # Rouge sobre (baisse)
        background="#FFFFFF",     # Blanc pur (fond principal)
        text="#111827",           # Noir profond (texte principal)
        text_secondary="#6B7280", # Gris moyen (texte secondaire)
        sidebar_background="#F9FAFB",
        sidebar_text="#111827",
        card_background="#F9FAFB",
        border="#D1D5DB",         # Gris fin
        button_text="#FFFFFF",
        shadow_color="rgba(17, 24, 39, 0.08)",
        series=("#1F2937", "#4B5563", "#9CA3AF", "#D1D5DB", "#B45309"),
    ),
}

SYNCED_CHART_PALETTE = "Synchronisee avec le theme visuel"


def main() -> None:
    """Run the Streamlit app."""
    st.set_page_config(
        page_title="Consolidation Financiere",
        page_icon=":bar_chart:",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _init_session_state()

    (
        source_files,
        selected_theme,
        selected_chart_palette,
        dashboard_name,
        numeric_chart_type,
        distribution_chart_type,
        merge_clicked,
    ) = _render_sidebar()

    palette = THEMES[selected_theme]

    # â”€â”€ Theme change: copy config.toml and rerun so Streamlit reloads it â”€â”€â”€â”€
    if selected_theme != st.session_state["active_theme"]:
        st.session_state["active_theme"] = selected_theme
        _apply_streamlit_config(selected_theme)
        st.rerun()

    _apply_theme_style(palette)
    set_chart_theme(
        style_name=selected_theme,
        palette_name=_resolve_chart_palette(selected_theme, selected_chart_palette),
    )

    st.title("Consolidation des Rapports Financiers")
    st.caption(
        "Pipeline automatise: import multi-fichiers, nettoyage, visualisation et export PDF."
    )
    if merge_clicked:
        _process_merge(source_files)

    dataframe = cast(pd.DataFrame, st.session_state["cleaned_data"])
    if dataframe.empty:
        st.info(
            "Importez des fichiers CSV/XLSX dans la barre laterale, puis cliquez sur 'Fusionner'."
        )
        return

    mapping = cast(ColumnMapping, st.session_state["column_mapping"])
    _render_dashboard(
        dataframe,
        mapping,
        dashboard_name,
        numeric_chart_type,
        distribution_chart_type,
    )


def _init_session_state() -> None:
    """Initialize default session state entries."""
    if "cleaned_data" not in st.session_state:
        st.session_state["cleaned_data"] = pd.DataFrame()
    if "column_mapping" not in st.session_state:
        st.session_state["column_mapping"] = ColumnMapping(
            amount="montant",
            pme="pme",
            date="date_engagement",
            flow="flux",
        )
    if "warnings" not in st.session_state:
        st.session_state["warnings"] = []
    if "active_theme" not in st.session_state:
        st.session_state["active_theme"] = "Finance Pro"


def _render_sidebar() -> tuple[list[SourceFile], str, str, str, str, str, bool]:
    """Render sidebar controls and return user selections."""
    theme_keys = tuple(THEMES.keys())
    active_theme: str = cast(str, st.session_state["active_theme"])

    with st.sidebar:
        st.header("Controles")
        selected_theme = st.selectbox(
            "Theme visuel",
            options=theme_keys,
            index=theme_keys.index(active_theme),
            help="1) Finance Pro  2) Dark Mode  3) Executive Mode",
        )
        selected_chart_palette = st.selectbox(
            "Palette des graphiques",
            options=(SYNCED_CHART_PALETTE, *CHART_THEME_NAMES),
            index=0,
            help="Permet de changer les couleurs des series Plotly sans modifier le theme global.",
        )
        st.caption("Dashboards principaux en grande institution:")
        st.caption("\n".join(PRINCIPAL_DASHBOARDS))
        uploaded_files = cast(
            list[UploadedFileLike] | None,
            st.file_uploader(
                "Importer un ou plusieurs CSV/Excel",
                type=["csv", "xlsx", "xls"],
                accept_multiple_files=True,
                help="Vous pouvez charger plusieurs fichiers en meme temps.",
            ),
        )
        dashboard_name = st.selectbox(
            "Type de dashboard financier",
            options=DASHBOARD_OPTIONS,
            index=0,
        )

        numeric_chart_type = st.selectbox(
            "Style graphique numerique",
            options=NUMERIC_CHART_TYPES,
            index=0,
        )
        distribution_chart_type = st.selectbox(
            "Style graphique de repartition",
            options=DISTRIBUTION_CHART_TYPES,
            index=0,
        )

        merge_clicked = st.button(
            "Fusionner",
            type="primary",
            use_container_width=True,
            help="Consolide les fichiers, nettoie les donnees et met a jour le dashboard.",
        )

    source_files = build_sources_from_uploads(uploaded_files) if uploaded_files else []
    return (
        source_files,
        selected_theme,
        selected_chart_palette,
        dashboard_name,
        numeric_chart_type,
        distribution_chart_type,
        merge_clicked,
    )


def _resolve_chart_palette(selected_theme: str, selected_chart_palette: str) -> str:
    """Resolve the effective chart palette name from sidebar selection."""
    if selected_chart_palette == SYNCED_CHART_PALETTE:
        return selected_theme
    return selected_chart_palette


def _process_merge(source_files: list[SourceFile]) -> None:
    """Merge uploaded files and update session state."""
    if not source_files:
        st.warning("Aucun fichier fourni.")
        return

    with st.spinner("Consolidation et nettoyage des donnees en cours..."):
        try:
            consolidated, warnings = consolidate_files(source_files)
            cleaned, mapping = clean_dataframe(consolidated)
        except ValueError as exc:
            st.error(str(exc))
            return

    st.session_state["cleaned_data"] = cleaned
    st.session_state["column_mapping"] = mapping
    st.session_state["warnings"] = warnings
    st.success(f"Fusion terminee: {len(cleaned)} ligne(s) consolidee(s).")


def _render_dashboard(
    dataframe: pd.DataFrame,
    mapping: ColumnMapping,
    dashboard_name: str,
    numeric_chart_type: str,
    distribution_chart_type: str,
) -> None:
    """Render KPI cards, charts and exports."""
    warnings = cast(list[str], st.session_state.get("warnings", []))
    if warnings:
        st.warning("Certains fichiers ont ete ignores:\n- " + "\n- ".join(warnings))

    dashboard_bundle = build_dashboard_bundle(
        dataframe=dataframe,
        mapping=mapping,
        selected_dashboard=dashboard_name,
        numeric_chart_type=numeric_chart_type,
        distribution_chart_type=distribution_chart_type,
    )
    _render_dashboard_bundle(dashboard_bundle)

    metrics = compute_kpis(dataframe, mapping)
    region_summary = aggregate_by_region(dataframe, mapping)
    flow_summary = aggregate_by_flow(dataframe, mapping)

    st.subheader("Apercu des donnees consolidees")
    st.dataframe(dataframe, use_container_width=True, hide_index=True)

    st.subheader("Exports")
    pdf_bytes = generate_pdf_report_now(
        metrics=metrics,
        region_summary=region_summary,
        flow_summary=flow_summary,
    )

    export_column_a, export_column_b = st.columns(2)
    with export_column_a:
        st.download_button(
            "Telecharger le rapport PDF",
            data=pdf_bytes,
            file_name="rapport_synthese_financier.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    with export_column_b:
        csv_bytes = dataframe.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Telecharger les donnees consolidees (CSV)",
            data=csv_bytes,
            file_name="donnees_consolidees.csv",
            mime="text/csv",
            use_container_width=True,
        )


def _render_dashboard_bundle(bundle: DashboardBundle) -> None:
    """Render domain-specific KPI cards and figures."""
    st.subheader(bundle.title)
    st.caption(bundle.description)
    _render_kpi_cards(bundle.kpis)

    figures = list(bundle.figures)
    if not figures:
        return

    if len(figures) == 1:
        st.plotly_chart(figures[0], use_container_width=True, config={"displaylogo": False})
        return

    chart_left, chart_right = st.columns(2)
    with chart_left:
        st.plotly_chart(figures[0], use_container_width=True, config={"displaylogo": False})
    with chart_right:
        st.plotly_chart(figures[1], use_container_width=True, config={"displaylogo": False})

    for figure in figures[2:]:
        st.plotly_chart(figure, use_container_width=True, config={"displaylogo": False})


def _render_kpi_cards(cards: tuple[tuple[str, str], ...]) -> None:
    """Display KPI cards by rows of three for readability."""
    for index in range(0, len(cards), 3):
        current_cards = cards[index : index + 3]
        columns = cast(tuple[Any, ...], tuple(st.columns(len(current_cards))))
        for column, (label, value) in zip(columns, current_cards):
            with column:
                _render_kpi_card(label, value)


def _render_kpi_card(label: str, value: str) -> None:
    """Render one custom KPI card."""
    st.markdown(
        f"""
        <div class="kpi-card">
          <div class="kpi-label">{label}</div>
          <div class="kpi-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _apply_theme_style(palette: ThemePalette) -> None:
    """Inject custom CSS variables and component overrides for the selected theme."""
    # Join chart series colors as a comma-separated string for display only;
    # individual series are consumed by set_chart_theme via the palette object.
    series_css = " ".join(
        f"--series-{i + 1}: {color};" for i, color in enumerate(palette.series)
    )

    st.markdown(
        f"""
        <style>
          :root {{
            --primary:         {palette.primary};
            --secondary:       {palette.secondary};
            --accent:          {palette.accent};
            --success:         {palette.success};
            --alert:           {palette.alert};
            --bg:              {palette.background};
            --text:            {palette.text};
            --text-secondary:  {palette.text_secondary};
            --sidebar-bg:      {palette.sidebar_background};
            --sidebar-text:    {palette.sidebar_text};
            --card-bg:         {palette.card_background};
            --border:          {palette.border};
            --btn-text:        {palette.button_text};
            --shadow:          {palette.shadow_color};
            {series_css}
          }}

          /* â”€â”€ Global â”€â”€ */
          body {{
            background-color: var(--bg);
            color: var(--text);
          }}
          html, body, [class*="css"] {{
            font-family: "Candara", "Optima", "Trebuchet MS", sans-serif;
            color: var(--text);
          }}

          /* â”€â”€ App container â”€â”€ */
          [data-testid="stAppViewContainer"] {{
            background-color: var(--bg);
          }}

          /* â”€â”€ Headings â”€â”€ */
          h1, h2, h3 {{
            color: var(--primary) !important;
          }}

          /* â”€â”€ Sidebar â”€â”€ */
          [data-testid="stSidebar"] {{
            background: var(--sidebar-bg);
            border-right: 1px solid var(--border);
          }}
          [data-testid="stSidebar"] * {{
            color: var(--sidebar-text) !important;
          }}

          /* â”€â”€ Streamlit metric widget â”€â”€ */
          .stMetric {{
            background-color: var(--card-bg);
            border-radius: 10px;
            padding: 10px;
            border: 1px solid var(--border);
          }}

          /* â”€â”€ KPI cards â”€â”€ */
          .kpi-card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 0.9rem 1rem;
            min-height: 118px;
            box-shadow: 0 10px 28px var(--shadow);
            animation: fade-slide 0.55s ease both;
          }}
          .kpi-label {{
            color: var(--text-secondary);
            font-size: 0.86rem;
            margin-bottom: 0.5rem;
          }}
          .kpi-value {{
            color: var(--primary);
            font-size: 1.45rem;
            font-weight: 800;
            line-height: 1.2;
            word-break: break-word;
          }}

          /* â”€â”€ Buttons â”€â”€ */
          .stButton > button {{
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            background: var(--primary) !important;
            color: var(--btn-text) !important;
            font-weight: 700 !important;
          }}
          .stDownloadButton > button {{
            border: 1px solid var(--border) !important;
            border-radius: 10px !important;
            background: var(--secondary) !important;
            color: var(--btn-text) !important;
            font-weight: 700 !important;
          }}
          .stButton > button:hover,
          .stDownloadButton > button:hover {{
            filter: brightness(0.93);
            border-color: var(--accent) !important;
            box-shadow: 0 0 0 2px var(--accent);
          }}

          /* â”€â”€ Entrance animation â”€â”€ */
          @keyframes fade-slide {{
            from {{
              opacity: 0;
              transform: translateY(10px);
            }}
            to {{
              opacity: 1;
              transform: translateY(0);
            }}
          }}

          /* â”€â”€ Responsive â”€â”€ */
          @media (max-width: 900px) {{
            .kpi-card {{
              min-height: 92px;
            }}
            .kpi-value {{
              font-size: 1.15rem;
            }}
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
