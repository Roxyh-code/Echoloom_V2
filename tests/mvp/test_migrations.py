from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from alembic import command
from echoloom.db import Base, make_engine


def test_migration_upgrade_repeat_and_downgrade(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[2]
    monkeypatch.chdir(root)
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    engine = make_engine(url)
    assert "character_profiles" in inspect(engine).get_table_names()
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        assert compare_metadata(context, Base.metadata) == []
    engine.dispose()
    command.downgrade(config, "base")
    engine = make_engine(url)
    assert inspect(engine).get_table_names() == ["alembic_version"]
    engine.dispose()
