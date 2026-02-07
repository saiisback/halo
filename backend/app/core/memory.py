"""
Agent Memory System - Learning from compilation errors and successful patterns

Stores error→fix mappings and successful generation patterns in a JSON file.
Agents query this before each generation to avoid repeating mistakes.
"""

import json
import hashlib
import logging
import fcntl
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MEMORY_FILE = Path(__file__).parent.parent.parent / "knowledge" / "agent_memory.json"

DEFAULT_MEMORY = {
    "error_fixes": [],
    "successful_patterns": {},
    "generation_stats": {
        "total_generations": 0,
        "first_attempt_success": 0,
        "required_retries": 0,
        "common_errors": [],
    },
}


class AgentMemory:
    """File-based memory system for agent learning."""

    def __init__(self, memory_path: Path = MEMORY_FILE):
        self._path = memory_path
        self._data: Optional[dict] = None

    def _ensure_dir(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        """Load memory from disk."""
        if self._data is not None:
            return self._data

        self._ensure_dir()

        if not self._path.exists():
            self._data = json.loads(json.dumps(DEFAULT_MEMORY))
            return self._data

        try:
            with open(self._path, "r") as f:
                fcntl.flock(f, fcntl.LOCK_SH)
                try:
                    self._data = json.load(f)
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"[MEMORY] Failed to load memory file, resetting: {e}")
            self._data = json.loads(json.dumps(DEFAULT_MEMORY))

        return self._data

    def save(self):
        """Persist memory to disk with file locking."""
        if self._data is None:
            return

        self._ensure_dir()

        try:
            with open(self._path, "w") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    json.dump(self._data, f, indent=2)
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
        except OSError as e:
            logger.error(f"[MEMORY] Failed to save memory: {e}")

    @staticmethod
    def _spec_hash(template_type: str, spec: dict) -> str:
        """Create a short hash from template type + spec for dedup."""
        key = template_type + json.dumps(spec, sort_keys=True)
        return hashlib.sha256(key.encode()).hexdigest()[:12]

    def record_error(
        self,
        error_msg: str,
        code: str,
        fix_code: Optional[str] = None,
    ):
        """Record a compilation/deployment error and optional fix."""
        data = self.load()
        now = datetime.now(timezone.utc).isoformat()

        # Normalise error to a short pattern (first meaningful line)
        pattern = _extract_error_pattern(error_msg)

        # Check if we already track this pattern
        existing = None
        for entry in data["error_fixes"]:
            if entry["error_pattern"] == pattern:
                existing = entry
                break

        if existing:
            existing["occurrences"] += 1
            existing["last_seen"] = now
            if fix_code and not existing.get("fix_description"):
                existing["fix_description"] = _summarise_fix(error_msg, code, fix_code)
        else:
            data["error_fixes"].append({
                "error_pattern": pattern,
                "fix_description": _summarise_fix(error_msg, code, fix_code) if fix_code else "",
                "occurrences": 1,
                "last_seen": now,
            })

        # Keep only top 50 errors, sorted by occurrence
        data["error_fixes"].sort(key=lambda e: e["occurrences"], reverse=True)
        data["error_fixes"] = data["error_fixes"][:50]

        # Update common_errors in stats
        stats = data["generation_stats"]
        stats["required_retries"] = stats.get("required_retries", 0) + 1
        top_errors = [e["error_pattern"] for e in data["error_fixes"][:10]]
        stats["common_errors"] = top_errors

        self.save()

    def record_success(
        self,
        template_type: str,
        spec: dict,
        code: str,
        attempts: int = 1,
    ):
        """Record a successful generation (compiled + deployed)."""
        data = self.load()
        now = datetime.now(timezone.utc).isoformat()
        key = f"{template_type}_{self._spec_hash(template_type, spec)}"

        data["successful_patterns"][key] = {
            "spec_summary": spec.get("description", "")[:200],
            "code_snippet": code[:500],
            "compile_attempts": attempts,
            "timestamp": now,
        }

        # Cap at 100 patterns
        if len(data["successful_patterns"]) > 100:
            # Remove oldest entries
            sorted_keys = sorted(
                data["successful_patterns"],
                key=lambda k: data["successful_patterns"][k].get("timestamp", ""),
            )
            for old_key in sorted_keys[: len(sorted_keys) - 100]:
                del data["successful_patterns"][old_key]

        stats = data["generation_stats"]
        stats["total_generations"] = stats.get("total_generations", 0) + 1
        if attempts == 1:
            stats["first_attempt_success"] = stats.get("first_attempt_success", 0) + 1

        self.save()

    def get_lessons_learned(self, max_items: int = 10) -> str:
        """Return a formatted string of top error patterns + fixes for prompt injection."""
        data = self.load()
        fixes = data.get("error_fixes", [])

        if not fixes:
            return ""

        lines = ["## LESSONS LEARNED (from previous builds — avoid these mistakes):"]
        for entry in fixes[:max_items]:
            pattern = entry["error_pattern"]
            fix = entry.get("fix_description", "")
            count = entry.get("occurrences", 1)
            if fix:
                lines.append(f"- ERROR ({count}x): {pattern} → FIX: {fix}")
            else:
                lines.append(f"- ERROR ({count}x): {pattern}")

        return "\n".join(lines)

    def get_similar_success(self, template_type: str, spec: dict) -> Optional[str]:
        """Return past working code snippet if a similar spec was built before."""
        data = self.load()
        key = f"{template_type}_{self._spec_hash(template_type, spec)}"

        entry = data.get("successful_patterns", {}).get(key)
        if entry:
            return entry.get("code_snippet")

        # Fallback: look for any entry with the same template_type prefix
        for k, v in data.get("successful_patterns", {}).items():
            if k.startswith(f"{template_type}_"):
                return v.get("code_snippet")

        return None

    def get_stats(self) -> dict:
        """Return generation statistics."""
        data = self.load()
        return data.get("generation_stats", {})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_error_pattern(error_msg: str) -> str:
    """Boil a compiler error down to a short, matchable pattern."""
    for line in error_msg.splitlines():
        line = line.strip()
        # Grab the first line that looks like a real error
        if line.startswith("error") or "cannot find" in line or "expected" in line or "no method" in line:
            # Trim file paths
            if "] " in line:
                line = line.split("] ", 1)[-1]
            return line[:200]
    # Fallback: first 200 chars
    return error_msg.strip()[:200]


def _summarise_fix(error_msg: str, original_code: str, fixed_code: str) -> str:
    """Create a short human-readable description of what changed."""
    # Simple heuristic: describe what was added/removed
    orig_lines = set(original_code.splitlines())
    fix_lines = set(fixed_code.splitlines())

    added = fix_lines - orig_lines
    removed = orig_lines - fix_lines

    parts = []
    if removed:
        sample = next(iter(removed)).strip()[:80]
        parts.append(f"removed '{sample}'")
    if added:
        sample = next(iter(added)).strip()[:80]
        parts.append(f"added '{sample}'")

    return "; ".join(parts) if parts else "code adjusted"


# Singleton for convenience
_memory_instance: Optional[AgentMemory] = None


def get_memory() -> AgentMemory:
    """Get the global AgentMemory singleton."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = AgentMemory()
    return _memory_instance
