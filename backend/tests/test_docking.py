import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_docking_returns_job_id(client: AsyncClient):
    response = await client.post(
        "/api/docking/run",
        json={
            "target_pdb_path": "structures/test.pdb",
            "molecules": ["CC(=O)Oc1ccccc1C(=O)O"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"
