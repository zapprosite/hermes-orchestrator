"""OrchestratorPlugin: hermes-orchestrator para hermes-agent."""
from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger("hermes-orchestrator")


class OrchestratorPlugin:
    """Plugin standalone."""
    name = "hermes-orchestrator"
    kind = "standalone"
    version = "1.0.0"

    def register(self, ctx) -> None:
        """Hook de registro."""
        # Tools
        ctx.register_tool("hermes_orchestrator_status", self._tool_status)

        # Skills
        skill_path = self._skill_path()
        if skill_path.exists():
            ctx.register_skill("hermes-orchestrator", skill_path)

        log.info("hermes-orchestrator v%s registrado", self.version)

    def _skill_path(self) -> Path:
        return Path(__file__).parent.parent.parent / "skills" / "orchestrator"

    def _tool_status(self, **_):
        return {"status": "ready", "version": self.version}
