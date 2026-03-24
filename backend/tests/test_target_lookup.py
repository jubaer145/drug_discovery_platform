import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_target_lookup_returns_job_id(client: AsyncClient):
    response = await client.post(
        "/api/targets/lookup",
        json={"query": "EGFR"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"
