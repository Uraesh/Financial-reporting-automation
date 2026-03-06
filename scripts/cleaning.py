"""Data cleaning and normalization utilities."""

from __future__ import annotations

import re
import unicodedata
import warnings
from dataclasses import replace
from typing import Collection, Iterable, Sequence, cast

import pandas as pd

from scripts.types import ColumnMapping

AMOUNT_ALIASES: tuple[str, ...] = (
    "montant",
    "montant_engagement",
    "montant_total",
    "montant_net",
    "montant_brut",
    "engagement",
    "engagement_amount",
    "amount",
    "amount_total",
    "valeur",
    "value",
    "encours",
    "solde",
    "principal",
    "capital",
    "revenu",
    "revenue",
    "chiffre_affaires",
)
PME_ALIASES: tuple[str, ...] = (
    "pme",
    "nom_pme",
    "nom_entreprise",
    "entreprise",
    "societe",
    "beneficiaire",
    "beneficiaire_final",
    "client",
    "raison_sociale",
    "contrepartie",
    "counterparty",
    "tiers",
)
DATE_ALIASES: tuple[str, ...] = (
    "date",
    "date_engagement",
    "date_operation",
    "date_transaction",
    "date_valeur",
    "date_comptable",
    "engagement_date",
    "periode",
    "periode_comptable",
    "timestamp",
    "month",
    "mois",
)
FLOW_ALIASES: tuple[str, ...] = (
    "flux",
    "type_flux",
    "nature_flux",
    "categorie_flux",
    "flow",
    "flow_type",
    "type_operation",
    "nature_operation",
    "operation",
    "mouvement",
    "sens",
    "transaction_type",
)

AMOUNT_KEYWORDS: tuple[str, ...] = (
    "montant",
    "engagement",
    "amount",
    "valeur",
    "value",
    "encours",
    "solde",
    "capital",
    "principal",
    "revenu",
    "revenue",
    "chiffre",
    "affaires",
)
PME_KEYWORDS: tuple[str, ...] = (
    "pme",
    "entreprise",
    "societe",
    "beneficiaire",
    "client",
    "raison",
    "sociale",
    "contrepartie",
    "tiers",
)
DATE_KEYWORDS: tuple[str, ...] = (
    "date",
    "periode",
    "mois",
    "month",
    "timestamp",
    "valeur",
    "transaction",
    "comptable",
    "operation",
)
FLOW_KEYWORDS: tuple[str, ...] = (
    "flux",
    "flow",
    "type",
    "nature",
    "categorie",
    "operation",
    "mouvement",
    "sens",
    "transaction",
)
FLOW_VALUE_HINTS: tuple[str, ...] = (
    "inflow",
    "outflow",
    "credit",
    "debit",
    "entree",
    "sortie",
    "paiement",
    "achat",
    "vente",
    "payment",
)
INTERNAL_COLUMNS: frozenset[str] = frozenset({"source_file"})
AMOUNT_SCORE_THRESHOLD = 8.0
DATE_SCORE_THRESHOLD = 8.0
FLOW_SCORE_THRESHOLD = 5.5
PME_SCORE_THRESHOLD = 5.5
NAME_SCORE_THRESHOLD = 18


def _column_names(dataframe: pd.DataFrame) -> list[str]:
    """Return dataframe column names as plain strings."""
    return [str(column_name) for column_name in cast(list[object], list(dataframe.columns))]


def _column_series(dataframe: pd.DataFrame, column_name: str) -> pd.Series:
    """Return one dataframe column as a typed pandas series."""
    return cast(pd.Series, dataframe.loc[:, column_name])


