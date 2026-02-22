"""
Portrait Generator for Anachron V2

Generates cinematic ensemble portrait images at the end of a game when a player
chooses to stay. Uses a two-stage approach:
  1. Claude extracts structured visual scene data from the narrative
  2. Scene data is assembled into a detailed image prompt
  3. OpenAI gpt-image-1.5 generates the portrait image

The resulting image is saved to static/portraits/ and the path stored in aoa_entries.
"""

import os
import re
import json
import base64
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Try to import SDKs
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = bool(os.environ.get('OPENAI_API_KEY'))
except ImportError:
    OPENAI_AVAILABLE = False

PORTRAITS_DIR = os.environ.get(
    'RAILWAY_VOLUME_MOUNT_PATH',
    os.path.join(os.path.dirname(__file__), '..', 'data', 'portraits')
)


# ---------------------------------------------------------------------------
# Stage 1: Scene Extraction Prompt (sent to Claude)
# ---------------------------------------------------------------------------

SCENE_EXTRACTION_PROMPT = """You are analyzing the ending of a time-travel adventure game to extract visual scene details for a painted ensemble portrait illustration.

The player chose to stay in {final_era} ({final_era_year}). Their character name is {character_name}. Their ending type is {ending_type} with scores: Belonging {belonging_score}, Legacy {legacy_score}, Freedom {freedom_score}.

Key NPCs encountered across all eras: {key_npcs}
Items used during the journey: {items_used}

PLAYER NARRATIVE (the richest source — describes their life after staying):
{player_narrative}

HISTORIAN NARRATIVE (third-person summary):
{historian_narrative}

Extract detailed visual scene information as JSON for a painted ensemble portrait in the style of a 1980s adventure movie poster.

The composition: ultra-wide shot of a grand room. Central figure seated in an ornate armchair (ONLY person sitting). All others standing in a natural V-formation. The room/setting is 70% of the image with the people placed dramatically in the center. Extreme spotlight on the figures, the rest of the room in deep shadow.

IMPORTANT GUIDELINES:
- Only include characters from the FINAL ERA narrative
- If children/grandchildren exist, they MUST appear
- Central figure should appear NO OLDER THAN 50 — strong, dignified, with touches of silver hair. Never frail or elderly.
- Keep descriptions SHORT and DENSE — 1-2 phrases per field, not paragraphs
- Expression: confident, proud, warm dignity. Chins up. Some characters may have a faint warm smile. Central figure: strong composure with warmth in the eyes. NOT morose, tired, or sad.
- Setting: their SPECIFIC achievement (restaurant, farm, workshop — not generic backdrop)
- Include 2-3 journey artifacts as props
- Keep room description minimal (it will be mostly in shadow)

Return ONLY a JSON object (no markdown, no explanation) with these keys:
- central_figure: {{name, age_appearance, clothing, expression}} (1-2 sentences each)
- characters: array of max 7, each with {{name, relationship, appearance, clothing, expression}} (1 sentence each)
- setting: {{city, era_decade, architecture, key_artifact_on_wall, windows_view}}
- objects: array of 2-3 short strings describing props
- mood: {{color_palette, emotional_tone}}"""

# ---------------------------------------------------------------------------
# Stage 2: Image Prompt Template (fixed sections + dynamic fill)
# gpt-image-1 has no practical prompt length limit — use full detail.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# SECTION A: Immutable Style Block (always first, dominates prompt attention)
# Follows ChatGPT's guidance: 50% lighting, 30% composition, 20% era details.
# Declarative, not prose. Lighting repeated for emphasis.
# ---------------------------------------------------------------------------

STYLE_BLOCK = """STYLE:
Painted 1980s epic adventure movie poster.
Thick visible oil brushstrokes.
Rich saturated pigments.
Hand-painted illustration.
Not photorealistic.

Ultra-wide 3:2 landscape.

LIGHTING:
Warm golden chiaroscuro like a richly lit oil painting.
Single powerful warm spotlight from above the central group.
Figures glow with golden highlights on faces, hands, and fabric.
Sculpted shadows under chins and behind bodies add depth.
The background is warmly lit but secondary — architectural details, wall decorations, and furniture are clearly visible in warm amber tones.
The room feels like a candlelit interior with warm ambient glow throughout.
Figures are the brightest part of the image but the room is NOT dark — it has rich warm light.
Brightness contrast is moderate — figures are about 2x brighter than the room.
Everything warm and golden. No cold or harsh lighting.

COMPOSITION:
Ultra-wide establishing shot pulled far back.
The architecture dominates the frame — 70-75% of the image is room and background.
The figures occupy the center but are dwarfed by the vast space around them.
Floor visible.
Ceiling visible in shadow.
One central seated figure in ornate chair at exact center.
Only one person seated.
All others stand behind in loose V-formation.
Heights varied naturally.
Everyone faces generally forward.

MOOD:
Confident. Warm. Dignified. Proud.
Chins raised. Shoulders back. Strong posture.
Expressions convey quiet pride and satisfaction — not sadness, not fatigue, not weariness.
Some characters may have the faintest hint of a warm smile.
Central figure: strong, composed, serene confidence with warmth in the eyes. Maximum age 50. Not elderly. Not frail. Strong and vital with distinguished silver-touched hair.
The overall feeling is of a family portrait celebrating triumph and legacy."""

