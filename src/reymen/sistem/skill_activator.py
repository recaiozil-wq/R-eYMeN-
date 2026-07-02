# -*- coding: utf-8 -*-
"""reymen/sistem/skill_activator.py — Auto-activation framework for ReYMeN skills.

Minimal registry that maps skill names to file paths, with an activate()
method that reads the .md content. Uses a dict-based registry with
persist()/load() for durable state across sessions.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SkillActivator:
    """Dict-based registry mapping skill names to file paths.

    Provides activate() to load skill content from disk and
    persist()/load() for durable JSON state.
    """

    def __init__(self, registry_path: Optional[Path] = None):
        self._registry: Dict[str, str] = {}  # name -> full file path
        self._registry_path = registry_path or Path.home() / ".reymen" / "skill_registry.json"

    # ── Registry management ──────────────────────────────────────────────

    def register(self, name: str, file_path: str | Path) -> None:
        """Register a skill by name pointing to its .md file path."""
        self._registry[name] = str(Path(file_path).resolve())
        logger.debug("Skill registered: %s -> %s", name, file_path)

    def unregister(self, name: str) -> bool:
        """Remove a skill from the registry. Returns True if it existed."""
        return self._registry.pop(name, None) is not None

    def get(self, name: str) -> Optional[str]:
        """Return the registered file path for a skill, or None."""
        return self._registry.get(name)

    def list_registered(self) -> Dict[str, str]:
        """Return a copy of the full registry dict (name -> path)."""
        return dict(self._registry)

    def is_registered(self, name: str) -> bool:
        """Check if a skill name is registered."""
        return name in self._registry

    # ── Activation ───────────────────────────────────────────────────────

    def activate(self, name: str) -> Optional[str]:
        """Read and return the .md content of a registered skill.

        Args:
            name: Registered skill name.

        Returns:
            str: The full .md content if found and readable, else None.
        """
        path_str = self._registry.get(name)
        if not path_str:
            logger.warning("Skill not registered: %s", name)
            return None

        path = Path(path_str)
        if not path.exists():
            logger.warning("Skill file missing: %s (%s)", name, path)
            return None

        try:
            content = path.read_text(encoding="utf-8")
            logger.info("Skill activated: %s (%d chars)", name, len(content))
            return content
        except Exception as exc:
            logger.error("Failed to read skill %s: %s", name, exc)
            return None

    # ── Auto-scan: discover .md files in a directory ─────────────────────

    def scan_directory(self, skills_dir: Path, pattern: str = "*.md") -> int:
        """Scan a directory and register all matching .md files.

        Args:
            skills_dir: Directory containing skill .md files.
            pattern: Glob pattern to match (default: '*.md').

        Returns:
            int: Number of newly registered skills.
        """
        if not skills_dir.exists():
            logger.warning("Skills directory not found: %s", skills_dir)
            return 0

        count = 0
        for md_file in sorted(skills_dir.glob(pattern)):
            if md_file.is_file():
                name = md_file.stem  # filename without extension
                if not self.is_registered(name):
                    self.register(name, md_file)
                    count += 1

        return count

    # ── Persistence ──────────────────────────────────────────────────────

    def persist(self) -> None:
        """Save registry to JSON file."""
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._registry_path.write_text(
                json.dumps(self._registry, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            logger.debug("Registry persisted to %s", self._registry_path)
        except Exception as exc:
            logger.error("Failed to persist registry: %s", exc)

    def load(self) -> None:
        """Load registry from JSON file (replaces current state)."""
        if not self._registry_path.exists():
            logger.debug("No registry file found at %s", self._registry_path)
            return
        try:
            data = json.loads(self._registry_path.read_text(encoding="utf-8"))
            self._registry = data
            logger.debug("Registry loaded: %d entries", len(self._registry))
        except Exception as exc:
            logger.error("Failed to load registry: %s", exc)
            self._registry = {}

    # ── Convenience ──────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._registry)

    def __contains__(self, name: str) -> bool:
        return name in self._registry

    def __repr__(self) -> str:
        return f"SkillActivator(entries={len(self._registry)}, path={self._registry_path})"
