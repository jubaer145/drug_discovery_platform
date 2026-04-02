import json
import logging

import anthropic
from rdkit import Chem

from core.config import settings
from models.schemas import MolGenerationInput
from .base import BaseModule, ModuleInput, ModuleOutput

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an expert medicinal chemist specializing in de novo drug design.
Given a protein target, generate novel drug-like molecules as SMILES strings
that could bind to the target's active site.

Requirements for each molecule:
- Valid SMILES syntax (will be validated by RDKit)
- Drug-like properties (MW 200-500, LogP 1-5, ≤5 HBD, ≤10 HBA)
- Novel scaffolds — not existing approved drugs
- Realistic synthetic accessibility

Respond ONLY with valid JSON — no markdown, no commentary:
{
  "molecules": [
    {
      "smiles": "c1ccc2c(c1)nc(n2)N1CCN(CC1)C(=O)c1ccccc1",
      "name": "Compound_1",
      "predicted_mw": 345.2,
      "predicted_logp": 2.8,
      "binding_rationale": "Targets the S1' pocket with a benzamide warhead",
      "novelty_note": "Novel pyrimidine-piperazine scaffold"
    }
  ],
  "design_strategy": "Approach used for molecule generation",
  "target_pocket_analysis": "Brief analysis of the binding site"
}
"""


class MolGenerationModule(BaseModule):
    """Generates novel drug-like molecules using AI (Claude API).

    In production, replace with REINVENT 4 for real LSTM-based SMILES generation.
    """

    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def validate_input(self, input: ModuleInput) -> tuple[bool, str]:
        if not isinstance(input, MolGenerationInput):
            return False, "Input must be MolGenerationInput"
        if input.num_molecules < 1 or input.num_molecules > 200:
            return False, "num_molecules must be between 1 and 200"
        return True, ""

    def run(self, input: ModuleInput) -> ModuleOutput:
        assert isinstance(input, MolGenerationInput)

        # Claude can realistically generate ~20 molecules per call
        batch_size = min(input.num_molecules, 20)

        try:
            message = self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": (
                        f"Generate {batch_size} novel drug-like molecules targeting "
                        f"{input.target_name or 'the specified protein'}.\n"
                        f"{input.target_info}"
                    ),
                }],
            )
            raw = message.content[0].text
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
                                errors=[f"AI generation failed: {e}"])

        # Validate SMILES with RDKit
        valid_molecules = []
        invalid_count = 0
        for mol_data in data.get("molecules", []):
            smiles = mol_data.get("smiles", "")
            mol = Chem.MolFromSmiles(smiles)
            if mol is not None:
                mol_data["smiles"] = Chem.MolToSmiles(mol)  # canonicalize
                mol_data["valid"] = True
                valid_molecules.append(mol_data)
            else:
                invalid_count += 1

        data["molecules"] = valid_molecules
        data["total_generated"] = len(valid_molecules)
        data["invalid_count"] = invalid_count

        return ModuleOutput(
            job_id=input.job_id,
            status="completed",
            data=data,
        )
