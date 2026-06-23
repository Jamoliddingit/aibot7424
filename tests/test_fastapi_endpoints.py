"""Tests for FastAPI health-check endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.fixture
def transport():
    return ASGITransport(app=app)


@pytest.mark.asyncio
async def test_get_root(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "AIBOT OK"
    assert data["ping"] is True


@pytest.mark.asyncio
async def test_head_root(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.head("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_ping(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ping")
    assert response.status_code == 200
    data = response.json()
    assert data["pong"] is True


@pytest.mark.asyncio
async def test_root_returns_json_content_type(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")
    assert "application/json" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_nonexistent_endpoint_returns_404(transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/nonexistent")
    assert response.status_code == 404
