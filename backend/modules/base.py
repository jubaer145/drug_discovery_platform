# backend/modules/base.py

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class ModuleInput(BaseModel):
    job_id: str
    user_id: str | None = None


class ModuleOutput(BaseModel):
    job_id: str
    status: str          # "completed" | "failed"
    data: dict[str, Any]
    errors: list[str] = []
    warnings: list[str] = []


class BaseModule(ABC):
    """
    Contract for all pipeline modules.

    Subclasses implement validate_input() and run().
    Never override execute() — it handles logging and error wrapping.

    Usage:
        module = TargetLookupModule()
        result = module.execute(TargetLookupInput(job_id="abc", query="EGFR"))
    """

    def validate_input(self, input: ModuleInput) -> tuple[bool, str]:
        """
        Returns (is_valid, error_message).
        Override to add input-specific validation.
        """
        return True, ""

    @abstractmethod
    def run(self, input: ModuleInput) -> ModuleOutput:
        """Core logic. Only called if validate_input passes."""
        pass

    def execute(self, input: ModuleInput) -> ModuleOutput:
        logger.info(f"[{self.__class__.__name__}] Starting job {input.job_id}")
        try:
            is_valid, error_msg = self.validate_input(input)
            if not is_valid:
                logger.warning(f"[{self.__class__.__name__}] Validation failed: {error_msg}")
                return ModuleOutput(
                    job_id=input.job_id,
                    status="failed",
                    data={},
                    errors=[error_msg]
                )
            result = self.run(input)
            logger.info(f"[{self.__class__.__name__}] Completed job {input.job_id} — status: {result.status}")
            return result
        except Exception as e:
            logger.exception(f"[{self.__class__.__name__}] Unhandled error in job {input.job_id}")
            return ModuleOutput(
                job_id=input.job_id,
                status="failed",
                data={},
                errors=[f"Unhandled exception: {str(e)}"]
            )
