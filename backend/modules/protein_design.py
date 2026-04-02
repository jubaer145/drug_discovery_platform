import json
import logging

import anthropic

from core.config import settings
from models.schemas import ProteinDesignInput
from .base import BaseModule, ModuleInput, ModuleOutput

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an expert computational protein engineer specializing in de novo protein design.
Given a target protein structure (PDB data), design novel protein binder sequences that
could interact with the target's binding site.

For each designed sequence:
- Generate a realistic amino acid sequence (single-letter code, 50-150 residues)
- Estimate a confidence/pLDDT score (0-100, be realistic)
- Describe the binding strategy (helix bundle, beta sheet, loop-mediated, etc.)
- Note key interacting residues

Respond ONLY with valid JSON matching this schema — no markdown, no commentary:
{
  "designs": [
    {
      "sequence": "MKTAY...",
      "name": "Binder_1",
      "length": 85,
      "predicted_plddt": 78.5,
      "binding_strategy": "Three-helix bundle targeting the active site cleft",
      "key_residues": "D23, E45, R67 form salt bridges with target",
      "estimated_affinity_nm": 150
    }
  ],
  "target_analysis": "Brief analysis of the target's druggable surface",
  "design_strategy": "Overall approach taken for the designs"
}
"""


class ProteinDesignModule(BaseModule):
    """Designs novel protein binders using AI (Claude API).

    In production, replace with ProteinMPNN + RFdiffusion for real structure-based design.
    """

    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def validate_input(self, input: ModuleInput) -> tuple[bool, str]:
        if not isinstance(input, ProteinDesignInput):
            return False, "Input must be ProteinDesignInput"
        if not input.pdb_path:
            return False, "pdb_path is required"
        if input.num_designs < 1 or input.num_designs > 20:
            return False, "num_designs must be between 1 and 20"
        return True, ""

    def run(self, input: ModuleInput) -> ModuleOutput:
        assert isinstance(input, ProteinDesignInput)

        # Load PDB info for context
        pdb_info = ""
        try:
            from core.storage import download_file
            bucket, key = input.pdb_path.split("/", 1)
            pdb_data = download_file(bucket, key)
            # Send first 2000 chars of PDB for context
            pdb_info = pdb_data.decode("utf-8", errors="ignore")[:2000]
        except Exception as e:
            pdb_info = f"Could not load PDB: {e}"

        try:
            message = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Design {input.num_designs} novel protein binders for this target"
                        f"{' (' + input.target_name + ')' if input.target_name else ''}.\n\n"
                        f"Target PDB data (first 2000 chars):\n{pdb_info}"
                    ),
                }],
            )
            raw = message.content[0].text
            # Strip markdown fences if present
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            data = json.loads(text)
        except json.JSONDecodeError as e:
            return ModuleOutput(job_id=input.job_id, status="failed", data={},
                                errors=[f"AI returned invalid JSON: {e}"])
        except Exception as e:
            return ModuleOutput(job_id=input.job_id, status="failed", data={},
                                errors=[f"AI design failed: {e}"])

        return ModuleOutput(
            job_id=input.job_id,
            status="completed",
            data=data,
        )
