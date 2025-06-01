from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

from src.config import settings
from src.database import Base
from src.models.vk_account import VKAccountOrm
from src.models.vk_account_cred import VKAccountCredOrm
from src.models.category import CategoryOrm
from src.models.user import UserOrm
from src.models.vk_group import VKGroupOrm
from src.models.celery_task import CeleryTaskOrm
from src.models.clip_list import ClipListOrm
from src.models.vk_clip import VKClipOrm
from src.models.workerpost import WorkerPostOrm
from src.models.schedule_posting import SchedulePostingOrm

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Превращаем async URL в sync
# Например: postgresql+asyncpg://... -> postgresql://...
sync_db_url = settings.DB_URL.replace("postgresql+asyncpg://", "postgresql://")
config.set_main_option("sqlalchemy.url", sync_db_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


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
        dialect_opts={"paramstyle": "named"},
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
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
