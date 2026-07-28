import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_response_shape(client: AsyncClient):
    response = await client.get("/api/v1/health")
    body = response.json()
    assert body["status"] == "ok"
    assert "app_name" in body
    assert "version" in body


@pytest.mark.asyncio
async def test_health_db_returns_200(client: AsyncClient):
    response = await client.get("/api/v1/health/db")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_db_response_shape(client: AsyncClient):
    response = await client.get("/api/v1/health/db")
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "reachable"
