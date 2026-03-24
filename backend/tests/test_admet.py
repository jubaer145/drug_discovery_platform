import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admet_returns_job_id(client: AsyncClient):
    response = await client.post(
        "/api/admet/predict",
        json={"smiles_list": ["CC(=O)Oc1ccccc1C(=O)O", "c1ccccc1"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"
