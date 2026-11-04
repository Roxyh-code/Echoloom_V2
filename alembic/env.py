from pathlib import Path

from alembic import context
from echoloom.config import Settings
from echoloom.db import Base, make_engine

settings = Settings()
if settings.database_url.startswith("sqlite:///./"):
    Path(settings.database_url.removeprefix("sqlite:///./")).parent.mkdir(
        parents=True, exist_ok=True
    )
engine = make_engine(settings.database_url)
with engine.connect() as connection:
    context.configure(
        connection=connection, target_metadata=Base.metadata, render_as_batch=True
    )
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
