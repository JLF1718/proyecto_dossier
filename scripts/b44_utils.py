"""
b44_utils.py — Utilidad para leer, actualizar y recodificar archivos .b44
Proyecto Dossier · CONTROL DE JUNTAS INSPECCIONADAS
─────────────────────────────────────────────────────────────────────────────
Flujo de uso:
    data = b44_load("juntas_raw.b44")          # decodifica el payload
    data["registros"][0]["juntas_liberadas"] = 30  # modifica lo que necesites
    b44_save(data, "juntas_raw.b44")           # re-codifica y guarda
─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

# ── Alfabeto Base44 ────────────────────────────────────────────────────────────
# 44 caracteres ASCII seguros: sin comillas, sin barras, sin acentos, URL-safe
ALPHABET: str = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGH"
BASE: int = len(ALPHABET)  # 44


# ── Codec ─────────────────────────────────────────────────────────────────────

def _encode(data: bytes) -> str:
    """Convierte bytes a cadena Base44."""
    if not data:
        return ""
    n = int.from_bytes(data, "big")
    if n == 0:
        return ALPHABET[0]
    digits: list[str] = []
    while n:
        digits.append(ALPHABET[n % BASE])
        n //= BASE
    pad = len(data) - len(data.lstrip(b"\x00"))
    return ALPHABET[0] * pad + "".join(reversed(digits))


def _decode(s: str) -> bytes:
    """Convierte cadena Base44 a bytes."""
    if not s:
        return b""
    n = 0
    for ch in s:
        n = n * BASE + ALPHABET.index(ch)
    byte_length = math.ceil(len(s) * math.log(BASE) / math.log(256))
    result = n.to_bytes(byte_length, "big").lstrip(b"\x00") or b"\x00"
    pad = len(s) - len(s.lstrip(ALPHABET[0]))
    return b"\x00" * pad + result


def _checksum(data: bytes) -> int:
    return sum(data) % (2 ** 32)


# ── API pública ───────────────────────────────────────────────────────────────

def b44_load(path: str | Path) -> dict[str, Any]:
    """
    Carga y decodifica un archivo .b44.

    Returns:
        dict con las claves: schema_version, encoding, metadata, registros
    """
    path = Path(path)
    with path.open("r", encoding="ascii") as f:
        wrapper = json.load(f)

    raw_bytes = _decode(wrapper["payload"])

    # Verificar integridad
    calc = _checksum(raw_bytes)
    stored = wrapper.get("checksum_sum32")
    if stored is not None and calc != stored:
        raise ValueError(
            f"Checksum inválido: esperado {stored}, calculado {calc}. "
            "El archivo puede estar corrupto."
        )

    return json.loads(raw_bytes.decode("utf-8"))


def b44_save(data: dict[str, Any], path: str | Path) -> None:
    """
    Re-codifica `data` en Base44 y sobreescribe (o crea) el archivo .b44.

    El campo metadata.fecha_extraccion se actualiza automáticamente.
    """
    path = Path(path)

    # Actualizar timestamp
    if "metadata" in data:
        data["metadata"]["fecha_extraccion"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

    payload_bytes = json.dumps(
        data, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    b44_payload = _encode(payload_bytes)

    wrapper = {
        "b44_version": "1.0",
        "alphabet": ALPHABET,
        "byte_length": len(payload_bytes),
        "checksum_sum32": _checksum(payload_bytes),
        "created_at": datetime.now().isoformat(),
        "payload": b44_payload,
    }

    with path.open("w", encoding="ascii") as f:
        json.dump(wrapper, f, indent=2, ensure_ascii=True)


def b44_to_dataframe(path: str | Path):
    """
    Carga el archivo .b44 y devuelve un pandas.DataFrame con los registros.

    Requires: pandas
    """
    import pandas as pd  # noqa: PLC0415

    data = b44_load(path)
    return pd.DataFrame(data["registros"])


def b44_update_sue(
    path: str | Path,
    sue: str,
    **kwargs: int | float | None,
) -> None:
    """
    Actualiza los campos de un SUE específico y guarda el archivo.

    Ejemplo:
        b44_update_sue("juntas_raw.b44", "SUE_80",
                       juntas_liberadas=35,
                       juntas_pendientes=103)
    """
    data = b44_load(path)
    found = False
    for rec in data["registros"]:
        if rec["sue"] == sue:
            for k, v in kwargs.items():
                if k not in rec:
                    raise KeyError(
                        f"Campo '{k}' no existe en el esquema. "
                        f"Campos válidos: {list(rec.keys())}"
                    )
                rec[k] = v
            # Recalcular campos derivados si hay suficiente info
            total = rec.get("total_juntas") or 0
            lib   = rec.get("juntas_liberadas") or 0
            rec_  = rec.get("juntas_rechazadas") or 0
            rec["juntas_inspeccionadas"] = lib + rec_
            if total:
                pend = rec.get("juntas_pendientes") or 0
                ratio = round(pend / total, 6)
                rec["ratio_pendientes_sobre_total"] = ratio
                rec["pct_pendiente_inspeccion"]     = round(ratio * 100, 2)
                rec["pct_avance_inspeccion"]         = round((1 - ratio) * 100, 2)
            found = True
            break
    if not found:
        raise ValueError(f"SUE '{sue}' no encontrado. Disponibles: "
                         f"{[r['sue'] for r in data['registros']]}")
    b44_save(data, path)
    print(f"✓ {sue} actualizado y guardado en {path}")


def b44_add_sue(path: str | Path, record: dict[str, Any]) -> None:
    """
    Agrega un nuevo registro SUE al archivo .b44.

    El dict `record` debe incluir al menos: sue, total_juntas, juntas_liberadas,
    juntas_rechazadas, juntas_pendientes, fuente_hoja, fuente_archivo.
    """
    REQUIRED = {"sue", "total_juntas", "fuente_hoja", "fuente_archivo"}
    missing = REQUIRED - record.keys()
    if missing:
        raise ValueError(f"Campos requeridos faltantes: {missing}")

    data = b44_load(path)
    existing = {r["sue"] for r in data["registros"]}
    if record["sue"] in existing:
        raise ValueError(
            f"'{record['sue']}' ya existe. Use b44_update_sue() para modificarlo."
        )

    # Completar campos derivados
    total = record.get("total_juntas") or 0
    lib   = record.get("juntas_liberadas") or 0
    rec_  = record.get("juntas_rechazadas") or 0
    pend  = record.get("juntas_pendientes") or 0
    record.setdefault("juntas_inspeccionadas", lib + rec_)
    if total:
        ratio = round(pend / total, 6)
        record.setdefault("ratio_pendientes_sobre_total", ratio)
        record.setdefault("pct_pendiente_inspeccion",     round(ratio * 100, 2))
        record.setdefault("pct_avance_inspeccion",         round((1 - ratio) * 100, 2))

    data["registros"].append(record)
    data["metadata"]["total_sues"] = len(data["registros"])
    b44_save(data, path)
    print(f"✓ {record['sue']} agregado. Total SUEs: {data['metadata']['total_sues']}")


# ── CLI mínimo ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    cmd  = args[0]
    file = args[1] if len(args) > 1 else "juntas_raw.b44"

    if cmd == "inspect":
        data = b44_load(file)
        print(f"Schema: {data['schema_version']}  |  Hoja: {data['metadata']['hoja']}")
        print(f"Extracción: {data['metadata']['fecha_extraccion']}")
        print(f"SUEs: {data['metadata']['total_sues']}")
        for r in data["registros"]:
            avance = r.get("pct_avance_inspeccion", "?")
            print(f"  {r['sue']:12s}  total={r['total_juntas']:5}  "
                  f"liberadas={str(r['juntas_liberadas']):5}  "
                  f"pendientes={str(r['juntas_pendientes']):5}  "
                  f"avance={avance}%")

    elif cmd == "to-json":
        data = b44_load(file)
        out  = Path(file).with_suffix(".decoded.json")
        with out.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Decodificado → {out}")

    else:
        print(f"Comandos: inspect <file.b44> | to-json <file.b44>")
