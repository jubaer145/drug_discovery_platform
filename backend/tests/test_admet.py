import pytest
from httpx import AsyncClient

from modules.admet import AdmetModule
from models.schemas import AdmetInput


# Well-known SMILES
ASPIRIN = "CC(=O)Oc1ccccc1C(=O)O"
CAFFEINE = "Cn1c(=O)c2c(ncn2C)n(C)c1=O"
# Large molecule that violates Lipinski (MW > 500)
LARGE_MOL = "CC(C)CC1=CC=C(C=C1)C(C)C(=O)OC2CC(CC3=CC=C(C=C3)C(C)C(=O)OC4CC(CC5=CC=C(C=C5)C(C)CC)C(C)C4)C(C)C2"
# Known PAINS compound (rhodanine)
RHODANINE = "O=C1CSC(=S)N1"


class TestAdmetModule:

    def test_aspirin(self):
        """Aspirin should pass Lipinski and get GREEN overall."""
        module = AdmetModule()
        result = module.execute(AdmetInput(
            job_id="test-a-1",
            smiles_list=[ASPIRIN],
            run_tier2=False,
        ))

        assert result.status == "completed"
        profiles = result.data["profiles"]
        assert len(profiles) == 1

        p = profiles[0]
        assert p["tier1"]["lipinski_pass"] is True
        assert p["overall"] == "GREEN"
        assert p["recommendation"] == "recommended"
        assert p["tier1"]["mw"] < 500
        assert p["tier1"]["logp"] < 5

    def test_pains_detection(self):
        """Rhodanine (known PAINS motif) should be flagged."""
        module = AdmetModule()
        result = module.execute(AdmetInput(
            job_id="test-a-2",
            smiles_list=[RHODANINE],
            run_tier2=False,
        ))

        assert result.status == "completed"
        p = result.data["profiles"][0]
        assert p["tier1"]["has_pains"] is True
        assert p["overall"] in ("AMBER", "RED")
        assert any("PAINS" in f["message"] for f in p["flags"])

    def test_lipinski_fail(self):
        """A large molecule violating Lipinski should get RED."""
        module = AdmetModule()
        result = module.execute(AdmetInput(
            job_id="test-a-3",
            smiles_list=[LARGE_MOL],
            run_tier2=False,
        ))

        assert result.status == "completed"
        p = result.data["profiles"][0]
        assert p["tier1"]["lipinski_pass"] is False
        assert p["overall"] == "RED"
        assert p["recommendation"] == "not_recommended"
        assert len(p["tier1"]["lipinski_violations"]) > 0

    def test_batch(self):
        """Batch of 5 molecules all return tier1 data."""
        module = AdmetModule()
        smiles = [ASPIRIN, CAFFEINE, RHODANINE, "CCO", "c1ccccc1"]
        result = module.execute(AdmetInput(
            job_id="test-a-4",
            smiles_list=smiles,
            run_tier2=False,
        ))

        assert result.status == "completed"
        assert result.data["total"] == 5
        for p in result.data["profiles"]:
            assert "tier1" in p
            assert p["tier1"]["mw"] > 0
            assert p["overall"] in ("GREEN", "AMBER", "RED")

    def test_traffic_light_logic(self):
        """Verify GREEN/AMBER/RED classification logic."""
        module = AdmetModule()
        smiles = [ASPIRIN, RHODANINE, LARGE_MOL]
        result = module.execute(AdmetInput(
            job_id="test-a-5",
            smiles_list=smiles,
            run_tier2=False,
        ))

        assert result.status == "completed"
        profiles = {p["smiles"]: p for p in result.data["profiles"]}

        assert profiles[ASPIRIN]["overall"] == "GREEN"
        assert profiles[RHODANINE]["overall"] in ("AMBER", "RED")
        assert profiles[LARGE_MOL]["overall"] == "RED"

        assert result.data["green_count"] >= 1
        assert result.data["red_count"] >= 1


# ---------------------------------------------------------------------------
# Route-level test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admet_predict_returns_profiles(client: AsyncClient):
    """POST /api/admet/predict returns completed profiles synchronously."""
    response = await client.post(
        "/api/admet/predict",
        json={"smiles_list": [ASPIRIN, CAFFEINE]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["total"] == 2
    assert len(data["profiles"]) == 2
    for p in data["profiles"]:
        assert "tier1" in p
        assert "overall" in p
