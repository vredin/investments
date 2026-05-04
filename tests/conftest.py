import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load .env before reading DATABASE_URL from os.environ (pydantic-settings does not
# populate os.environ — dotenv does).
load_dotenv()

from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

# Use a separate test database. Override DATABASE_URL with _test suffix if needed.
_TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get("DATABASE_URL", "").replace("/investments", "/investments_test"),
)


def _db_available() -> bool:
    """Return True if the test database is reachable."""
    if not _TEST_DB_URL:
        return False
    try:
        eng = create_engine(_TEST_DB_URL, pool_pre_ping=True)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="PostgreSQL test database not available",
)


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(_TEST_DB_URL, pool_pre_ping=True)
    # Ensure pgvector extension exists before table creation
    with eng.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def db_session(engine):
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
