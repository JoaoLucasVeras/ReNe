"""Run-directory and tabular logging helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd


def make_run_dir(root: str | Path, prefix: str) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = Path(root) / f"{prefix}-{stamp}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def save_json(path: str | Path, data: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def save_rows(path: str | Path, rows: list[dict[str, Any]]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False)
