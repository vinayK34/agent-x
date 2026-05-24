import pytest
from httpx import ASGITransport, AsyncClient

from app.db import init_db
from app.main import create_app


@pytest.fixture
async def client(tmp_path, monkeypatch):
    db_path = tmp_path / "t.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    # Re-import to pick up env
    from app import config
    config.get_settings.cache_clear()  # type: ignore[attr-defined]

    app = create_app()
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c
