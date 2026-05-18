import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Path fix ────────────────────────────────────────────────────────────────
# env.py lives at: project_root/app/alembic/env.py
# Going up 2 levels lands at project_root, which is what Python needs
# to resolve imports like "from app.core.config import settings"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# ── App imports ─────────────────────────────────────────────────────────────
from app.core.config import settings
from app.db.database import Base

# Import every model so SQLAlchemy registers them on Base.metadata
# Without these, autogenerate won't detect your tables
from app.models import userModel, teamModel, ticketModel, commentModel

# ── Alembic config ──────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Pull DATABASE_URL from your settings (reads from app/.env)
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


# ── Offline mode ────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode ─────────────────────────────────────────────────────────────
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()