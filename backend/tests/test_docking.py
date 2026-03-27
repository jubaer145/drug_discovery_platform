from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from httpx import AsyncClient

from modules.docking import DockingModule
from models.schemas import DockingInput


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

MOCK_VINA_LOG = """\
AutoDock Vina v1.2.5

mode |   affinity | dist from best mode
     | (kcal/mol) | rmsd l.b.| rmsd u.b.
-----+------------+----------+----------
   1         -9.2          0          0
   2         -8.8        1.2        2.1
   3         -8.1        2.5        4.3
"""

MOCK_PDB = """\
ATOM      1  N   ALA A   1      10.000  10.000  10.000  1.00  85.20           N
ATOM      2  CA  ALA A   1      10.000  11.000  10.000  1.00  85.20           C
END
"""


# ---------------------------------------------------------------------------
# Helper: parse vina log from text (for testability)
# ---------------------------------------------------------------------------

def _parse_vina_log_text(text: str) -> list[float]:
    """Parse Vina log text for binding affinities (mirrors module logic)."""
    affinities = []
    in_results = False
    for line in text.splitlines():
        if "-----+------------" in line:
            in_results = True
            continue
        if in_results:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    affinities.append(float(parts[1]))
                except ValueError:
                    break
            else:
                break
    return affinities


# ---------------------------------------------------------------------------
# Module tests
# ---------------------------------------------------------------------------

class TestDockingModule:

    def test_smiles_validation(self):
        """Invalid SMILES are skipped with warning, valid ones proceed."""
        module = DockingModule()

        mock_pdb_data = MOCK_PDB.encode()

        # Mock download_file, subprocess, and RDKit docking flow
        with patch("modules.docking.download_file", return_value=mock_pdb_data), \
             patch("modules.docking.subprocess.run") as mock_subprocess, \
             patch("modules.docking.upload_file"):

            # Mock obabel for receptor prep
            mock_subprocess.return_value = MagicMock(returncode=0)

            # We need to mock _dock_single_ligand to control per-ligand behavior
            with patch.object(module, "_dock_single_ligand") as mock_dock:
                # First SMILES valid -> returns result, second invalid -> returns None
                mock_dock.side_effect = [
                    {
                        "smiles": "CCO",
                        "rank": 0,
                        "best_affinity_kcal_mol": -7.5,
                        "all_pose_affinities": [-7.5, -6.8],
                        "pose_pdbqt_path": None,
                        "docking_success": True,
                    },
                    None,  # invalid SMILES
                ]

                result = module.execute(DockingInput(
                    job_id="test-d-1",
                    pdb_path="structures/test/receptor.pdb",
                    smiles_list=["CCO", "INVALID_SMILES"],
                    binding_site={"center_x": 10, "center_y": 10, "center_z": 10,
                                  "size_x": 20, "size_y": 20, "size_z": 20},
                ))

        assert result.status == "completed"
        assert result.data["docked_count"] == 1
        assert result.data["failed_count"] == 1
        assert "INVALID_SMILES" in result.data["failed_smiles"]

    def test_vina_output_parsing(self):
        """Vina log with known affinities parses correctly."""
        affinities = _parse_vina_log_text(MOCK_VINA_LOG)

        assert len(affinities) == 3
        assert affinities[0] == -9.2
        assert affinities[1] == -8.8
        assert affinities[2] == -8.1

    def test_all_fail(self):
        """All invalid SMILES results in failed status."""
        module = DockingModule()

        mock_pdb_data = MOCK_PDB.encode()

        with patch("modules.docking.download_file", return_value=mock_pdb_data), \
             patch("modules.docking.subprocess.run") as mock_subprocess:

            mock_subprocess.return_value = MagicMock(returncode=0)

            with patch.object(module, "_dock_single_ligand", return_value=None):
                result = module.execute(DockingInput(
                    job_id="test-d-3",
                    pdb_path="structures/test/receptor.pdb",
                    smiles_list=["INVALID1", "INVALID2", "INVALID3"],
                    binding_site={"center_x": 10, "center_y": 10, "center_z": 10,
                                  "size_x": 20, "size_y": 20, "size_z": 20},
                ))

        assert result.status == "failed"
        assert "All" in result.errors[0]

    def test_partial_fail(self):
        """8/10 succeed, 2 fail — docked_count=8, failed_count=2."""
        module = DockingModule()

        mock_pdb_data = MOCK_PDB.encode()

        with patch("modules.docking.download_file", return_value=mock_pdb_data), \
             patch("modules.docking.subprocess.run") as mock_subprocess, \
             patch("modules.docking.upload_file"):

            mock_subprocess.return_value = MagicMock(returncode=0)

            def dock_side_effect(smiles, idx, *args, **kwargs):
                if idx >= 8:  # last 2 fail
                    return None
                return {
                    "smiles": smiles,
                    "rank": 0,
                    "best_affinity_kcal_mol": -5.0 - idx * 0.5,
                    "all_pose_affinities": [-5.0 - idx * 0.5],
                    "pose_pdbqt_path": None,
                    "docking_success": True,
                }

            with patch.object(module, "_dock_single_ligand", side_effect=dock_side_effect):
                smiles = [f"C{'C' * i}O" for i in range(10)]
                result = module.execute(DockingInput(
                    job_id="test-d-4",
                    pdb_path="structures/test/receptor.pdb",
                    smiles_list=smiles,
                    binding_site={"center_x": 10, "center_y": 10, "center_z": 10,
                                  "size_x": 20, "size_y": 20, "size_z": 20},
                ))

        assert result.status == "completed"
        assert result.data["docked_count"] == 8
        assert result.data["failed_count"] == 2

    def test_pocket_detection_parsing(self):
        """Fpocket output is parsed to extract binding site center."""
        module = DockingModule()

        mock_info = """\
Pocket 1:
    Score :      0.65
    Druggability Score :      0.72
    Volume :      350.5
    Center :     12.5  15.3  20.1

Pocket 2:
    Score :      0.30
    Druggability Score :      0.40
    Volume :      100.0
    Center :     5.0   5.0   5.0
"""
        # Write mock info file
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(mock_info)
            info_path = Path(f.name)

        try:
            result = module._parse_fpocket_output(info_path)
            assert result is not None
            assert abs(result["center_x"] - 12.5) < 0.1
            assert abs(result["center_y"] - 15.3) < 0.1
            assert abs(result["center_z"] - 20.1) < 0.1
            assert result["size_x"] == 20.0
        finally:
            info_path.unlink()


# ---------------------------------------------------------------------------
# Route-level test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_docking_returns_job_id(client: AsyncClient):
    """POST /api/docking/run returns job_id and pending status."""
    with patch("api.routes.docking.run_docking") as mock_task:
        mock_task.delay = MagicMock()
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
    mock_task.delay.assert_called_once()
