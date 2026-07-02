"""ReYMeN Web Search Provider ABC
===============================

Defines the pluggable-backend interface for web search and content extraction.
Bağımsız ReYMeN sürümü — herhangi bir Hermes bağımlılığı yoktur.

Response shape (search):
    {"success": True, "data": {"web": [{"title": str, "url": str, "description": str, "position": int}, ...]}}

Response shape (extract):
    {"success": True, "data": [{"url": str, "title": str, "content": str, "raw_content": str, "metadata": dict}, ...]}

On failure:
    {"success": False, "error": str}
"""

from __future__ import annotations

import abc
from typing import Any, Dict, List


class WebSearchProvider(abc.ABC):
    """Abstract base class for a web search/extract backend.

    Subclasses must implement is_available() and at least one of
    search() / extract().
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Stable short identifier (lowercase, no spaces)."""

    @property
    def display_name(self) -> str:
        return self.name

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Return True when this provider can service calls (env var check, etc.)."""

    def supports_search(self) -> bool:
        return True

    def supports_extract(self) -> bool:
        return False

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        raise NotImplementedError(f"{self.name} does not support search")

    def extract(self, urls: List[str], **kwargs: Any) -> Any:
        """Extract content from URLs. May be async."""
        raise NotImplementedError(f"{self.name} does not support extract")

    def get_setup_schema(self) -> Dict[str, Any]:
        return {"name": self.display_name, "badge": "", "tag": "", "env_vars": []}
