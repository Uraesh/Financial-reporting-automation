"""KPI and aggregation helpers."""

from __future__ import annotations

from typing import cast

import pandas as pd

from scripts.types import ColumnMapping, KpiMetrics


def _column_series(dataframe: pd.DataFrame, column_name: str) -> pd.Series:
    """Return one dataframe column as a typed pandas series."""
    return cast(pd.Series, dataframe.loc[:, column_name])


def _numeric_series(values: pd.Series) -> pd.Series:
    """Return a float series safe for aggregations."""
    series = pd.Series(values, index=values.index, copy=False, dtype="object")
    numeric_values = pd.to_numeric(series, errors="coerce")
    return pd.Series(numeric_values, index=series.index, dtype="float64").fillna(0.0)


def compute_kpis(dataframe: pd.DataFrame, mapping: ColumnMapping) -> KpiMetrics:
    """Compute dashboard KPI values."""
    amount_series = _numeric_series(_column_series(dataframe, mapping.amount))
    pme_series = pd.Series(_column_series(dataframe, mapping.pme), dtype="string")
    region_series = pd.Series(_column_series(dataframe, mapping.region), dtype="string")

    total_engagements = float(amount_series.to_numpy(dtype="float64").sum())
    pme_count = int(pme_series.nunique(dropna=True))
    transaction_count = int(len(dataframe))
    region_count = int(region_series.nunique(dropna=True))

    return KpiMetrics(
        total_engagements=total_engagements,
        pme_count=pme_count,
        transaction_count=transaction_count,
        region_count=region_count,
    )


def aggregate_by_region(dataframe: pd.DataFrame, mapping: ColumnMapping) -> pd.DataFrame:
    """Aggregate engagement amounts by region."""
    grouped_source = cast(pd.DataFrame, dataframe.loc[:, [mapping.region, mapping.amount]].copy())
    grouped_source[mapping.amount] = _numeric_series(_column_series(grouped_source, mapping.amount))
    grouped = cast(
        pd.DataFrame,
        grouped_source.groupby(mapping.region, dropna=False, as_index=False).agg(
        total_amount=(mapping.amount, "sum")
        ),
    )
    grouped = grouped.rename(columns={mapping.region: "region"})
    grouped["total_amount"] = cast(pd.Series, grouped.loc[:, "total_amount"]).astype(float)
    grouped = grouped.sort_values("total_amount", ascending=False).reset_index(drop=True)
    return grouped


def aggregate_by_flow(dataframe: pd.DataFrame, mapping: ColumnMapping) -> pd.DataFrame:
    """Aggregate engagement amounts by flow category."""
    grouped_source = cast(pd.DataFrame, dataframe.loc[:, [mapping.flow, mapping.amount]].copy())
    grouped_source[mapping.amount] = _numeric_series(_column_series(grouped_source, mapping.amount))
    grouped = cast(
        pd.DataFrame,
        grouped_source.groupby(mapping.flow, dropna=False, as_index=False).agg(
        total_amount=(mapping.amount, "sum")
        ),
    )
    grouped = grouped.rename(columns={mapping.flow: "flow"})
    grouped["total_amount"] = cast(pd.Series, grouped.loc[:, "total_amount"]).astype(float)
    grouped = grouped.sort_values("total_amount", ascending=False).reset_index(drop=True)
    return grouped


def format_currency(amount: float) -> str:
    """Format a number as finance-friendly text."""
    raw = f"{amount:,.2f}"
    return raw.replace(",", " ").replace(".", ",")
