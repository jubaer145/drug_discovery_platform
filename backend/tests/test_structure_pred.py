import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_structure_predict_returns_job_id(client: AsyncClient):
    response = await client.post(
        "/api/structures/predict",
        json={"sequence": "MKTAYIAKQRQISFVKSHFSRQ", "method": "esmfold"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"
