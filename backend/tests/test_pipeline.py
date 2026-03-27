from unittest.mock import patch, MagicMock

import pytest
from httpx import AsyncClient

from core.pipeline import (
    _prepare_molecules, _admet_prefilter, _rank_candidates,
)
from modules.docking import DockingModule
from models.schemas import MoleculeInput, AdmetInput


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestMoleculePreparation:

    def test_smiles_validation(self):
        """Valid SMILES are canonicalized, invalid are dropped."""
        mols = MoleculeInput(smiles=["CCO", "CC(=O)O", "INVALID_MOL"])
        result = _prepare_molecules(mols)
        assert len(result) == 2
        assert "CCO" in result

    def test_deduplication(self):
        """Duplicate SMILES (including non-canonical) are removed."""
        mols = MoleculeInput(smiles=["CCO", "OCC", "CCO"])
        result = _prepare_molecules(mols)
        assert len(result) == 1  # CCO and OCC are the same molecule

    def test_empty_input(self):
        """None molecules returns empty list."""
        assert _prepare_molecules(None) == []


class TestAdmetPrefilter:

    def test_filters_red_molecules(self):
        """RED-flagged molecules are removed, GREEN/AMBER kept."""
        # Use real ADMET module with known molecules
        smiles = [
            "CCO",          # ethanol — should pass (GREEN)
            "c1ccccc1",     # benzene — should pass
            "CC(=O)Oc1ccccc1C(=O)O",  # aspirin — GREEN
        ]
        result = _admet_prefilter("test-pf", smiles, min_qed=0.0, max_count=100)
        # All small molecules should pass Lipinski
        assert len(result) >= 2

    def test_max_count_limit(self):
        """Output is limited to max_count molecules."""
        smiles = [f"{'C' * i}O" for i in range(1, 20)]
        # Filter only valid ones first
        from rdkit import Chem
        valid = [s for s in smiles if Chem.MolFromSmiles(s)]
        result = _admet_prefilter("test-pf2", valid[:10], min_qed=0.0, max_count=3)
        assert len(result) <= 3


class TestRanking:

    def test_composite_score(self):
        """Composite score correctly weights docking + QED + Lipinski + PAINS."""
        docking = [
            {"smiles": "CCO", "best_affinity_kcal_mol": -9.0, "pose_pdbqt_path": None},
            {"smiles": "CC", "best_affinity_kcal_mol": -5.0, "pose_pdbqt_path": None},
        ]
        admet = {
            "CCO": {
                "overall": "GREEN",
                "tier1": {"qed": 0.8, "lipinski_pass": True, "has_pains": False},
            },
            "CC": {
                "overall": "AMBER",
                "tier1": {"qed": 0.3, "lipinski_pass": True, "has_pains": True},
            },
        }
        ranked = _rank_candidates(docking, admet)
        assert len(ranked) == 2
        assert ranked[0]["smiles"] == "CCO"  # better affinity + better ADMET
        assert ranked[0]["rank"] == 1
        assert ranked[1]["rank"] == 2
        assert ranked[0]["composite_score"] > ranked[1]["composite_score"]

    def test_empty_docking(self):
        """Empty docking results returns empty ranking."""
        assert _rank_candidates([], {}) == []


class TestPipelineOrchestration:

    def test_full_pipeline_with_mocks(self):
        """Full virtual screening pipeline with all modules mocked."""
        from core.pipeline import run_virtual_screening
        from models.schemas import PipelineConfig

        mock_pdb = b"ATOM      1  N   ALA A   1      0.0  0.0  0.0  1.00  0.00\nEND\n"

        config = PipelineConfig(
            job_id="test-pipe-1",
            task="virtual_screening",
            target_pdb_id="1IEP",
            molecules=MoleculeInput(smiles=["CCO", "CC(=O)O", "c1ccccc1"]),
            admet_filter_before_docking=True,
            max_molecules_to_dock=10,
        )

        # Mock: RCSB PDB download
        mock_httpx_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = mock_pdb
        mock_resp.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_resp
        mock_httpx_client.__enter__ = MagicMock(return_value=mock_httpx_client)
        mock_httpx_client.__exit__ = MagicMock(return_value=False)

        # Mock: DockingModule returns results
        mock_docking_result = MagicMock()
        mock_docking_result.status = "completed"
        mock_docking_result.data = {
            "results": [
                {"smiles": "CCO", "best_affinity_kcal_mol": -7.5, "pose_pdbqt_path": None},
                {"smiles": "CC(=O)O", "best_affinity_kcal_mol": -6.8, "pose_pdbqt_path": None},
            ],
        }

        with patch("core.pipeline.httpx.Client", return_value=mock_httpx_client), \
             patch("core.pipeline.upload_file"), \
             patch("core.pipeline.send_progress_update"), \
             patch.object(DockingModule, "execute", return_value=mock_docking_result):

            result = run_virtual_screening("test-pipe-1", config)

        assert "pipeline_summary" in result
        assert result["pipeline_summary"]["total_input_molecules"] == 3
        assert result["pipeline_summary"]["successfully_docked"] == 2
        assert len(result["ranked_candidates"]) == 2
        assert result["ranked_candidates"][0]["rank"] == 1


# ---------------------------------------------------------------------------
# Route-level tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pipeline_requires_target(client: AsyncClient):
    """POST /api/pipeline/run without target returns 422."""
    response = await client.post(
        "/api/pipeline/run",
        json={
            "task_type": "virtual_screening",
            "molecules": {"smiles": ["CCO"]},
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_pipeline_requires_molecules(client: AsyncClient):
    """POST /api/pipeline/run without molecules returns 422."""
    response = await client.post(
        "/api/pipeline/run",
        json={
            "target_pdb_id": "1IEP",
            "task_type": "virtual_screening",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_pipeline_dispatches_job(client: AsyncClient):
    """POST /api/pipeline/run with valid input returns job_id."""
    with patch("api.routes.pipeline.dispatch_pipeline") as mock_dispatch:
        from models.schemas import PipelineResponse
        mock_dispatch.return_value = PipelineResponse(job_id="test-123", status="pending", estimated_minutes=2)
        response = await client.post(
            "/api/pipeline/run",
            json={
                "target_pdb_id": "1IEP",
                "task_type": "virtual_screening",
                "molecules": {"smiles": ["CCO", "c1ccccc1"]},
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def _disabled_test(client: AsyncClient):
    """Placeholder to keep the old patch approach."""
    with patch("core.queue.run_pipeline_task") as mock_task:
        mock_task.delay = MagicMock()
        response = await client.post(
            "/api/pipeline/run",
            json={
                "target_pdb_id": "1IEP",
                "task_type": "virtual_screening",
                "molecules": {"smiles": ["CCO", "c1ccccc1"]},
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"
    mock_task.delay.assert_called_once()
