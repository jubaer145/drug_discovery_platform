import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_ai_query_returns_job_id(client: AsyncClient):
    response = await client.post(
        "/api/ai/suggest-targets",
        json={"disease_description": "Type 2 diabetes targeting insulin resistance"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"
