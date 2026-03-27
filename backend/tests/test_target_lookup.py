from unittest.mock import patch, MagicMock

import pytest
import httpx
from httpx import AsyncClient

from modules.target_lookup import TargetLookupModule
from models.schemas import TargetLookupInput


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

MOCK_PDB_ENTRY = {
    "struct": {"title": "Crystal structure of ABL1 kinase domain"},
    "exptl": [{"method": "X-RAY DIFFRACTION"}],
    "refine": [{"ls_d_res_high": 2.1}],
}

MOCK_PDB_POLYMER = {
    "rcsb_entity_source_organism": [{"ncbi_scientific_name": "Homo sapiens"}],
    "rcsb_polymer_entity_container_identifiers": {"uniprot_ids": ["P00519"]},
}

MOCK_UNIPROT_EGFR = {
    "primaryAccession": "P00533",
    "proteinDescription": {
        "recommendedName": {"fullName": {"value": "Epidermal growth factor receptor"}},
    },
    "genes": [{"geneName": {"value": "EGFR"}}],
    "organism": {"scientificName": "Homo sapiens"},
    "sequence": {"length": 1210, "value": "MRPSGTAGAALLALLAALCPASRALEEKKVC"},
    "comments": [
        {
            "commentType": "FUNCTION",
            "texts": [{"value": "Receptor tyrosine kinase involved in cell signaling."}],
        },
        {
            "commentType": "DISEASE",
            "disease": {"diseaseId": "Lung adenocarcinoma"},
        },
    ],
    "uniProtKBCrossReferences": [
        {
            "database": "PDB",
            "id": "1IVO",
            "properties": [
                {"key": "Method", "value": "X-ray"},
                {"key": "Resolution", "value": "2.6"},
            ],
        },
        {
            "database": "PDB",
            "id": "3NJP",
            "properties": [
                {"key": "Method", "value": "X-ray"},
                {"key": "Resolution", "value": "1.5"},
            ],
        },
    ],
}

MOCK_UNIPROT_SEARCH = {
    "results": [
        MOCK_UNIPROT_EGFR,
        {
            "primaryAccession": "Q504U8",
            "proteinDescription": {
                "recommendedName": {"fullName": {"value": "EGFR-related protein"}},
            },
            "genes": [{"geneName": {"value": "ERBB2"}}],
            "organism": {"scientificName": "Homo sapiens"},
            "sequence": {"length": 800, "value": "MELAALCRWGLLL"},
            "comments": [],
            "uniProtKBCrossReferences": [],
        },
    ]
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(json_data, status_code=200):
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"{status_code}", request=MagicMock(), response=resp,
        )
    return resp


def _make_client_mock(responses: dict):
    """Create an httpx.Client mock that returns different responses based on URL."""
    client_mock = MagicMock()

    def side_effect(url, **kwargs):
        for pattern, resp in responses.items():
            if pattern in url:
                return resp
        return _make_response({}, 404)

    client_mock.get = MagicMock(side_effect=side_effect)
    client_mock.__enter__ = MagicMock(return_value=client_mock)
    client_mock.__exit__ = MagicMock(return_value=False)
    return client_mock


# ---------------------------------------------------------------------------
# Module-level tests (mock httpx.Client)
# ---------------------------------------------------------------------------

class TestTargetLookupModule:

    def test_pdb_id_lookup(self):
        """Query '1IEP' auto-detects as PDB ID and returns protein data."""
        module = TargetLookupModule()
        mock_client = _make_client_mock({
            "/core/entry/1IEP": _make_response(MOCK_PDB_ENTRY),
            "/core/polymer_entity/1IEP/1": _make_response(MOCK_PDB_POLYMER),
            "uniprotkb/P00519.json": _make_response(MOCK_UNIPROT_EGFR),
            "alphafold.ebi.ac.uk": _make_response([], 200),
        })

        with patch("modules.target_lookup.httpx.Client", return_value=mock_client):
            result = module.execute(TargetLookupInput(job_id="test-1", query="1IEP"))

        assert result.status == "completed"
        assert "ABL1" in result.data.get("protein_name", "")
        assert result.data["best_pdb_id"] == "1IEP"
        assert len(result.data.get("pdb_structures", [])) >= 1

    def test_uniprot_lookup(self):
        """Query 'P00533' auto-detects as UniProt and returns EGFR data."""
        module = TargetLookupModule()
        mock_client = _make_client_mock({
            "uniprotkb/P00533.json": _make_response(MOCK_UNIPROT_EGFR),
            "alphafold.ebi.ac.uk": _make_response([], 200),
        })

        with patch("modules.target_lookup.httpx.Client", return_value=mock_client):
            result = module.execute(TargetLookupInput(job_id="test-2", query="P00533"))

        assert result.status == "completed"
        assert result.data["gene_symbol"] == "EGFR"
        assert result.data["sequence_length"] == 1210
        assert result.data["uniprot_id"] == "P00533"
        assert len(result.data["pdb_structures"]) == 2

    def test_name_lookup(self):
        """Query 'EGFR' auto-detects as name and resolves via UniProt search."""
        module = TargetLookupModule()
        mock_client = _make_client_mock({
            "uniprotkb/search": _make_response(MOCK_UNIPROT_SEARCH),
            "alphafold.ebi.ac.uk": _make_response([], 200),
        })

        with patch("modules.target_lookup.httpx.Client", return_value=mock_client):
            result = module.execute(TargetLookupInput(job_id="test-3", query="EGFR"))

        assert result.status == "completed"
        assert result.data.get("uniprot_id") == "P00533"
        assert result.data.get("protein_name") == "Epidermal growth factor receptor"
        # Should include multiple candidates since search returned 2
        assert result.data.get("multiple_candidates") is not None
        assert len(result.data["multiple_candidates"]) == 2

    def test_invalid_pdb(self):
        """Query 'ZZZZ' (not matching PDB pattern) searches by name; empty results return gracefully."""
        module = TargetLookupModule()
        mock_client = _make_client_mock({
            "uniprotkb/search": _make_response({"results": []}),
        })

        with patch("modules.target_lookup.httpx.Client", return_value=mock_client):
            result = module.execute(TargetLookupInput(job_id="test-4", query="ZZZZ"))

        # "ZZZZ" doesn't match PDB pattern (needs digit first), so goes to name search
        assert result.status == "completed"
        assert result.data == {}
        assert len(result.warnings) > 0
        assert "No results" in result.warnings[0]

    def test_alphafold_check(self):
        """AlphaFold availability is detected for P00533."""
        module = TargetLookupModule()
        mock_client = _make_client_mock({
            "uniprotkb/P00533.json": _make_response(MOCK_UNIPROT_EGFR),
            "alphafold.ebi.ac.uk": _make_response([], 200),
        })

        with patch("modules.target_lookup.httpx.Client", return_value=mock_client):
            result = module.execute(TargetLookupInput(job_id="test-5", query="P00533"))

        assert result.status == "completed"
        assert result.data["has_alphafold"] is True
        assert "AF-P00533" in result.data["alphafold_url"]


# ---------------------------------------------------------------------------
# Route-level test
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_target_lookup_returns_job_id(client: AsyncClient):
    """POST /api/targets/lookup returns job_id and pending status."""
    with patch("api.routes.targets.run_target_lookup") as mock_task:
        mock_task.delay = MagicMock()
        response = await client.post(
            "/api/targets/lookup",
            json={"query": "EGFR"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"
    mock_task.delay.assert_called_once()
