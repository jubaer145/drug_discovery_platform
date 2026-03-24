from .base import BaseModule, ModuleInput, ModuleOutput


class DockingModule(BaseModule):
    """Wraps AutoDock Vina for molecular docking. Implemented in Sprint 4."""

    def run(self, input: ModuleInput) -> ModuleOutput:
        raise NotImplementedError("DockingModule.run() — implemented in Sprint 4")
