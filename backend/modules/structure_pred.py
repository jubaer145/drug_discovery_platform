import json
import re
import logging

import httpx

from core.config import settings
from core.storage import upload_file
from models.schemas import StructurePredInput
from .base import BaseModule, ModuleInput, ModuleOutput

logger = logging.getLogger(__name__)

VALID_AA = set("ACDEFGHIKLMNPQRSTVWYX")
MAX_SEQUENCE_LENGTH = 400
MIN_SEQUENCE_LENGTH = 10


class StructurePredModule(BaseModule):
    """Predicts 3D protein structure via the ESMFold API."""

    def validate_input(self, input: ModuleInput) -> tuple[bool, str]:
        if not isinstance(input, StructurePredInput):
            return False, "Input must be StructurePredInput"

        sequence = _clean_sequence(input.sequence)

        if len(sequence) < MIN_SEQUENCE_LENGTH:
            return False, f"Sequence must be at least {MIN_SEQUENCE_LENGTH} residues (got {len(sequence)})"
        if len(sequence) > MAX_SEQUENCE_LENGTH:
            return False, f"Sequence must be at most {MAX_SEQUENCE_LENGTH} residues (got {len(sequence)})"

        invalid_chars = set(sequence.upper()) - VALID_AA
        if invalid_chars:
            return False, f"Invalid amino acid characters: {', '.join(sorted(invalid_chars))}"

        return True, ""

    def run(self, input: ModuleInput) -> ModuleOutput:
        assert isinstance(input, StructurePredInput)
        sequence = _clean_sequence(input.sequence)

        # Call ESMFold API
        try:
            with httpx.Client(timeout=300.0) as client:
                resp = client.post(
                    settings.esmfold_api_url,
                    content=sequence,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                resp.raise_for_status()
                pdb_string = resp.text
        except httpx.TimeoutException:
            return ModuleOutput(
                job_id=input.job_id, status="failed", data={},
                errors=["ESMFold API timed out (limit: 5 minutes)"],
            )
        except httpx.HTTPStatusError as e:
            return ModuleOutput(
                job_id=input.job_id, status="failed", data={},
                errors=[f"ESMFold API error: {e.response.status_code}"],
            )

        # Parse pLDDT scores from B-factor column
        plddt_scores = _parse_plddt(pdb_string)

        if not plddt_scores:
            return ModuleOutput(
                job_id=input.job_id, status="failed", data={},
                errors=["Could not parse pLDDT scores from PDB output"],
            )

        mean_plddt = sum(plddt_scores) / len(plddt_scores)
        min_plddt = min(plddt_scores)
        pct_high = sum(1 for s in plddt_scores if s > 70) / len(plddt_scores)

        if mean_plddt >= 80:
            quality = "high"
        elif mean_plddt >= 60:
            quality = "medium"
        else:
            quality = "low"

        # Save to MinIO
        warnings: list[str] = []
        pdb_key = f"{input.job_id}/predicted.pdb"
        plddt_key = f"{input.job_id}/plddt.json"

        plddt_data = {
            "per_residue": plddt_scores,
            "mean": round(mean_plddt, 2),
            "min": round(min_plddt, 2),
            "pct_high_confidence": round(pct_high, 4),
        }

        try:
            upload_file("structures", pdb_key, pdb_string.encode(), "chemical/x-pdb")
            upload_file("structures", plddt_key, json.dumps(plddt_data).encode(), "application/json")
        except Exception as e:
            warnings.append(f"Could not save to MinIO: {e}")

        return ModuleOutput(
            job_id=input.job_id,
            status="completed",
            data={
                "pdb_url": f"structures/{pdb_key}",
                "plddt_url": f"structures/{plddt_key}",
                "mean_plddt": round(mean_plddt, 2),
                "min_plddt": round(min_plddt, 2),
                "pct_high_confidence": round(pct_high, 4),
                "sequence_length": len(sequence),
                "prediction_source": "ESMFold",
                "quality_assessment": quality,
            },
            warnings=warnings,
        )


def _clean_sequence(seq: str) -> str:
    """Strip whitespace, newlines, and FASTA headers from a sequence."""
    lines = seq.strip().splitlines()
    cleaned = []
    for line in lines:
        line = line.strip()
        if line.startswith(">"):
            continue  # skip FASTA header
        cleaned.append(re.sub(r"\s+", "", line))
    return "".join(cleaned).upper()


def _parse_plddt(pdb_string: str) -> list[float]:
    """Extract per-residue pLDDT scores from the B-factor column of ATOM records.

    pLDDT is stored in the B-factor column (columns 61-66) of CA atoms.
    We take one value per residue (CA atom only) to avoid duplicates.
    """
    scores: list[float] = []
    seen_residues: set[str] = set()

    for line in pdb_string.splitlines():
        if not line.startswith("ATOM"):
            continue
        atom_name = line[12:16].strip()
        if atom_name != "CA":
            continue
        # Unique residue key: chain + residue number
        chain = line[21]
        res_num = line[22:26].strip()
        key = f"{chain}:{res_num}"
        if key in seen_residues:
            continue
        seen_residues.add(key)

        try:
            bfactor = float(line[60:66].strip())
            scores.append(round(bfactor, 2))
        except (ValueError, IndexError):
            continue

    return scores
