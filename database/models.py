"""
Database Models
================
SQLAlchemy ORM models for the QA Platform.

Tables:
  - dossiers       : construction package records (mirrors CSV schema)
  - weld_joints    : welding inspection records
  - concrete_tests : concrete QC test results
  - nc_forms       : Non-Conformance reports
  - audit_log      : status change audit trail
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey,
    Index, Integer, String, Text, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.session import Base


# ── Dossier (construction QA package) ─────────────────────────────────────────

class Dossier(Base):
    __tablename__ = "dossiers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bloque: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    etapa: Mapped[Optional[str]] = mapped_column(String(50))
    estatus: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PLANEADO", index=True
    )
    peso_kg: Mapped[float] = mapped_column(Float, default=0.0)
    peso_liberado_kg: Mapped[Optional[float]] = mapped_column(Float)
    contratista: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entrega: Mapped[Optional[str]] = mapped_column(String(10))   # e.g. S186
    no_revision: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    audit_entries: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="dossier", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_dossiers_contratista_estatus", "contratista", "estatus"),
    )

    def __repr__(self) -> str:
        return f"<Dossier {self.bloque} [{self.estatus}] {self.contratista}>"


# ── Welding record ─────────────────────────────────────────────────────────────

class WeldJoint(Base):
    __tablename__ = "weld_joints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    junta_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    contratista: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    sistema: Mapped[Optional[str]] = mapped_column(String(100))
    proceso: Mapped[Optional[str]] = mapped_column(String(20))      # SMAW, GTAW, FCAW…
    material: Mapped[Optional[str]] = mapped_column(String(100))
    diametro_pulg: Mapped[Optional[float]] = mapped_column(Float)
    espesor_mm: Mapped[Optional[float]] = mapped_column(Float)
    soldador_id: Mapped[Optional[str]] = mapped_column(String(50))
    fecha_soldadura: Mapped[Optional[datetime]] = mapped_column(DateTime)
    fecha_inspeccion: Mapped[Optional[datetime]] = mapped_column(DateTime)
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE", index=True)
    tipo_end: Mapped[Optional[str]] = mapped_column(String(20))     # VT, RT, UT, PT, MT
    resultado_end: Mapped[Optional[str]] = mapped_column(String(20))
    observaciones: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<WeldJoint {self.junta_id} [{self.estado}]>"


# ── Concrete test ─────────────────────────────────────────────────────────────

class ConcreteTest(Base):
    __tablename__ = "concrete_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    muestra_id: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    contratista: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    sistema: Mapped[Optional[str]] = mapped_column(String(100))
    elemento: Mapped[Optional[str]] = mapped_column(String(100))
    fecha_vaciado: Mapped[Optional[datetime]] = mapped_column(DateTime)
    resistencia_disenio_mpa: Mapped[Optional[float]] = mapped_column(Float)
    resistencia_7d_mpa: Mapped[Optional[float]] = mapped_column(Float)
    resistencia_28d_mpa: Mapped[Optional[float]] = mapped_column(Float)
    estado: Mapped[str] = mapped_column(String(20), default="PENDIENTE", index=True)
    observaciones: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def __repr__(self) -> str:
        return f"<ConcreteTest {self.muestra_id} [{self.estado}]>"


# ── Non-Conformance form ───────────────────────────────────────────────────────

class NCForm(Base):
    __tablename__ = "nc_forms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero_nc: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    contratista: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    disciplina: Mapped[str] = mapped_column(String(100), nullable=False)
    sistema: Mapped[Optional[str]] = mapped_column(String(100))
    responsable: Mapped[Optional[str]] = mapped_column(String(100))
    fecha_emision: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    fecha_cierre: Mapped[Optional[datetime]] = mapped_column(DateTime)
    estado: Mapped[str] = mapped_column(String(20), default="ABIERTA", index=True)
    accion_correctiva: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<NCForm {self.numero_nc} [{self.estado}]>"


# ── Audit log ─────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    dossier_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("dossiers.id", ondelete="CASCADE"), index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # dossier/weld/concrete/nc
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    field_changed: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(String(100))
    new_value: Mapped[Optional[str]] = mapped_column(String(100))
    changed_by: Mapped[Optional[str]] = mapped_column(String(100))
    changed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)

    dossier: Mapped[Optional["Dossier"]] = relationship("Dossier", back_populates="audit_entries")

    def __repr__(self) -> str:
        return f"<AuditLog {self.entity_type}:{self.entity_id} {self.field_changed}>"
