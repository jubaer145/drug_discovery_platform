from .base import BaseModule, ModuleInput, ModuleOutput


class ProteinDesignModule(BaseModule):
    """Wraps RFdiffusion for protein design. Implemented in Sprint 3."""

    def run(self, input: ModuleInput) -> ModuleOutput:
        raise NotImplementedError("ProteinDesignModule.run() — implemented in Sprint 3")
