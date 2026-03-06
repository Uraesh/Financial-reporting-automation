"""Switch Streamlit theme by copying the matching config.toml, then restart."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

THEMES_DIR = Path(__file__).resolve().parent / "themes"
CONFIG_DIR = Path(__file__).resolve().parent / ".streamlit"

THEME_FILES: dict[str, str] = {
    "Finance Pro": "config_finance_pro.toml",
    "Dark Mode": "config_dark_mode.toml",
    "Executive Mode": "config_executive_mode.toml",
}


def switch_theme(theme_name: str) -> None:
    """Copy the selected theme config and relaunch the dashboard."""
    if theme_name not in THEME_FILES:
        raise ValueError(
            f"Theme inconnu: '{theme_name}'. "
            f"Choisir parmi: {list(THEME_FILES.keys())}"
        )

    src = THEMES_DIR / THEME_FILES[theme_name]
    dst = CONFIG_DIR / "config.toml"

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)
    print(f"Theme applique: {theme_name} -> {dst}")

    subprocess.run(  # noqa: S603
        [sys.executable, "-m", "streamlit", "run", "dashboard/app.py"],
        check=True,
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:  # noqa: PLR2004
        print("Usage: python switch_theme.py <theme>")
        print(f"Themes disponibles: {list(THEME_FILES.keys())}")
        sys.exit(1)

    switch_theme(sys.argv[1])
