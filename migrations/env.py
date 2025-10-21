import sys
import os

# Lấy đường dẫn tuyệt đối tới thư mục gốc của project
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from app.db import Base
from app.models import user  # để Alembic nhận tất cả models
from app.core.config import settings


# cấu hình log
config = context.config
fileConfig(config.config_file_name)

# đường dẫn DB lấy từ .env
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
