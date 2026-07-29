import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# 1. Add current directory to sys.path so Alembic can find your app modules
sys.path.append(os.getcwd())

# 2. Load environment variables from .env file
load_dotenv()

# 3. Import Base and models for autogenerate support
from db.database import Base
import db.models  # Ensures all models (User, ChatRoom, ChatMessage, UploadedFile) are registered

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# 4. Dynamically set the database URL from .env or fallback to local SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 5. Assign Base metadata so Alembic detects model changes
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
            render_as_batch=True
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()