def clean_dataframe(raw_dataframe: pd.DataFrame) -> tuple[pd.DataFrame, ColumnMapping]:
    """Apply cleansing rules and return cleaned dataframe + resolved mapping."""
    if raw_dataframe.empty:
        raise ValueError("La consolidation est vide, impossible de nettoyer les donnees.")

    cleaned = standardize_columns(raw_dataframe)
    cleaned = cleaned.dropna(axis=0, how="all").reset_index(drop=True)

    if "region" not in cleaned.columns:
        cleaned["region"] = "Inconnue"

    mapping = _resolve_columns(cleaned)

    cleaned[mapping.amount] = _normalize_amounts(_column_series(cleaned, mapping.amount)).fillna(0.0)
    cleaned[mapping.amount] = cleaned[mapping.amount].astype(float).round(2)

    cleaned[mapping.pme] = _clean_text_series(
        _column_series(cleaned, mapping.pme),
        default_value="PME inconnue",
    )
    cleaned[mapping.flow] = _clean_text_series(
        _column_series(cleaned, mapping.flow),
        default_value="Flux non classe",
    )
    cleaned[mapping.region] = _clean_text_series(
        _column_series(cleaned, mapping.region),
        default_value="Inconnue",
    ).str.title()
    cleaned[mapping.date] = _normalize_dates(_column_series(cleaned, mapping.date))

    cleaned = cleaned.drop_duplicates().reset_index(drop=True)
    return cleaned, mapping


