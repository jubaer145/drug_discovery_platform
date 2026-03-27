from unittest.mock import patch, MagicMock

import pytest
from httpx import AsyncClient

from modules.structure_pred import StructurePredModule, _parse_plddt
from models.schemas import StructurePredInput


# ---------------------------------------------------------------------------
# Mock PDB with known B-factors (pLDDT scores)
# ---------------------------------------------------------------------------

MOCK_PDB = """\
ATOM      1  N   ALA A   1      10.000  10.000  10.000  1.00  85.20           N
ATOM      2  CA  ALA A   1      10.000  11.000  10.000  1.00  85.20           C
ATOM      3  C   ALA A   1      10.000  12.000  10.000  1.00  85.20           C
ATOM      4  N   GLY A   2      11.000  12.000  10.000  1.00  72.50           N
ATOM      5  CA  GLY A   2      12.000  12.000  10.000  1.00  72.50           C
ATOM      6  C   GLY A   2      13.000  12.000  10.000  1.00  72.50           C
ATOM      7  N   VAL A   3      14.000  12.000  10.000  1.00  91.30           N
ATOM      8  CA  VAL A   3      15.000  12.000  10.000  1.00  91.30           C
ATOM      9  C   VAL A   3      16.000  12.000  10.000  1.00  91.30           C
ATOM     10  N   LEU A   4      17.000  12.000  10.000  1.00  45.10           N
ATOM     11  CA  LEU A   4      18.000  12.000  10.000  1.00  45.10           C
ATOM     12  C   LEU A   4      19.000  12.000  10.000  1.00  45.10           C
END
"""

# pLDDT from CA atoms: 85.20, 72.50, 91.30, 45.10
# mean = (85.20 + 72.50 + 91.30 + 45.10) / 4 = 73.525
# min = 45.10
# pct_high (>70) = 3/4 = 0.75


def _make_httpx_response(text: str, status_code: int = 200):
    resp = MagicMock()
    resp.text = text
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        import httpx
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"{status_code}", request=MagicMock(), response=resp,
        )
    return resp


# ---------------------------------------------------------------------------
# Module-level tests
# ---------------------------------------------------------------------------

class TestStructurePredModule:

    def test_valid_sequence(self):
        """A valid short sequence returns completed status with pdb_url."""
        module = StructurePredModule()
        sequence = "MKTAYIAKQRQISFVKSHFSRQ"  # 22 AA

        mock_client = MagicMock()
        mock_client.post.return_value = _make_httpx_response(MOCK_PDB)
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("modules.structure_pred.httpx.Client", return_value=mock_client), \
             patch("modules.structure_pred.upload_file") as mock_upload:
            result = module.execute(StructurePredInput(
                job_id="test-sp-1", sequence=sequence,
            ))

        assert result.status == "completed"
        assert "pdb_url" in result.data
        assert "plddt_url" in result.data
        assert result.data["prediction_source"] == "ESMFold"
        assert result.data["sequence_length"] == 22
        assert mock_upload.call_count == 2  # PDB + pLDDT JSON

    def test_sequence_too_long(self):
        """A sequence over 400 AA fails validation."""
        module = StructurePredModule()
        sequence = "A" * 401

        result = module.execute(StructurePredInput(
            job_id="test-sp-2", sequence=sequence,
        ))

        assert result.status == "failed"
        assert any("at most 400" in e for e in result.errors)

    def test_invalid_characters(self):
        """A sequence with invalid amino acid characters fails validation."""
        module = StructurePredModule()
        sequence = "MKTAYIAKBZQRQISFVKSHFSRQ"  # B and Z are invalid

        result = module.execute(StructurePredInput(
            job_id="test-sp-3", sequence=sequence,
        ))

        assert result.status == "failed"
        assert any("B" in e for e in result.errors)
        assert any("Z" in e for e in result.errors)

    def test_plddt_parsing(self):
        """pLDDT scores are correctly extracted from PDB B-factor column."""
        scores = _parse_plddt(MOCK_PDB)

        assert len(scores) == 4
        assert scores[0] == 85.20
        assert scores[1] == 72.50
        assert scores[2] == 91.30
        assert scores[3] == 45.10

        mean = sum(scores) / len(scores)
        assert abs(mean - 73.525) < 0.01

    def test_quality_assessment(self):
        """Quality is 'high' when mean pLDDT > 80."""
        module = StructurePredModule()

        # Create PDB with all high B-factors (pLDDT = 85)
        high_pdb_lines = []
        for i in range(1, 21):
            high_pdb_lines.append(
                f"ATOM  {i*2-1:5d}  N   ALA A {i:3d}      "
                f"10.000  10.000  10.000  1.00  85.00           N"
            )
            high_pdb_lines.append(
                f"ATOM  {i*2:5d}  CA  ALA A {i:3d}      "
                f"10.000  11.000  10.000  1.00  85.00           C"
            )
        high_pdb_lines.append("END")
        high_pdb = "\n".join(high_pdb_lines)

        mock_client = MagicMock()
        mock_client.post.return_value = _make_httpx_response(high_pdb)
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch("modules.structure_pred.httpx.Client", return_value=mock_client), \
             patch("modules.structure_pred.upload_file"):
            result = module.execute(StructurePredInput(
                job_id="test-sp-5", sequence="A" * 20,
            ))

        assert result.status == "completed"
        assert result.data["quality_assessment"] == "high"
        assert result.data["mean_plddt"] == 85.0


# ---------------------------------------------------------------------------
# Route-level test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_structure_predict_returns_job_id(client: AsyncClient):
    """POST /api/structures/predict returns job_id and pending status."""
    with patch("api.routes.structures.run_structure_prediction") as mock_task:
        mock_task.delay = MagicMock()
        response = await client.post(
            "/api/structures/predict",
            json={"sequence": "MKTAYIAKQRQISFVKSHFSRQ", "method": "esmfold"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"
    mock_task.delay.assert_called_once()
