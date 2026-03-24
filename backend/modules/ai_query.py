from .base import BaseModule, ModuleInput, ModuleOutput


class AIQueryModule(BaseModule):
    """Calls Claude API to suggest molecular targets from a disease description. Implemented in Sprint 2."""

    def run(self, input: ModuleInput) -> ModuleOutput:
        raise NotImplementedError("AIQueryModule.run() — implemented in Sprint 2")