def standardize_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to snake_case ASCII."""
    renamed_dataframe = dataframe.copy()
    normalized_columns = [_slugify(column_name) for column_name in _column_names(renamed_dataframe)]
    renamed_dataframe.columns = _deduplicate_names(normalized_columns)
    return renamed_dataframe


def _resolve_columns(dataframe: pd.DataFrame) -> ColumnMapping:
    """Resolve columns used by KPI and visualizations."""
    columns = tuple(_column_names(dataframe))
    excluded_columns: set[str] = {"region"}

    amount_column = _find_amount_column(dataframe, excluded=excluded_columns)
    if amount_column is None:
        raise ValueError(_build_missing_column_message("montant", columns))
    excluded_columns.add(amount_column)

    date_column = _find_date_column(dataframe, excluded=excluded_columns)
    if date_column is None:
        dataframe["date_engagement"] = pd.Timestamp.today().strftime("%Y-%m-%d")
        date_column = "date_engagement"
    excluded_columns.add(date_column)

    flow_column = _find_flow_column(dataframe, excluded=excluded_columns)
    if flow_column is None:
        dataframe["flux"] = "Flux non classe"
        flow_column = "flux"
    excluded_columns.add(flow_column)

    pme_column = _find_pme_column(dataframe, excluded=excluded_columns)
    if pme_column is None:
        dataframe["pme"] = "PME inconnue"
        pme_column = "pme"

    mapping = ColumnMapping(
        amount=amount_column,
        pme=pme_column,
        date=date_column,
        flow=flow_column,
    )
    return replace(mapping, region="region")


def _find_amount_column(
    dataframe: pd.DataFrame,
    excluded: Collection[str],
) -> str | None:
    """Find the main amount column from names, then from numeric content."""
    named_match = _find_best_named_column(
        dataframe.columns,
        aliases=AMOUNT_ALIASES,
        keywords=AMOUNT_KEYWORDS,
        excluded=excluded,
    )
    if named_match is not None and (
        _is_exact_alias_match(named_match, AMOUNT_ALIASES)
        or _amount_content_score(_column_series(dataframe, named_match), named_match) > 0.0
    ):
        return named_match
    return _find_amount_by_content(dataframe, excluded=excluded)


def _find_date_column(
    dataframe: pd.DataFrame,
    excluded: Collection[str],
) -> str | None:
    """Find the main date column from names, then from date-like content."""
    named_match = _find_best_named_column(
        dataframe.columns,
        aliases=DATE_ALIASES,
        keywords=DATE_KEYWORDS,
        excluded=excluded,
    )
    if named_match is not None and (
        _is_exact_alias_match(named_match, DATE_ALIASES)
        or _date_content_score(_column_series(dataframe, named_match), named_match) > 0.0
    ):
        return named_match
    return _find_date_by_content(dataframe, excluded=excluded)


def _find_flow_column(
    dataframe: pd.DataFrame,
    excluded: Collection[str],
) -> str | None:
    """Find the transaction-flow column from names, then text-category content."""
    named_match = _find_best_named_column(
        dataframe.columns,
        aliases=FLOW_ALIASES,
        keywords=FLOW_KEYWORDS,
        excluded=excluded,
    )
    if named_match is not None and (
        _is_exact_alias_match(named_match, FLOW_ALIASES)
        or _name_similarity_score(
            named_match,
            aliases=FLOW_ALIASES,
            keywords=FLOW_KEYWORDS,
        )
        >= 40
        or _flow_content_score(_column_series(dataframe, named_match), named_match) > 0.0
    ):
        return named_match
    return _find_flow_by_content(dataframe, excluded=excluded)


def _find_pme_column(
    dataframe: pd.DataFrame,
    excluded: Collection[str],
) -> str | None:
    """Find the company/beneficiary column from names, then text identity content."""
    named_match = _find_best_named_column(
        dataframe.columns,
        aliases=PME_ALIASES,
        keywords=PME_KEYWORDS,
        excluded=excluded,
    )
    if named_match is not None and (
        _is_exact_alias_match(named_match, PME_ALIASES)
        or _name_similarity_score(
            named_match,
            aliases=PME_ALIASES,
            keywords=PME_KEYWORDS,
        )
        >= 40
        or _pme_content_score(_column_series(dataframe, named_match), named_match) > 0.0
    ):
        return named_match
    return _find_pme_by_content(dataframe, excluded=excluded)


def _find_best_named_column(
    columns: Iterable[str],
    aliases: Sequence[str],
    keywords: Sequence[str],
    excluded: Collection[str],
) -> str | None:
    """Return the strongest name-based match for one semantic role."""
    skipped_columns = set(excluded) | INTERNAL_COLUMNS
    best_column: str | None = None
    best_score = 0

    for column_name in columns:
        if column_name in skipped_columns:
            continue
        score = _name_similarity_score(column_name, aliases=aliases, keywords=keywords)
        if score > best_score:
            best_score = score
            best_column = column_name

    if best_score < NAME_SCORE_THRESHOLD:
        return None
    return best_column


def _name_similarity_score(
    column_name: str,
    aliases: Sequence[str],
    keywords: Sequence[str],
) -> int:
    """Score how well a normalized column name matches a semantic role."""
    normalized_name = _slugify(column_name)
    name_tokens = {token for token in normalized_name.split("_") if token}
    keyword_tokens = {_slugify(keyword) for keyword in keywords}
    best_score = 0

    for alias in aliases:
        normalized_alias = _slugify(alias)
        alias_tokens = {token for token in normalized_alias.split("_") if token}
        if normalized_name == normalized_alias:
            return 100
        if normalized_alias and normalized_alias in normalized_name:
            best_score = max(best_score, 70)

        overlap_count = len(name_tokens & alias_tokens)
        if not overlap_count:
            continue

        overlap_score = overlap_count * 22
        if alias_tokens and alias_tokens.issubset(name_tokens):
            overlap_score += 18
        best_score = max(best_score, overlap_score)

    keyword_score = sum(6 for keyword in keyword_tokens if keyword in name_tokens)
    return best_score + keyword_score


def _is_exact_alias_match(column_name: str, aliases: Sequence[str]) -> bool:
    """Return whether a column name exactly matches one declared alias."""
    normalized_name = _slugify(column_name)
    normalized_aliases = {_slugify(alias) for alias in aliases}
    return normalized_name in normalized_aliases


def _find_amount_by_content(
    dataframe: pd.DataFrame,
    excluded: Collection[str],
) -> str | None:
    """Infer an amount column from numeric content when names are ambiguous."""
    candidates: list[tuple[float, str]] = []
    for column_name in _column_names(dataframe):
        if _skip_candidate(column_name, excluded):
            continue
        score = _amount_content_score(_column_series(dataframe, column_name), column_name)
        if score > 0.0:
            candidates.append((score, column_name))
    return _pick_clear_candidate(candidates, min_score=AMOUNT_SCORE_THRESHOLD)


def _find_date_by_content(
    dataframe: pd.DataFrame,
    excluded: Collection[str],
) -> str | None:
    """Infer a date column from date-like content when names are ambiguous."""
    candidates: list[tuple[float, str]] = []
    for column_name in _column_names(dataframe):
        if _skip_candidate(column_name, excluded):
            continue
        score = _date_content_score(_column_series(dataframe, column_name), column_name)
        if score > 0.0:
            candidates.append((score, column_name))
    return _pick_clear_candidate(candidates, min_score=DATE_SCORE_THRESHOLD)


def _find_flow_by_content(
    dataframe: pd.DataFrame,
    excluded: Collection[str],
) -> str | None:
    """Infer a flow/category column from categorical text values."""
    candidates: list[tuple[float, str]] = []
    for column_name in _column_names(dataframe):
        if _skip_candidate(column_name, excluded):
            continue
        score = _flow_content_score(_column_series(dataframe, column_name), column_name)
        if score > 0.0:
            candidates.append((score, column_name))
    return _pick_clear_candidate(candidates, min_score=FLOW_SCORE_THRESHOLD)


def _find_pme_by_content(
    dataframe: pd.DataFrame,
    excluded: Collection[str],
) -> str | None:
    """Infer an entity column from text values when names are not explicit."""
    candidates: list[tuple[float, str]] = []
    for column_name in _column_names(dataframe):
        if _skip_candidate(column_name, excluded):
            continue
        score = _pme_content_score(_column_series(dataframe, column_name), column_name)
        if score > 0.0:
            candidates.append((score, column_name))
    return _pick_clear_candidate(candidates, min_score=PME_SCORE_THRESHOLD)


def _skip_candidate(column_name: str, excluded: Collection[str]) -> bool:
    """Return whether a column should be skipped from semantic inference."""
    return column_name in set(excluded) | INTERNAL_COLUMNS


def _amount_content_score(series: pd.Series, column_name: str) -> float:
    """Score how plausible a series is for an amount field."""
    if _date_parse_ratio(series) >= 0.75:
        return 0.0

    numeric_ratio, parsed_numeric = _numeric_parse_ratio(series)
    if numeric_ratio < 0.75:
        return 0.0

    unique_values = int(parsed_numeric.nunique(dropna=True))
    if unique_values < 2:
        return 0.0

    score = numeric_ratio * 10.0 + min(unique_values, 10) * 0.2

    name_tokens = {token for token in _slugify(column_name).split("_") if token}
    if name_tokens & {"id", "code", "numero", "num", "phone", "telephone"}:
        score -= 4.0
    return score


def _date_content_score(series: pd.Series, column_name: str) -> float:
    """Score how plausible a series is for a date field."""
    date_ratio = _date_parse_ratio(series)
    if date_ratio < 0.75:
        return 0.0

    score = date_ratio * 10.0
    name_tokens = {token for token in _slugify(column_name).split("_") if token}
    if name_tokens & {"date", "periode", "timestamp", "month", "mois"}:
        score += 2.0
    return score


def _flow_content_score(series: pd.Series, column_name: str) -> float:
    """Score how plausible a series is for a transaction-flow/category field."""
    text_values = _text_values(series)
    if text_values.empty:
        return 0.0

    if _date_parse_ratio(series) >= 0.75:
        return 0.0

    numeric_ratio, _ = _numeric_parse_ratio(series)
    if numeric_ratio >= 0.75:
        return 0.0

    distinct_count = int(text_values.nunique(dropna=True))
    distinct_ratio = distinct_count / max(len(text_values), 1)
    if distinct_count < 2 or distinct_ratio > 0.65:
        return 0.0

    score = min(distinct_count, 12) * 0.25 + (1.0 - distinct_ratio) * 4.0
    sample_values = cast(list[object], text_values.head(50).tolist())
    value_text = " ".join(str(value).lower() for value in sample_values)
    if any(keyword in value_text for keyword in FLOW_VALUE_HINTS):
        score += 2.5

    name_tokens = {token for token in _slugify(column_name).split("_") if token}
    if name_tokens & {"flux", "flow", "nature", "operation", "mouvement", "sens"}:
        score += 1.5
    return score


def _pme_content_score(series: pd.Series, column_name: str) -> float:
    """Score how plausible a series is for a company or beneficiary field."""
    text_values = _text_values(series)
    if text_values.empty:
        return 0.0

    if _date_parse_ratio(series) >= 0.75:
        return 0.0

    numeric_ratio, _ = _numeric_parse_ratio(series)
    if numeric_ratio >= 0.75:
        return 0.0

    distinct_count = int(text_values.nunique(dropna=True))
    distinct_ratio = distinct_count / max(len(text_values), 1)
    if distinct_count < 2 or distinct_ratio < 0.15:
        return 0.0

    score = min(distinct_count, 20) * 0.2 + min(distinct_ratio, 1.0) * 3.0
    name_tokens = {token for token in _slugify(column_name).split("_") if token}
    if name_tokens & {"pme", "entreprise", "societe", "client", "beneficiaire"}:
        score += 2.0
    if name_tokens & {"region", "flux", "flow", "date", "montant", "amount"}:
        score -= 3.0
    return score


def _pick_clear_candidate(
    candidates: Sequence[tuple[float, str]],
    min_score: float,
) -> str | None:
    """Select a candidate only when the confidence gap is sufficient."""
    if not candidates:
        return None

    ordered_candidates = sorted(candidates, reverse=True)
    best_score, best_name = ordered_candidates[0]
    if best_score < min_score:
        return None

    if len(ordered_candidates) == 1:
        return best_name

    second_best_score = ordered_candidates[1][0]
    if best_score - second_best_score < 0.75:
        return None

    return best_name


def _numeric_parse_ratio(series: pd.Series) -> tuple[float, pd.Series]:
    """Return parsed numeric ratio over non-empty cells and the parsed values."""
    text_values = _text_values(series)
    if text_values.empty:
        return 0.0, pd.Series(dtype="float64")

    parsed_numeric = _normalize_amounts(text_values)
    ratio = float(parsed_numeric.notna().mean())
    return ratio, parsed_numeric


def _date_parse_ratio(series: pd.Series) -> float:
    """Return date-parse ratio over non-empty cells."""
    text_values = _text_values(series)
    if text_values.empty:
        return 0.0

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        parsed_dates = pd.to_datetime(text_values, errors="coerce", dayfirst=True)
    return float(parsed_dates.notna().mean())


def _text_values(series: pd.Series) -> pd.Series:
    """Normalize a series to non-empty text values."""
    text_series = series.astype("string").str.strip()
    blank_mask = text_series.str.len().fillna(0).eq(0)
    text_series = text_series.mask(blank_mask, pd.NA)
    return text_series.dropna()


def _build_missing_column_message(column_role: str, columns: Sequence[str]) -> str:
    """Build a clear inference error message with detected columns."""
    formatted_columns = ", ".join(columns) if columns else "aucune colonne"
    return (
        "Impossible d'identifier automatiquement la colonne "
        f"{column_role} a partir des noms et du contenu. "
        f"Colonnes detectees: {formatted_columns}."
    )


def _normalize_amounts(series: pd.Series) -> pd.Series:
    """Parse financial amounts to numeric series."""
    text_series = series.astype("string").str.replace(" ", "", regex=False)
    text_series = text_series.str.replace(",", ".", regex=False)
    text_series = text_series.str.replace(r"[^0-9.\-]", "", regex=True)
    normalized_values: list[object] = list(cast(Iterable[object], text_series))
    numeric_values = pd.to_numeric(normalized_values, errors="coerce")
    return pd.Series(numeric_values, index=series.index, dtype="float64")


def _normalize_dates(series: pd.Series) -> pd.Series:
    """Normalize date formats to YYYY-MM-DD and impute missing values."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        parsed_dates = pd.to_datetime(series, errors="coerce", dayfirst=True)
    if parsed_dates.notna().any():
        fallback_date = parsed_dates.dropna().iloc[0]
    else:
        fallback_date = pd.Timestamp.today().normalize()

    normalized_dates = parsed_dates.fillna(fallback_date).dt.strftime("%Y-%m-%d")
    return normalized_dates.astype("string")


def _clean_text_series(series: pd.Series, default_value: str) -> pd.Series:
    """Trim text values and fill missing entries."""
    text_series = series.astype("string").str.strip()
    blank_mask = text_series.str.len().fillna(0).eq(0)
    text_series = text_series.mask(blank_mask, pd.NA)
    return text_series.fillna(default_value).astype("string")


def _slugify(value: str) -> str:
    """Convert a string to normalized snake_case ASCII."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_only).strip("_").lower()
    return slug or "colonne"


def _deduplicate_names(names: Sequence[str]) -> list[str]:
    """Guarantee unique column names after slugification."""
    counts: dict[str, int] = {}
    deduplicated: list[str] = []
    for name in names:
        current_count = counts.get(name, 0)
        if not current_count:
            deduplicated_name = name
        else:
            deduplicated_name = f"{name}_{current_count + 1}"
        counts[name] = current_count + 1
        deduplicated.append(deduplicated_name)

    return deduplicated
