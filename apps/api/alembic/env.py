"""Alembic environment configuration."""

from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path
from sys import path as sys_path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure the API src is on the Python path
_api_src = Path(__file__).resolve().parents[1] / "src"
if str(_api_src) not in sys_path:
    sys_path.insert(0, str(_api_src))

# Add packages to the path so imports work
_packages = Path(__file__).resolve().parents[4] / "packages"
for pkg_subdir in [
    "case-schema/src",
    "domain/src",
    "simulation-engine/src",
]:
    pkg_path = str(_packages / pkg_subdir)
    if pkg_path not in sys_path:
        sys_path.insert(0, pkg_path)

# Alembic Config
config = context.config

# Set up logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import models so Base.metadata is populated
from afcs_api import models  # noqa: F401, E402
from afcs_api.db import Base  # noqa: E402

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
