from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import questionary
from rich.console import Console
from rich.table import Table

from .core import CsvEditorError, apply_changes_by_bloque, get_row_by_bloque, load_csv

DEFAULT_EDIT_FIELDS = [
    "estatus",
    "semana_liberacion_dossier",
    "peso_dossier_kg",
    "total_piezas",
    "in_contract_scope",
]


def _display_value(value: Any) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def _estatus_with_style(value: Any) -> str:
    text = _display_value(value)
    normalized = text.strip().lower()
    if normalized == "approved":
        return f"[green]{text}[/green]"
    if normalized in {"pending", "in_review"}:
        return f"[yellow]{text}[/yellow]"
    return f"[red]{text}[/red]"


def _render_row_preview(console: Console, row: pd.Series) -> None:
    table = Table(title="Vista previa del bloque", show_lines=False)
    table.add_column("Campo")
    table.add_column("Valor")
    for column, value in row.items():
        if column == "estatus":
            display = _estatus_with_style(value)
        else:
            display = _display_value(value)
        table.add_row(str(column), display)
    console.print(table)


def _build_diff(current_row: pd.Series, changes: dict[str, Any]) -> Table:
    table = Table(title="Cambios a guardar")
    table.add_column("Campo")
    table.add_column("Actual")
    table.add_column("Nuevo")

    for field, new_value in changes.items():
        current_value = _display_value(current_row.get(field))
        new_value_display = _display_value(new_value)
        table.add_row(field, current_value, new_value_display)

    return table


def run_tui(
    csv_path: Path = Path("data/processed/baysa_dossiers_clean.csv"),
    schema_path: Path = Path("data/schema.json"),
) -> int:
    console = Console()

    try:
        df = load_csv(csv_path)
        if "bloque" not in df.columns:
            raise CsvEditorError("Column 'bloque' is required")

        unique_bloques = sorted(df["bloque"].dropna().astype("string").unique().tolist())
        if not unique_bloques:
            raise CsvEditorError("No bloques available in CSV")

        selected_bloque = questionary.autocomplete(
            "Selecciona bloque:",
            choices=unique_bloques,
            match_middle=True,
            validate=lambda value: True if value in unique_bloques else "Selecciona un bloque valido",
        ).ask()
        if selected_bloque is None:
            console.print("Operacion cancelada.")
            return 1

        _, current_row = get_row_by_bloque(df, selected_bloque)
        _render_row_preview(console, current_row)
        console.print("estatus: approved|pending|in_review")

        default_checked = [field for field in DEFAULT_EDIT_FIELDS if field in df.columns]
        editable_fields = questionary.checkbox(
            "Selecciona campos a editar:",
            choices=[
                questionary.Choice(title=col, value=col, checked=(col in default_checked))
                for col in df.columns
            ],
        ).ask()

        if editable_fields is None:
            console.print("Operacion cancelada.")
            return 1
        if len(editable_fields) == 0:
            console.print("No se seleccionaron campos. Sin cambios.")
            return 0

        changes: dict[str, Any] = {}
        for field in editable_fields:
            current_text = _display_value(current_row.get(field))
            new_value = questionary.text(
                f"Nuevo valor para {field} (enter mantiene actual):",
                default=current_text,
            ).ask()
            if new_value is None:
                console.print("Operacion cancelada.")
                return 1
            if new_value == "":
                continue
            if new_value != current_text:
                changes[field] = new_value

        if not changes:
            console.print("No hay cambios para guardar.")
            return 0

        console.print(_build_diff(current_row, changes))

        confirmed = questionary.confirm("Guardar cambios?").ask()
        if not confirmed:
            console.print("Operacion cancelada. No se escribio el CSV.")
            return 1

        backup_path = apply_changes_by_bloque(csv_path, schema_path, selected_bloque, changes)
        console.print(f"Guardado OK. Backup: {backup_path}")
        return 0
    except CsvEditorError as exc:
        console.print(f"Error: {exc}")
        return 1
