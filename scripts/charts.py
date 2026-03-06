"""Plotly chart builders for financial dashboards."""

from __future__ import annotations

from typing import NamedTuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.graph_objs import Figure

NUMERIC_CHART_TYPES: tuple[str, ...] = (
    "Barres",
    "Barres horizontales",
    "Ligne",
    "Aire",
    "Waterfall",
    "Scatter",
    "Histogramme",
)

DISTRIBUTION_CHART_TYPES: tuple[str, ...] = (
    "Camembert",
    "Donut",
    "Treemap",
    "Sunburst",
    "Funnel",
    "Barres",
)

REGION_CHART_TYPES: tuple[str, ...] = (
    "Barres",
    "Barres horizontales",
    "Ligne",
    "Aire",
    "Waterfall",
)

FLOW_CHART_TYPES: tuple[str, ...] = (
    "Camembert",
    "Donut",
    "Treemap",
    "Sunburst",
    "Funnel",
    "Barres",
)


class ChartThemePalette(NamedTuple):
    """Color palette used to style all Plotly figures."""
    primary: str
    secondary: str
    success: str
    alert: str
    background: str
    panel_background: str
    text: str
    series: tuple[str, ...]


CHART_THEME_PALETTES: dict[str, ChartThemePalette] = {
    "Finance Pro": ChartThemePalette(
        primary="#1E40AF",
        secondary="#059669",
        success="#10B981",
        alert="#EF4444",
        background="#F8FAFC",
        panel_background="#FFFFFF",
        text="#0F2044",
        series=("#1E40AF", "#059669", "#0EA5E9", "#8B5CF6", "#F59E0B"),
    ),
    "Dark Mode": ChartThemePalette(
        primary="#58A6FF",
        secondary="#3FB950",
        success="#3FB950",
        alert="#F85149",
        background="#0D1117",
        panel_background="#161B22",
        text="#E6EDF3",
        series=("#58A6FF", "#3FB950", "#D2A8FF", "#FFA657", "#FF7B72"),
    ),
    "Executive Mode": ChartThemePalette(
        primary="#1F2937",
        secondary="#B45309",
        success="#047857",
        alert="#B91C1C",
        background="#FFFFFF",
        panel_background="#F9FAFB",
        text="#111827",
        series=("#1F2937", "#4B5563", "#9CA3AF", "#D1D5DB", "#B45309"),
    ),
}

CHART_THEME_NAMES: tuple[str, ...] = tuple(CHART_THEME_PALETTES.keys())

_chart_theme_state: dict[str, str] = {
    "style": "Finance Pro",
    "palette": "Finance Pro",
}


def set_chart_theme(style_name: str, palette_name: str | None = None) -> None:
    """Set active chart style and optional series palette."""
    set_chart_style(style_name)
    if palette_name is None:
        set_chart_palette(style_name)
        return
    set_chart_palette(palette_name)


def set_chart_style(theme_name: str) -> None:
    """Set active chart surface style."""
    if theme_name in CHART_THEME_PALETTES:
        _chart_theme_state["style"] = theme_name


def set_chart_palette(theme_name: str) -> None:
    """Set active chart series palette."""
    if theme_name in CHART_THEME_PALETTES:
        _chart_theme_state["palette"] = theme_name


def create_numeric_figure(
    dataframe: pd.DataFrame,
    *,
    x_column: str,
    y_column: str,
    chart_type: str,
    title: str,
    color_column: str | None = None,
) -> Figure:
    """Build a numeric chart from a dataframe."""
    if dataframe.empty:
        return _empty_figure("Aucune donnee disponible.")

    if chart_type == "Barres horizontales":
        figure = px.bar(
            dataframe,
            x=y_column,
            y=x_column,
            orientation="h",
            color=color_column or y_column,
            labels={x_column: "Categorie", y_column: "Valeur"},
            title=title,
        )
    elif chart_type == "Ligne":
        figure = px.line(
            dataframe,
            x=x_column,
            y=y_column,
            color=color_column,
            markers=True,
            labels={x_column: "Categorie", y_column: "Valeur"},
            title=title,
        )
    elif chart_type == "Aire":
        figure = px.area(
            dataframe,
            x=x_column,
            y=y_column,
            color=color_column,
            labels={x_column: "Categorie", y_column: "Valeur"},
            title=title,
        )
    elif chart_type == "Waterfall":
        palette = _series_palette()
        figure = go.Figure(
            go.Waterfall(
                x=dataframe[x_column],
                y=dataframe[y_column],
                marker={"color": palette.primary},
                connector={"line": {"color": palette.secondary}},
            )
        )
        figure.update_layout(title=title)
        figure.update_xaxes(title=x_column)
        figure.update_yaxes(title=y_column)
    elif chart_type == "Scatter":
        figure = px.scatter(
            dataframe,
            x=x_column,
            y=y_column,
            color=color_column,
            labels={x_column: "Categorie", y_column: "Valeur"},
            title=title,
        )
    elif chart_type == "Histogramme":
        figure = px.histogram(
            dataframe,
            x=y_column,
            color=color_column,
            nbins=30,
            labels={y_column: "Valeur"},
            title=title,
        )
    else:
        figure = px.bar(
            dataframe,
            x=x_column,
            y=y_column,
            color=color_column or y_column,
            labels={x_column: "Categorie", y_column: "Valeur"},
            title=title,
        )

    _style_figure(figure)
    return figure


