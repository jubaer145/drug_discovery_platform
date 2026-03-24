from .base import BaseModule, ModuleInput, ModuleOutput


class TargetLookupModule(BaseModule):
    """Fetches protein data from PDB and UniProt. Implemented in Sprint 1."""

    def run(self, input: ModuleInput) -> ModuleOutput:
        raise NotImplementedError("TargetLookupModule.run() — implemented in Sprint 1")