IMAGE_PROMPT_FOOTER = "NO text, NO titles, NO logos, NO borders, NO watermarks."


def extract_scene(aoa_data: dict) -> Optional[dict]:
    """Stage 1: Use Claude to extract structured visual scene data from narratives."""
    if not ANTHROPIC_AVAILABLE:
        logger.warning("Anthropic SDK not available, cannot extract scene")
        return None

    prompt = SCENE_EXTRACTION_PROMPT.format(
        final_era=aoa_data.get('final_era', 'Unknown'),
        final_era_year=aoa_data.get('final_era_year', 'Unknown'),
        character_name=aoa_data.get('character_name', 'The Traveler'),
        ending_type=aoa_data.get('ending_type', 'balanced'),
        belonging_score=aoa_data.get('belonging_score', 0),
        legacy_score=aoa_data.get('legacy_score', 0),
        freedom_score=aoa_data.get('freedom_score', 0),
        key_npcs=', '.join(aoa_data.get('key_npcs', [])) if isinstance(aoa_data.get('key_npcs'), list) else str(aoa_data.get('key_npcs', '[]')),
        items_used=', '.join(aoa_data.get('items_used', [])) if isinstance(aoa_data.get('items_used'), list) else str(aoa_data.get('items_used', '[]')),
        player_narrative=aoa_data.get('player_narrative', ''),
        historian_narrative=aoa_data.get('historian_narrative', ''),
    )

    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        # Parse JSON — handle potential markdown wrapping
        if text.startswith('```'):
            text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()

        scene = json.loads(text)
        logger.info(f"Scene extracted: {len(scene.get('characters', []))} characters")
        return scene
    except Exception as e:
        logger.error(f"Scene extraction failed: {e}")
        return None


def build_scene_blocks(scene: dict) -> str:
    """
    Build only the dynamic scene blocks (ERA, ROOM DETAILS, CENTRAL FIGURE, etc.).
    Does NOT include STYLE_BLOCK or IMAGE_PROMPT_FOOTER — those come from the user's template.
    Used by the Image Lab to append scene data to the user's editable prompt template.
    """
    parts = []

    setting = scene.get('setting', {})
    parts.append(f"\nERA:\n{setting.get('city', 'Historic city')}, {setting.get('era_decade', '')}.")

    room_bits = []
    if setting.get('architecture'):
        room_bits.append(setting['architecture'])
    if setting.get('key_artifact_on_wall'):
        room_bits.append(setting['key_artifact_on_wall'])
    if room_bits:
        parts.append(f"\nROOM DETAILS:\n{'. '.join(room_bits)}.")

    cf = scene.get('central_figure', {})
    parts.append(f"\nCENTRAL FIGURE:\n{cf.get('name', 'The protagonist')}, "
                 f"{cf.get('age_appearance', 'weathered figure')}. "
                 f"{cf.get('clothing', 'Era-appropriate clothing')}.")

    characters = scene.get('characters', [])
    if characters:
        char_lines = []
        for char in characters[:5]:
            char_lines.append(f"{char.get('name', 'Figure')} ({char.get('relationship', 'companion')}), "
                              f"{char.get('appearance', '')}, "
                              f"{char.get('clothing', '')}.")
        parts.append(f"\nSUPPORTING CHARACTERS:\n" + "\n".join(char_lines))

    objects = scene.get('objects', [])
    if objects:
        obj_strs = [o if isinstance(o, str) else o.get('description', str(o)) for o in objects[:3]]
        parts.append(f"\nPROPS:\n{'; '.join(obj_strs)}.")

    return '\n'.join(parts)


def get_live_style_block() -> str:
    """Return the live image style prompt from DB, falling back to the hardcoded STYLE_BLOCK."""
    try:
        import psycopg2.extras
        from db import get_db
        with get_db() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT template FROM lab_prompt_variants WHERE prompt_type = 'image_style' AND is_live = true ORDER BY version_number DESC LIMIT 1"
                )
                row = cur.fetchone()
                if row:
                    return row['template']
    except Exception as e:
        logger.warning(f"Could not load live image prompt from DB, using default: {e}")
    return STYLE_BLOCK


def build_image_prompt(scene: dict) -> str:
    """
    Stage 2: Assemble full image prompt = style block + scene blocks + footer.
    Uses the live DB style block if one has been pushed to production, otherwise STYLE_BLOCK.
    """
    return get_live_style_block() + build_scene_blocks(scene) + f"\n\n{IMAGE_PROMPT_FOOTER}"


