import os
import sys
from pathlib import Path
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Add apps/api to sys.path
api_root = str(Path(__file__).resolve().parent.parent)
if api_root not in sys.path:
    sys.path.insert(0, api_root)

# Set test environment variables
os.environ["SECRET_KEY"] = "test_environment_secret_key_at_least_32_chars_long_12345"
os.environ["CSRF_SECRET_KEY"] = "test_environment_csrf_key_at_least_32_chars_long_67890"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.core.rate_limiter import login_rate_limiter
from app.core.security import get_password_hash, generate_csrf_token
from app.db.base import Base
from app.db.session import get_db
import app.db.session as db_module
from app.main import app
from app.models.user import User
from app.models.system_state import SystemState

# In-memory SQLite for testing with StaticPool
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Point db_module to the test engine
db_module.engine = test_engine
db_module.SessionLocal = TestingSessionLocal


@pytest.fixture(autouse=True)
def setup_database():
    """Create all tables before each test and drop after."""
    Base.metadata.create_all(bind=test_engine)
    login_rate_limiter.reset()
    yield
    Base.metadata.drop_all(bind=test_engine)
    login_rate_limiter.reset()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app, base_url="http://localhost:3000")
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db_session: Session) -> User:
    user = User(
        email="publisher@example.com",
        hashed_password=get_password_hash("StrongPassword123!"),
        full_name="Test Publisher",
        is_active=True,
        is_admin=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def anon_csrf_token() -> str:
    return generate_csrf_token(identity="anonymous")
