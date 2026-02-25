#!/usr/bin/env python3
"""Task hierarchy validation for governance enforcement.

Validates task graph structure at creation time:
- Parent requirement: only goal/learn types may omit parent
- Parent-child type compatibility (tasks under epics, epics under projects, etc.)
- Returns warnings (not errors) to avoid blocking creation

Later (after data cleanup): warnings can be escalated to errors.

Usage:
    from lib.task_validation import validate_hierarchy

    warnings = validate_hierarchy(
        task_type="task",
        parent_id=None,
        parent_type=None,
        project="aops",
    )
    # warnings: ["Task type 'task' should have a parent. ..."]
"""

from __future__ import annotations

# Types that are allowed at root level (no parent required)
ROOT_ALLOWED_TYPES = frozenset({"goal", "learn", "project"})

# Valid parent-child type relationships.
# Key = child type, Value = set of acceptable parent types.
# If a child type isn't in this map, any parent type is accepted.
VALID_PARENT_CHILD = {
    "action": {"task", "epic", "bug", "feature"},
    "task": {"epic", "project", "goal"},
    "bug": {"epic", "project", "goal"},
    "feature": {"epic", "project", "goal"},
    "epic": {"project", "goal"},
    "project": {"goal"},
    "learn": {"epic", "project", "goal"},  # learn can also be root
}


def validate_hierarchy(
    *,
    task_type: str,
    parent_id: str | None,
    parent_type: str | None = None,
    project: str | None = None,
) -> list[str]:
    """Validate task hierarchy relationships.

    Returns a list of warning strings. Empty list means no issues.
    Warnings do NOT block creation — they inform the caller of
    governance concerns that should be addressed.

    Args:
        task_type: The type of the task being created (e.g. "task", "epic", "goal")
        parent_id: The parent task ID, or None if no parent
        parent_type: The type of the parent task (if parent_id is provided and resolvable)
        project: The project slug (for context in warning messages)

    Returns:
        List of warning strings (empty if no issues)
    """
    warnings: list[str] = []

    # Check 1: Orphan detection — non-root types should have a parent
    if parent_id is None and task_type not in ROOT_ALLOWED_TYPES:
        warnings.append(
            f"Task type '{task_type}' should have a parent. "
            f"Only goal, learn, and project types can be root-level. "
            f"Consider assigning a parent to maintain graph hierarchy."
        )

    # Check 2: Parent-child type compatibility
    if parent_id is not None and parent_type is not None:
        valid_parents = VALID_PARENT_CHILD.get(task_type)
        if valid_parents is not None and parent_type not in valid_parents:
            warnings.append(
                f"Unusual hierarchy: '{task_type}' under '{parent_type}' "
                f"(parent: {parent_id}). Expected parent types for "
                f"'{task_type}': {sorted(valid_parents)}."
            )

    return warnings
