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


def test_0001_upgrade_preserves_existing_messages_and_allocates_card_sequence(
    tmp_path, monkeypatch
):
    import sqlalchemy as sa

    from echoloom.db import allocate_timeline, sessions

    monkeypatch.chdir(Path(__file__).resolve().parents[2])
    url = f"sqlite:///{tmp_path / 'legacy.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    config = Config("alembic.ini")
    command.upgrade(config, "0001")
    engine = make_engine(url)
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO characters (id,original_description,current_profile_version,created_at,updated_at) VALUES ('c','original',1,'2026-01-01','2026-01-01')"
            )
        )
        conn.execute(
            sa.text(
                "INSERT INTO conversations (id,character_id,created_at,updated_at) VALUES ('v','c','2026-01-01','2026-01-01')"
            )
        )
        for identifier, role in (("a", "user"), ("b", "assistant")):
            conn.execute(
                sa.text(
                    "INSERT INTO messages (id,conversation_id,request_id,role,content,profile_version,created_at) VALUES (:id,'v','r',:role,:content,1,'2026-01-01')"
                ),
                {"id": identifier, "role": role, "content": f"old-{role}"},
            )
    command.upgrade(config, "head")
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                "SELECT id,content,timeline_order FROM messages ORDER BY timeline_order"
            )
        ).all()
        assert rows == [("a", "old-user", 1), ("b", "old-assistant", 2)]
    with sessions(engine)() as db:
        assert allocate_timeline(db, "v") == [3]
        db.commit()
    command.upgrade(config, "head")
    with engine.connect() as conn:
        assert (
            conn.scalar(
                sa.text("SELECT next_timeline_order FROM conversations WHERE id='v'")
            )
            == 3
        )
    engine.dispose()
