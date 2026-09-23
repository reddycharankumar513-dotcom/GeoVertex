import asyncio
import os
import sys
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.core.security import get_password_hash
from app.database.base import Base
from app.dependencies.db import get_db
from app.main import app
from app.models.jurisdiction import Jurisdiction
from app.models.organization import Organization
from app.models.user import User, UserRole

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_geovertex.db"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncSession:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncClient:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def seed_test_data(db_session: AsyncSession):
    # Seed Organization
    org = Organization(
        name="Test Municipal Cadastre Department",
        code="TEST-CAD-01",
        type="MUNICIPALITY",
        is_active=True,
    )
    db_session.add(org)
    await db_session.flush()

    # Seed Jurisdiction with bounding box (78.4800 to 78.5000, 17.3800 to 17.4000)
    jur = Jurisdiction(
        organization_id=org.id,
        name="Test Ward 500",
        code="TEST-W500",
        level="WARD",
        srid=4326,
        boundary_wkt="MULTIPOLYGON(((78.4800 17.3800, 78.5000 17.3800, 78.5000 17.4000, 78.4800 17.4000, 78.4800 17.3800)))",
        is_active=True,
    )
    db_session.add(jur)
    await db_session.flush()

    # Seed Users with explicit emails
    role_accounts = [
        ("admin@test.org", "test_admin", "Test Admin", UserRole.ADMIN),
        ("officer@test.org", "test_officer", "Test Officer", UserRole.GOVERNMENT_OFFICER),
        ("surveyor@test.org", "test_surveyor", "Test Surveyor", UserRole.SURVEYOR),
        ("citizen@test.org", "test_citizen", "Test Citizen", UserRole.CITIZEN),
        ("planner@test.org", "test_planner", "Test Planner", UserRole.URBAN_PLANNER),
    ]

    users = {}
    for email, username, full_name, role in role_accounts:
        user = User(
            email=email,
            username=username,
            full_name=full_name,
            password_hash=get_password_hash("TestPassword123!"),
            role=role.value,
            organization_id=org.id,
            jurisdiction_id=jur.id,
            is_active=True,
            is_verified=True,
        )
        db_session.add(user)
        await db_session.flush()
        users[role.value] = user

    # Deactivated User
    inactive_user = User(
        email="inactive@test.org",
        username="inactive_user",
        full_name="Inactive User",
        password_hash=get_password_hash("TestPassword123!"),
        role=UserRole.CITIZEN.value,
        is_active=False,
        is_verified=True,
    )
    db_session.add(inactive_user)
    await db_session.flush()
    users["INACTIVE"] = inactive_user

    await db_session.commit()
    return {"org": org, "jur": jur, "users": users}


@pytest_asyncio.fixture(scope="function")
async def auth_tokens(client: AsyncClient, seed_test_data) -> dict:
    """Provides ready-to-use Bearer authorization headers for each role."""
    roles = {
        "admin": "admin@test.org",
        "officer": "officer@test.org",
        "surveyor": "surveyor@test.org",
        "citizen": "citizen@test.org",
    }
    headers = {}
    for role_name, email in roles.items():
        res = await client.post(
            "/api/v1/auth/login",
            json={"username_or_email": email, "password": "TestPassword123!"},
        )
        token = res.json()["access_token"]
        headers[role_name] = {"Authorization": f"Bearer {token}"}
    return headers

