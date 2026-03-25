import json
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

MOCK_TARGETS_RESPONSE = {
    "targets": [
        {
            "protein_name": "BACE1",
            "gene_symbol": "BACE1",
            "uniprot_id": "P56817",
            "full_name": "Beta-secretase 1",
            "confidence": "high",
            "mechanism_summary": (
                "BACE1 cleaves amyloid precursor protein to produce amyloid-beta peptides. "
                "Accumulation of these peptides forms plaques that drive neurodegeneration."
            ),
            "druggability_note": "Well-defined active site with multiple co-crystal structures available.",
            "tags": ["amyloid pathway", "crystal structure available"],
            "has_pdb_structure": True,
            "clinical_stage": "phase3_trials",
            "difficulty": "moderate",
        },
        {
            "protein_name": "GSK3B",
            "gene_symbol": "GSK3B",
            "uniprot_id": "P49841",
            "full_name": "Glycogen synthase kinase-3 beta",
            "confidence": "medium",
            "mechanism_summary": (
                "GSK3B phosphorylates tau protein, promoting neurofibrillary tangle formation. "
                "Inhibiting GSK3B reduces tau hyperphosphorylation in preclinical models."
            ),
            "druggability_note": "ATP-competitive pocket is well characterised but selectivity is challenging.",
            "tags": ["tau pathway", "kinase"],
            "has_pdb_structure": True,
            "clinical_stage": "preclinical",
            "difficulty": "moderate",
        },
        {
            "protein_name": "TREM2",
            "gene_symbol": "TREM2",
            "uniprot_id": "Q9NZC2",
            "full_name": "Triggering receptor expressed on myeloid cells 2",
            "confidence": "medium",
            "mechanism_summary": (
                "TREM2 modulates microglial activation and phagocytosis of amyloid plaques. "
                "Loss-of-function variants increase Alzheimer's risk significantly."
            ),
            "druggability_note": "Agonist antibodies are in trials; small-molecule approaches remain exploratory.",
            "tags": ["neuroinflammation", "immune modulation"],
            "has_pdb_structure": True,
            "clinical_stage": "preclinical",
            "difficulty": "difficult",
        },
    ],
    "query_interpretation": "Identifying protein targets implicated in Alzheimer's disease pathology.",
    "confidence_explanation": "High confidence for BACE1 due to extensive clinical data; others have strong preclinical support.",
}

MOCK_CANCER_RESPONSE = {
    "targets": [
        {
            "protein_name": "EGFR",
            "gene_symbol": "EGFR",
            "uniprot_id": "P00533",
            "full_name": "Epidermal growth factor receptor",
            "confidence": "high",
            "mechanism_summary": (
                "EGFR is frequently overexpressed in triple-negative breast cancer. "
                "Its activation drives proliferation and survival signalling."
            ),
            "druggability_note": "Multiple approved inhibitors exist with well-characterised binding pockets.",
            "tags": ["kinase", "approved drugs"],
            "has_pdb_structure": True,
            "clinical_stage": "approved",
            "difficulty": "easy",
        },
        {
            "protein_name": "PARP1",
            "gene_symbol": "PARP1",
            "uniprot_id": "P09874",
            "full_name": "Poly [ADP-ribose] polymerase 1",
            "confidence": "high",
            "mechanism_summary": (
                "PARP1 is involved in DNA damage repair. "
                "TNBC with BRCA mutations is especially sensitive to PARP inhibition."
            ),
            "druggability_note": "Well-validated NAD+ binding pocket with approved drugs (olaparib).",
            "tags": ["DNA repair", "synthetic lethality"],
            "has_pdb_structure": True,
            "clinical_stage": "approved",
            "difficulty": "easy",
        },
    ],
    "query_interpretation": "Identifying targets relevant to drug resistance in triple-negative breast cancer.",
    "confidence_explanation": "Strong clinical evidence for both targets in TNBC treatment.",
}


def _make_mock_response(data: dict) -> MagicMock:
    """Build a mock Anthropic Messages response."""
    content_block = MagicMock()
    content_block.text = json.dumps(data)
    response = MagicMock()
    response.content = [content_block]
    return response


def _patch_module_client(mock_data: dict):
    """Return a patch context that replaces the Anthropic client on the route-level module."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value = _make_mock_response(mock_data)
    return patch("api.routes.ai_query._module._client", mock_client)


@pytest.mark.asyncio
async def test_alzheimers_query(client: AsyncClient):
    with _patch_module_client(MOCK_TARGETS_RESPONSE):
        response = await client.post(
            "/api/ai/suggest-targets",
            json={"query": "what proteins drive Alzheimer's disease?"},
        )
    assert response.status_code == 200
    data = response.json()

    targets = data["targets"]
    assert 3 <= len(targets) <= 5
    for t in targets:
        assert "confidence" in t
    assert any(t["confidence"] == "high" for t in targets)


@pytest.mark.asyncio
async def test_cancer_query(client: AsyncClient):
    with _patch_module_client(MOCK_CANCER_RESPONSE):
        response = await client.post(
            "/api/ai/suggest-targets",
            json={"query": "what causes triple-negative breast cancer resistance?"},
        )
    assert response.status_code == 200
    data = response.json()

    targets = data["targets"]
    assert len(targets) > 0
    for t in targets:
        assert t["uniprot_id"] is not None


@pytest.mark.asyncio
async def test_short_query_fails(client: AsyncClient):
    response = await client.post(
        "/api/ai/suggest-targets",
        json={"query": "hi"},
    )
    assert response.status_code == 422
    data = response.json()
    detail = data["detail"]
    assert isinstance(detail, (list, str))


@pytest.mark.asyncio
async def test_response_structure(client: AsyncClient):
    with _patch_module_client(MOCK_TARGETS_RESPONSE):
        response = await client.post(
            "/api/ai/suggest-targets",
            json={"query": "what proteins are involved in Parkinson's disease?"},
        )
    assert response.status_code == 200
    data = response.json()

    assert "targets" in data
    assert "query_interpretation" in data
    assert "confidence_explanation" in data

    required_fields = {
        "protein_name", "gene_symbol", "uniprot_id", "full_name",
        "confidence", "mechanism_summary", "druggability_note",
        "tags", "has_pdb_structure", "clinical_stage", "difficulty",
    }
    for target in data["targets"]:
        assert required_fields.issubset(target.keys())
        assert target["confidence"] in ("high", "medium", "low")
        assert target["clinical_stage"] in ("approved", "phase3_trials", "preclinical", "unknown")
        assert target["difficulty"] in ("easy", "moderate", "difficult")
        assert isinstance(target["tags"], list)
        assert isinstance(target["has_pdb_structure"], bool)
