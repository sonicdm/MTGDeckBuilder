from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from mtg_deck_builder.db.models import Base as AppBase
from mtg_deck_builder.db.mtgjson_models.base import MTGJSONBase
import sys
import os

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = [AppBase.metadata, MTGJSONBase.metadata]

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# Only include tables in our models
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table":
        all_model_tables = set()
        for meta in target_metadata:
            all_model_tables.update(meta.tables.keys())
        return name in all_model_tables
    return True

# Prompt for confirmation if a migration would drop a table
from alembic.operations.ops import DropTableOp

def process_revision_directives(context, revision, directives):
    script = directives[0]
    if hasattr(script, 'upgrade_ops'):
        for op in script.upgrade_ops.ops:
            if isinstance(op, DropTableOp):
                confirm = input(f"WARNING: Migration will drop table '{op.to_table.name}'. Continue? [y/N]: ")
                if confirm.lower() != 'y':
                    print("Aborting migration.")
                    exit(1)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_object=include_object,
        process_revision_directives=process_revision_directives,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            process_revision_directives=process_revision_directives,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
