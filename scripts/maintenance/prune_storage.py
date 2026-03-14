#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Poda segura de almacenamiento para mantener el proyecto ligero."""

from __future__ import annotations

import shutil
from pathlib import Path


BASE = Path(__file__).resolve().parents[2]


def _size_mb(path: Path) -> float:
    if path.is_file():
        return round(path.stat().st_size / (1024 * 1024), 2)
    total = 0
    for file_path in path.rglob("*"):
        if file_path.is_file():
            total += file_path.stat().st_size
    return round(total / (1024 * 1024), 2)


def _delete_path(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        path.unlink(missing_ok=True)
        return 1

    removed = 0
    for item in sorted(path.rglob("*"), reverse=True):
        if item.is_file():
            item.unlink(missing_ok=True)
            removed += 1
        elif item.is_dir():
            try:
                item.rmdir()
            except OSError:
                pass
    try:
        path.rmdir()
    except OSError:
        shutil.rmtree(path, ignore_errors=True)
    return removed


def _prune_files(directory: Path, pattern: str, keep: int) -> int:
    if not directory.exists():
        return 0
    files = sorted(
        [p for p in directory.glob(pattern) if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    removed = 0
    for old_file in files[keep:]:
        old_file.unlink(missing_ok=True)
        removed += 1
    return removed


def _prune_recursive_files(directory: Path, pattern: str, keep: int) -> int:
    if not directory.exists():
        return 0
    removed = 0
    grouped: dict[Path, list[Path]] = {}
    for file_path in directory.rglob(pattern):
        if file_path.is_file():
            grouped.setdefault(file_path.parent, []).append(file_path)
    for _, files in grouped.items():
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for old_file in files[keep:]:
            old_file.unlink(missing_ok=True)
            removed += 1
    return removed


def _prune_output() -> dict[str, int]:
    output_dir = BASE / "output"
    tablas = output_dir / "tablas"
    dashboards = output_dir / "dashboards"
    historico = output_dir / "historico"

    removed = {
        "tablas": 0,
        "dashboards": 0,
        "historico": 0,
        "cache_dirs": 0,
    }

    if tablas.exists():
        html_tablas = sorted(
            [p for p in tablas.glob("*.html") if p.is_file() and "baysa" in p.name.lower() and "jamar" not in p.name.lower()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        conservar = set(html_tablas[:1])
        for file_path in tablas.glob("*.html"):
            if file_path not in conservar:
                file_path.unlink(missing_ok=True)
                removed["tablas"] += 1

    removed["dashboards"] = _prune_files(dashboards, "*.html", keep=1)
    removed["historico"] = _prune_recursive_files(historico, "*.html", keep=1)

    for cache_dir in [output_dir / ".cache", output_dir / "cache", output_dir / "cache_backups"]:
        removed["cache_dirs"] += _delete_path(cache_dir)

    return removed


def _prune_data_backups() -> dict[str, int]:
    removed = {
        "csv_backups": 0,
        "historico_excels": 0,
    }
    for contractor_dir in [BASE / "data" / "contratistas" / "BAYSA", BASE / "data" / "contratistas" / "JAMAR"]:
        removed["csv_backups"] += _prune_files(contractor_dir, "*_backup_*.csv", keep=5)

    data_historico = BASE / "data" / "historico"
    removed["historico_excels"] = _prune_recursive_files(data_historico, "*.xlsx", keep=3)
    return removed


def _prune_python_artifacts() -> dict[str, int]:
    removed = {
        "__pycache__": 0,
        "pytest_cache": 0,
    }
    for pycache_dir in BASE.rglob("__pycache__"):
        removed["__pycache__"] += _delete_path(pycache_dir)

    for cache_dir in BASE.rglob(".pytest_cache"):
        removed["pytest_cache"] += _delete_path(cache_dir)

    return removed


def main() -> int:
    before_output = _size_mb(BASE / "output")
    before_data = _size_mb(BASE / "data")

    output_removed = _prune_output()
    data_removed = _prune_data_backups()
    python_removed = _prune_python_artifacts()

    after_output = _size_mb(BASE / "output")
    after_data = _size_mb(BASE / "data")

    print("\n" + "=" * 64)
    print("PODA SEGURA DE ALMACENAMIENTO")
    print("=" * 64)
    print(f"Output antes: {before_output:.2f} MB")
    print(f"Output despues: {after_output:.2f} MB")
    print(f"Data antes: {before_data:.2f} MB")
    print(f"Data despues: {after_data:.2f} MB")
    print("\nElementos podados:")
    print(f"  • tablas HTML eliminadas: {output_removed['tablas']}")
    print(f"  • dashboards HTML eliminados: {output_removed['dashboards']}")
    print(f"  • historico HTML eliminados: {output_removed['historico']}")
    print(f"  • archivos de cache eliminados: {output_removed['cache_dirs']}")
    print(f"  • backups CSV eliminados: {data_removed['csv_backups']}")
    print(f"  • excels historicos eliminados: {data_removed['historico_excels']}")
    print(f"  • __pycache__ eliminados: {python_removed['__pycache__']}")
    print(f"  • .pytest_cache eliminados: {python_removed['pytest_cache']}")
    print("=" * 64 + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())