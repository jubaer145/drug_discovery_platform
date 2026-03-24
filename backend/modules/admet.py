from .base import BaseModule, ModuleInput, ModuleOutput


class AdmetModule(BaseModule):
    """Uses RDKit + SwissADME for ADMET property prediction. Implemented in Sprint 5."""

    def run(self, input: ModuleInput) -> ModuleOutput:
        raise NotImplementedError("AdmetModule.run() — implemented in Sprint 5")
