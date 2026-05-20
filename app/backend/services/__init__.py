"""Services layer for VigilAI business logic."""

from services.action_automator import ActionAutomator
from services.deduplicator import CrossDomainDeduplicator
from services.workbench_bridge import WorkbenchBridge

__all__ = ["ActionAutomator", "CrossDomainDeduplicator", "WorkbenchBridge"]
