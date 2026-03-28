import pytest
from httpx import AsyncClient


ASPIRIN = "CC(=O)Oc1ccccc1C(=O)O"
ETHANOL = "CCO"


@pytest.mark.asyncio
async def test_render_valid_smiles(client: AsyncClient):
    """GET /api/molecules/render returns PNG for valid SMILES."""
    response = await client.get(f"/api/molecules/render?smiles={ASPIRIN}&size=150")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert len(response.content) > 100  # valid PNG has content
    assert "cache-control" in response.headers


@pytest.mark.asyncio
async def test_render_invalid_smiles(client: AsyncClient):
    """GET /api/molecules/render returns placeholder for invalid SMILES."""
    response = await client.get("/api/molecules/render?smiles=INVALID_SMILES")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"


@pytest.mark.asyncio
async def test_validate_smiles(client: AsyncClient):
    """POST /api/molecules/validate returns per-SMILES validation results."""
    response = await client.post(
        "/api/molecules/validate",
        json={"smiles_list": [ASPIRIN, "INVALID", ETHANOL, ""]},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3  # empty string is skipped
    assert data[0]["valid"] is True
    assert data[0]["smiles"] == ASPIRIN
    assert data[1]["valid"] is False
    assert data[2]["valid"] is True


@pytest.mark.asyncio
async def test_export_sdf_with_smiles(client: AsyncClient):
    """POST /api/molecules/export-sdf returns SDF file."""
    response = await client.post(
        "/api/molecules/export-sdf",
        json={"job_id": "test-123", "smiles_list": [ASPIRIN, ETHANOL]},
    )
    assert response.status_code == 200
    assert "chemical/x-mdl-sdfile" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]
    content = response.text
    assert "$$$$" in content  # SDF record separator


@pytest.mark.asyncio
async def test_export_sdf_empty(client: AsyncClient):
    """POST /api/molecules/export-sdf with no molecules returns 422."""
    response = await client.post(
        "/api/molecules/export-sdf",
        json={"job_id": "test-123", "smiles_list": []},
    )
    assert response.status_code == 422
