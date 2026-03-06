"""Ingestion utilities for CSV and Excel financial files."""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Sequence, cast

import pandas as pd

from scripts.types import SourceFile, UploadedFileLike

SUPPORTED_EXTENSIONS: set[str] = {".csv", ".xlsx", ".xls"}
KNOWN_REGIONS: dict[str, str] = {
    "nord": "Nord",
    "sud": "Sud",
    "est": "Est",
    "ouest": "Ouest",
    "centre": "Centre",
    "central": "Centre",
    "littoral": "Littoral",
}


def build_sources_from_uploads(uploaded_files: Sequence[UploadedFileLike]) -> list[SourceFile]:
    """Convert uploaded files to `SourceFile` objects."""
    sources: list[SourceFile] = []
    for uploaded_file in uploaded_files:
        sources.append(
            SourceFile(
                filename=uploaded_file.name,
                content=uploaded_file.getvalue(),
            )
        )
    return sources


def load_sources_from_directory(directory_path: Path) -> list[SourceFile]:
    """Load all supported files from a local directory."""
    if not directory_path.exists():
        raise ValueError(f"Le dossier {directory_path} est introuvable.")

    sources: list[SourceFile] = []
    for file_path in sorted(directory_path.iterdir()):
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        sources.append(SourceFile(filename=file_path.name, content=file_path.read_bytes()))

    return sources


def infer_region_from_filename(filename: str) -> str:
    """Infer region from a filename."""
    stem = Path(filename).stem.lower()
    tokens = re.split(r"[_\-\s]+", stem)

    for token in tokens:
        if token in KNOWN_REGIONS:
            return KNOWN_REGIONS[token]

    first_token = next((token for token in tokens if token), "")
    return first_token.title() if first_token else "Inconnue"


def consolidate_files(source_files: Sequence[SourceFile]) -> tuple[pd.DataFrame, list[str]]:
    """
    Read and merge all source files into a single dataframe.

    Returns merged dataframe and a list of non-blocking warnings.
    """
    if not source_files:
        raise ValueError("Aucun fichier recu pour la consolidation.")

    frames: list[pd.DataFrame] = []
    warnings: list[str] = []

    for source_file in source_files:
        try:
            frame = read_source_file(source_file)
        except (ValueError, pd.errors.ParserError, ImportError) as exc:
            warnings.append(f"{source_file.filename}: {exc}")
            continue

        if frame.empty:
            warnings.append(f"{source_file.filename}: fichier vide ignore.")
            continue

        frames.append(frame)

    if not frames:
        raise ValueError("Aucun fichier valide n'a pu etre consolide.")

    merged = pd.concat(frames, ignore_index=True, sort=False)
    merged = merged.dropna(axis=0, how="all").reset_index(drop=True)
    return merged, warnings


def read_source_file(source_file: SourceFile) -> pd.DataFrame:
    """Read one source file into a dataframe."""
    extension = Path(source_file.filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("format non supporte (CSV, XLSX, XLS uniquement).")

    if extension == ".csv":
        frame = _read_csv(source_file.content)
    else:
        frame = _read_excel(source_file.content)

    frame.columns = [str(column_name).strip() for column_name in cast(list[object], list(frame.columns))]
    frame["source_file"] = source_file.filename
    frame["region"] = infer_region_from_filename(source_file.filename)
    return frame


def _read_csv(content: bytes) -> pd.DataFrame:
    """Read a CSV payload with delimiter auto-detection."""
    delimiter = _detect_csv_delimiter(content)
    buffer = io.BytesIO(content)
    return pd.read_csv(
        buffer,
        sep=delimiter,
        keep_default_na=True,
        na_values=["", "NA", "N/A", "null", "None"],
    )


def _read_excel(content: bytes) -> pd.DataFrame:
    """Read an Excel payload."""
    buffer = io.BytesIO(content)
    return pd.read_excel(buffer)


def _detect_csv_delimiter(content: bytes) -> str:
    """Detect CSV delimiter from payload sample."""
    sample = content[:4096].decode("utf-8", errors="ignore")
    if not sample.strip():
        return ","

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
    except csv.Error:
        return ","

    return dialect.delimiter
