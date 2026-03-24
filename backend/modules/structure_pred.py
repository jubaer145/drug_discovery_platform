from .base import BaseModule, ModuleInput, ModuleOutput


class StructurePredModule(BaseModule):
    """Wraps ESMFold / AlphaFold API for structure prediction. Implemented in Sprint 3."""

    def run(self, input: ModuleInput) -> ModuleOutput:
        raise NotImplementedError("StructurePredModule.run() — implemented in Sprint 3")
