"""
Prompt Override System for Narrative Lab

Provides in-memory caching of active prompt template overrides.
Zero DB overhead during normal gameplay — cache is only refreshed
when admin pushes or reverts a prompt via the lab.

Usage in prompts.py:
    from prompt_overrides import get_active_template
    template = get_active_template("system") or DEFAULT_SYSTEM_TEMPLATE
"""

import difflib
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# In-memory cache: prompt_type -> template text
_active_overrides: Dict[str, str] = {}

# Supported prompt types
SUPPORTED_TYPES = ["system", "turn", "arrival", "window"]


def get_active_template(prompt_type: str) -> Optional[str]:
    """Get the active override template for a prompt type, or None for default."""
    return _active_overrides.get(prompt_type)


def push_live(prompt_type: str, template: str):
    """Push a template override live. Updates in-memory cache."""
    if prompt_type not in SUPPORTED_TYPES:
        raise ValueError(f"Unsupported prompt type: {prompt_type}")
    _active_overrides[prompt_type] = template
    logger.info(f"Prompt override pushed live: {prompt_type}")


def revert_to_baseline(prompt_type: str):
    """Remove override for a prompt type, reverting to the default template."""
    removed = _active_overrides.pop(prompt_type, None)
    if removed:
        logger.info(f"Prompt override reverted: {prompt_type}")


def get_live_status() -> Dict[str, bool]:
    """Return which prompt types have active overrides."""
    return {pt: (pt in _active_overrides) for pt in SUPPORTED_TYPES}


def load_overrides_from_db():
    """
    Load any active (is_live=True) prompt variants from the database
    into the in-memory cache. Called on app startup.
    """
    try:
        import lab_db
        for prompt_type in SUPPORTED_TYPES:
            variant = lab_db.get_live_variant(prompt_type)
            if variant:
                _active_overrides[prompt_type] = variant['template']
                logger.info(f"Loaded active override for '{prompt_type}' (variant: {variant['name']})")
    except Exception as e:
        logger.warning(f"Could not load prompt overrides from DB: {e}")


def get_baseline_template(prompt_type: str) -> Optional[str]:
    """Get the baseline (default) template for a prompt type from prompts.py."""
    try:
        from prompts import BASELINE_TEMPLATES
        return BASELINE_TEMPLATES.get(prompt_type)
    except ImportError:
        return None


def compute_diffs(prompt_type: str, new_template: str, previous_template: str = None) -> Dict:
    """
    Compute diffs for a new prompt variant.

    Returns:
        {
            "diff_vs_baseline": unified diff string (or None),
            "diff_vs_previous": unified diff string (or None),
            "change_summary": one-line summary of changes
        }
    """
    baseline = get_baseline_template(prompt_type)

    diff_vs_baseline = None
    diff_vs_previous = None
    change_summary = ""

    if baseline:
        diff_vs_baseline = _unified_diff(baseline, new_template, "Baseline", "New")
        change_summary = _summarize_changes(baseline, new_template)

    if previous_template:
        diff_vs_previous = _unified_diff(previous_template, new_template, "Previous", "New")
        if not change_summary:
            change_summary = _summarize_changes(previous_template, new_template)

    return {
        "diff_vs_baseline": diff_vs_baseline,
        "diff_vs_previous": diff_vs_previous,
        "change_summary": change_summary,
    }


def _unified_diff(old_text: str, new_text: str, old_label: str = "old", new_label: str = "new") -> str:
    """Compute unified diff between two texts."""
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=old_label, tofile=new_label,
        lineterm=""
    )
    return "\n".join(diff)


def _summarize_changes(old_text: str, new_text: str) -> str:
    """Generate a one-line summary of changes between two texts."""
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    added = 0
    removed = 0
    changed = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'insert':
            added += (j2 - j1)
        elif tag == 'delete':
            removed += (i2 - i1)
        elif tag == 'replace':
            changed += max(i2 - i1, j2 - j1)

    similarity = round(matcher.ratio() * 100)

    parts = []
    if added:
        parts.append(f"+{added} lines")
    if removed:
        parts.append(f"-{removed} lines")
    if changed:
        parts.append(f"~{changed} lines changed")
    if not parts:
        return "No changes"

    return f"{', '.join(parts)} ({similarity}% similar)"
