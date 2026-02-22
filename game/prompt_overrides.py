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
    """Generate a descriptive summary of changes between two texts.

    Identifies which sections were added/modified/removed and extracts
    key phrases from changed content to produce a human-readable description.
    """
    import re

    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    added_count = 0
    removed_count = 0
    changed_count = 0

    # Collect actual changed/added/removed lines for analysis
    added_lines = []
    removed_lines = []
    modified_regions = []  # (old_lines_slice, new_lines_slice)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'insert':
            added_count += (j2 - j1)
            added_lines.extend(new_lines[j1:j2])
        elif tag == 'delete':
            removed_count += (i2 - i1)
            removed_lines.extend(old_lines[i1:i2])
        elif tag == 'replace':
            changed_count += max(i2 - i1, j2 - j1)
            modified_regions.append((old_lines[i1:i2], new_lines[j1:j2]))
            added_lines.extend(new_lines[j1:j2])

    if not added_count and not removed_count and not changed_count:
        return "No changes"

    # Extract section headers from changed content
    # Matches patterns like "10. NPC DEPTH", "ROMANTIC CONNECTIONS (SUBTLE):",
    # "NPC CONTINUITY (IMPORTANT):", "SMARTPHONE AS SECRET WEAPON", etc.
    section_pattern = re.compile(
        r'^\s*(?:\d+[\.\)]\s+)?([A-Z][A-Z\s\-/]+(?:\([^)]*\))?)\s*[:.]?\s*$'
    )
    keyword_pattern = re.compile(
        r'^\s*(?:\d+[\.\)]\s+)?([A-Z][A-Z\s\-/]{3,}(?:\([^)]*\))?)'
    )

    # Find section headers in added/changed content
    new_sections = []
    for line in added_lines:
        stripped = line.strip()
        if not stripped:
            continue
        m = section_pattern.match(line)
        if m:
            new_sections.append(m.group(1).strip())
        elif not new_sections:
            # Also check for keyword-style headers
            m2 = keyword_pattern.match(line)
            if m2 and len(m2.group(1).strip()) > 5:
                new_sections.append(m2.group(1).strip())

    # Find section headers in removed content
    removed_sections = []
    for line in removed_lines:
        m = section_pattern.match(line)
        if m:
            removed_sections.append(m.group(1).strip())

    # Find which existing sections were modified (look at context around changes)
    modified_sections = []
    for old_chunk, new_chunk in modified_regions:
        # Look for section headers near the modified region
        for line in old_chunk + new_chunk:
            m = keyword_pattern.match(line)
            if m and len(m.group(1).strip()) > 5:
                sec = m.group(1).strip()
                if sec not in new_sections and sec not in modified_sections:
                    modified_sections.append(sec)

    # Extract key themes from added content (non-header lines)
    key_phrases = _extract_key_phrases(added_lines)

    # Build descriptive summary
    parts = []

    if new_sections:
        # Deduplicate and limit
        unique_sections = list(dict.fromkeys(new_sections))[:3]
        section_names = [s.title() for s in unique_sections]
        parts.append(f"Added: {', '.join(section_names)}")

    if removed_sections:
        unique_removed = list(dict.fromkeys(removed_sections))[:3]
        section_names = [s.title() for s in unique_removed]
        parts.append(f"Removed: {', '.join(section_names)}")

    if modified_sections and not new_sections:
        unique_modified = list(dict.fromkeys(modified_sections))[:3]
        section_names = [s.title() for s in unique_modified]
        parts.append(f"Modified: {', '.join(section_names)}")

    # Add key themes if we found them and don't already have section info
    if key_phrases and not parts:
        parts.append(f"Changes related to: {', '.join(key_phrases[:3])}")
    elif key_phrases and len(parts) == 1:
        parts.append(f"Focus: {', '.join(key_phrases[:2])}")

    # Add stats as secondary info
    stats = []
    if added_count:
        stats.append(f"+{added_count}")
    if removed_count:
        stats.append(f"-{removed_count}")
    if changed_count:
        stats.append(f"~{changed_count}")
    similarity = round(matcher.ratio() * 100)

    if parts:
        return f"{'. '.join(parts)}. ({', '.join(stats)} lines, {similarity}% similar)"
    else:
        return f"{', '.join(stats)} lines changed ({similarity}% similar)"


def _extract_key_phrases(lines: list) -> list:
    """Extract key thematic phrases from added/changed lines."""
    import re

    # Common meaningful keywords in game prompts
    theme_keywords = {
        'npc': 'NPC depth',
        'romantic': 'romantic connections',
        'romance': 'romantic connections',
        'mate': 'romantic connections',
        'relationship': 'relationships',
        'continuity': 'continuity',
        'fulfillment': 'fulfillment tracking',
        'belonging': 'belonging',
        'legacy': 'legacy',
        'freedom': 'freedom',
        'window': 'time machine window',
        'dice': 'luck/dice mechanics',
        'luck': 'luck/dice mechanics',
        'historical': 'historical accuracy',
        'choice': 'choice design',
        'item': 'item handling',
        'smartphone': 'smartphone usage',
        'phone': 'smartphone usage',
        'wikipedia': 'smartphone usage',
        'antibiotics': 'item usage',
        'narrative': 'narrative style',
        'voice': 'narrative voice',
        'tone': 'tone/mood',
        'pacing': 'pacing',
        'engagement': 'engagement',
        'immersive': 'immersion',
        'emotion': 'emotional depth',
        'setback': 'setbacks/challenges',
        'obstacle': 'setbacks/challenges',
        'survival': 'survival mechanics',
        'era': 'era handling',
        'time travel': 'time travel mechanics',
    }

    found = {}
    text_block = ' '.join(line.strip().lower() for line in lines if line.strip())

    for keyword, theme in theme_keywords.items():
        if keyword in text_block and theme not in found.values():
            found[keyword] = theme

    return list(dict.fromkeys(found.values()))[:4]