def create_distribution_figure(
    dataframe: pd.DataFrame,
    label_column: str,
    value_column: str,
    chart_type: str,
    title: str,
) -> Figure:
    """Build a distribution/composition chart from a dataframe."""
    if dataframe.empty:
        return _empty_figure("Aucune donnee disponible.")

    if chart_type == "Donut":
        figure = px.pie(
            dataframe,
            names=label_column,
            values=value_column,
            title=title,
            hole=0.45,
        )
    elif chart_type == "Treemap":
        figure = px.treemap(
            dataframe,
            path=[label_column],
            values=value_column,
            title=title,
        )
    elif chart_type == "Sunburst":
        figure = px.sunburst(
            dataframe,
            path=[label_column],
            values=value_column,
            title=title,
        )
    elif chart_type == "Funnel":
        figure = px.funnel(
            dataframe,
            x=value_column,
            y=label_column,
            title=title,
        )
    elif chart_type == "Barres":
        figure = px.bar(
            dataframe,
            x=label_column,
            y=value_column,
            color=value_column,
            title=title,
        )
    else:
        figure = px.pie(
            dataframe,
            names=label_column,
            values=value_column,
            title=title,
        )

    _style_figure(figure)
    return figure


def create_region_figure(region_summary: pd.DataFrame, chart_type: str) -> Figure:
    """Build engagement amount chart by region."""
    return create_numeric_figure(
        dataframe=region_summary,
        x_column="region",
        y_column="total_amount",
        chart_type=chart_type,
        title="Montants des engagements par region",
    )


def create_flow_figure(flow_summary: pd.DataFrame, chart_type: str) -> Figure:
    """Build flow distribution chart."""
    return create_distribution_figure(
        dataframe=flow_summary,
        label_column="flow",
        value_column="total_amount",
        chart_type=chart_type,
        title="Repartition des flux",
    )


def style_figure(figure: Figure) -> Figure:
    """Apply common visual style and return the same figure."""
    _style_figure(figure)
    return figure


def _style_figure(figure: Figure) -> None:
    """Apply project visual style to all charts."""
    style_palette = _style_palette()
    series_palette = _series_palette()
    figure.update_layout(
        paper_bgcolor=style_palette.background,
        plot_bgcolor=style_palette.panel_background,
        font={
            "family": "Candara, Optima, Trebuchet MS, sans-serif",
            "color": style_palette.text,
        },
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
        colorway=list(series_palette.series),
        legend={"bgcolor": "rgba(0,0,0,0)"},
    )


def _empty_figure(message: str) -> Figure:
    """Return a placeholder figure."""
    palette = _style_palette()
    figure = go.Figure()
    figure.add_annotation(
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        text=message,
        showarrow=False,
        font={"size": 16, "color": palette.primary},
    )
    _style_figure(figure)
    figure.update_xaxes(visible=False)
    figure.update_yaxes(visible=False)
    return figure


def _style_palette() -> ChartThemePalette:
    """Return the active chart style palette."""
    return CHART_THEME_PALETTES.get(
        _chart_theme_state["style"],
        CHART_THEME_PALETTES["Finance Pro"],
    )


def _series_palette() -> ChartThemePalette:
    """Return the active chart series palette."""
    return CHART_THEME_PALETTES.get(
        _chart_theme_state["palette"],
        CHART_THEME_PALETTES["Finance Pro"],
    )