def _save_image_b64(b64_data: str, entry_id: str) -> Optional[str]:
    """Decode base64 image data and save to static/portraits/."""
    os.makedirs(PORTRAITS_DIR, exist_ok=True)
    filename = f"{entry_id}.png"
    filepath = os.path.join(PORTRAITS_DIR, filename)

    try:
        image_bytes = base64.b64decode(b64_data)
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
        logger.info(f"Portrait saved: {filepath} ({len(image_bytes)} bytes)")
        return f"/portraits/{filename}"
    except Exception as e:
        logger.error(f"Failed to save portrait image: {e}")
        return None


def _update_aoa_portrait(entry_id: str, image_path: str, prompt_text: str):
    """Update the aoa_entries row with portrait data."""
    try:
        from db import get_db
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE aoa_entries SET portrait_image_path = %s, portrait_prompt = %s WHERE entry_id = %s",
                    (image_path, prompt_text, entry_id)
                )
        logger.info(f"AoA entry updated with portrait: {entry_id}")
    except Exception as e:
        logger.error(f"Failed to update AoA portrait: {e}")


def generate_portrait(entry_id: str) -> Optional[str]:
    """
    Orchestrator: generate a portrait image for an AoA entry.

    1. Load AoA data from DB
    2. Extract scene via Claude
    3. Build detailed image prompt
    4. Generate image via OpenAI gpt-image-1
    5. Save image and update DB

    Returns the serving path (e.g. "/portraits/aoa_xxx.png") or None.
    """
    if not OPENAI_AVAILABLE:
        logger.warning("OpenAI SDK not available or OPENAI_API_KEY not set, skipping portrait")
        return None

    # 1. Load AoA data
    try:
        from db import storage
        aoa_data = storage.get_aoa_entry(entry_id)
        if not aoa_data:
            logger.error(f"AoA entry not found: {entry_id}")
            return None
    except Exception as e:
        logger.error(f"Failed to load AoA entry: {e}")
        return None

    # 2. Extract scene
    scene = extract_scene(aoa_data)
    if not scene:
        logger.error("Scene extraction failed, cannot generate portrait")
        return None

    # 3. Build detailed prompt (no length limit with gpt-image-1)
    prompt_text = build_image_prompt(scene)
    logger.info(f"Image prompt built ({len(prompt_text)} chars)")

    # 4. Generate image via OpenAI gpt-image-1.5
    try:
        client = openai.OpenAI()
        response = client.images.generate(
            model="gpt-image-1.5",
            prompt=prompt_text,
            size="1536x1024",
            quality="high",
            n=1,
        )
        b64_data = response.data[0].b64_json
        logger.info(f"gpt-image-1.5 image generated ({len(b64_data)} base64 chars)")
    except Exception as e:
        logger.error(f"OpenAI image generation failed: {e}")
        # Still save the prompt for debugging
        _update_aoa_portrait(entry_id, None, prompt_text)
        return None

    # 5. Save image and update DB
    serving_path = _save_image_b64(b64_data, entry_id)
    _update_aoa_portrait(entry_id, serving_path, prompt_text)

    return serving_path


def generate_image_from_prompt(prompt: str, model: str = "gpt-image-1.5",
                               quality: str = "medium", size: str = "1536x1024") -> Optional[str]:
    """
    Direct image generation from a raw prompt string — no Claude extraction stage.
    Used by the Image Lab tab for iterating on prompts manually.
    Saves image to data/portraits/lab_{id}.png and returns the serving path.
    """
    if not OPENAI_AVAILABLE:
        logger.warning("OpenAI SDK not available or OPENAI_API_KEY not set, skipping image generation")
        return None

    import uuid
    image_id = f"lab_{uuid.uuid4().hex[:12]}"

    try:
        client = openai.OpenAI()
        response = client.images.generate(
            model=model,
            prompt=prompt,
            size=size,
            quality=quality,
            n=1,
        )
        b64_data = response.data[0].b64_json
        logger.info(f"Image generated via {model} ({quality}, {size})")
    except Exception as e:
        logger.error(f"OpenAI image generation failed: {e}")
        return None

    return _save_image_b64(b64_data, image_id)


def generate_portrait_from_data(aoa_data: dict, image_id: str) -> Optional[str]:
    """
    Generate a portrait from provided data dict (no DB lookup).
    Used when there's no AoA entry but we still want a portrait.
    Saves image to static/portraits/ and returns the serving path.
    """
    if not OPENAI_AVAILABLE:
        logger.warning("OpenAI SDK not available or OPENAI_API_KEY not set, skipping portrait")
        return None

    scene = extract_scene(aoa_data)
    if not scene:
        logger.error("Scene extraction failed, cannot generate portrait")
        return None

    prompt_text = build_image_prompt(scene)
    logger.info(f"Image prompt built ({len(prompt_text)} chars)")

    try:
        client = openai.OpenAI()
        response = client.images.generate(
            model="gpt-image-1.5",
            prompt=prompt_text,
            size="1536x1024",
            quality="high",
            n=1,
        )
        b64_data = response.data[0].b64_json
        logger.info(f"gpt-image-1.5 image generated ({len(b64_data)} base64 chars)")
    except Exception as e:
        logger.error(f"OpenAI image generation failed: {e}")
        return None

    serving_path = _save_image_b64(b64_data, image_id)
    return serving_path
