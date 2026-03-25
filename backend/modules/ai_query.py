import json
import re

import anthropic

from core.config import settings
from models.schemas import AIQueryInput
from .base import BaseModule, ModuleInput, ModuleOutput

SYSTEM_PROMPT = """\
You are a world-class drug discovery expert and medicinal chemist. \
Given a disease or condition described in plain language, identify the most \
promising molecular targets for drug development.

Prioritise targets that meet these criteria (in order of importance):
1. Have validated 3D structures deposited in the Protein Data Bank (PDB).
2. Possess known druggable binding pockets with favourable tractability.
3. Are supported by published clinical or preclinical evidence linking them \
   to the queried disease or condition.

Guidelines:
- Be honest about target difficulty. For example, APOE4 is "difficult" and \
  intrinsically disordered proteins are "difficult".
- Explain mechanisms in terms a medical student would understand — clear, \
  precise, but not oversimplified.
- For clinical_stage use exactly one of: "approved", "phase3_trials", \
  "preclinical", or "unknown".
- For confidence use exactly one of: "high", "medium", or "low".
- For difficulty use exactly one of: "easy", "moderate", or "difficult".

Respond ONLY with valid JSON matching this exact schema — no markdown fences, \
no commentary, no text outside the JSON object:

{
  "targets": [
    {
      "protein_name": "string",
      "gene_symbol": "string",
      "uniprot_id": "string or null",
      "full_name": "string",
      "confidence": "high | medium | low",
      "mechanism_summary": "2-sentence clinical explanation",
      "druggability_note": "1 sentence on pocket quality / tractability",
      "tags": ["string"],
      "has_pdb_structure": true,
      "clinical_stage": "approved | phase3_trials | preclinical | unknown",
      "difficulty": "easy | moderate | difficult"
    }
  ],
  "query_interpretation": "1 sentence summarising what disease/mechanism was detected",
  "confidence_explanation": "1 sentence on overall evidence quality"
}
"""


class AIQueryModule(BaseModule):
    """Calls Claude API to suggest molecular targets from a disease description."""

    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def validate_input(self, input: ModuleInput) -> tuple[bool, str]:
        if not isinstance(input, AIQueryInput):
            return False, "Input must be AIQueryInput"

        query = input.query.strip()
        if len(query) < 10:
            return False, "Query must be at least 10 characters long"
        if len(query) > 500:
            return False, "Query must be at most 500 characters long"
        if re.fullmatch(r"[\d\s\W]+", query):
            return False, "Query must contain meaningful text, not only numbers or symbols"
        if not (1 <= input.max_targets <= 8):
            return False, "max_targets must be between 1 and 8"

        return True, ""

    def run(self, input: ModuleInput) -> ModuleOutput:
        assert isinstance(input, AIQueryInput)

        message = self._client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Suggest up to {input.max_targets} drug targets for: "
                        f"{input.query}"
                    ),
                }
            ],
        )

        raw_text = message.content[0].text

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            return ModuleOutput(
                job_id=input.job_id,
                status="failed",
                data={},
                errors=[f"Claude returned invalid JSON: {exc}"],
            )

        return ModuleOutput(
            job_id=input.job_id,
            status="completed",
            data=data,
        )
