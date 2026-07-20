"""Base declarativa y utilidades compartidas por los modelos.

Convención de fechas: se almacenan datetimes *naive* en UTC. SQLite no conserva
tzinfo, por lo que mezclar aware/naive rompería las comparaciones en las queries.
`utcnow()` es la única fuente de "ahora" del dominio.
"""

from datetime import date, datetime, timezone

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Nombres de constraints predecibles: necesarios para migraciones con Alembic.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    """Instante actual en UTC, sin tzinfo (ver nota del módulo)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def today() -> date:
    return utcnow().date()


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """Auditoría mínima de creación/actualización."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )
