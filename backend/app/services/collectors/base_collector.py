from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseCollector(ABC):
    """
    Abstract Base Class for TRACE-X Evidence Collectors.
    All collectors produce a standardized evidence bundle containing
    investigation metadata and raw artifact dictionaries.
    """

    @abstractmethod
    def collect(self, source_descriptor: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collects raw evidence from the specified source.

        Returns a dictionary structure:
        {
            "investigation_id": str,
            "title": str,
            "target_persona_a": str,
            "target_persona_b": str,
            "narrative": Optional[str],
            "artifacts": List[Dict[str, Any]]
        }
        """
        pass
