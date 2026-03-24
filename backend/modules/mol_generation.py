from .base import BaseModule, ModuleInput, ModuleOutput


class MolGenerationModule(BaseModule):
    """Wraps REINVENT for de novo molecule generation. Implemented in Sprint 4."""

    def run(self, input: ModuleInput) -> ModuleOutput:
        raise NotImplementedError("MolGenerationModule.run() — implemented in Sprint 4")
