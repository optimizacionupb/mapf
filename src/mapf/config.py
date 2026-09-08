from __future__ import annotations

import tomllib
from pathlib import Path

RUTA_CONFIG_DEFECTO = Path(__file__).resolve().parents[2] / 'config.toml'


def cargar_config(path: Path | None = None) -> dict:
    """Carga config.toml desde la raíz del proyecto o la ruta dada."""
    ruta = path if path is not None else RUTA_CONFIG_DEFECTO
    with ruta.open('rb') as f:
        return tomllib.load(f)
