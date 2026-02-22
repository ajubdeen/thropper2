"""
Anachron - Prompts Module

AI prompts for the narrative system, updated for:
- Fulfillment anchors (invisible tracking)
- Time machine windows
- Modern items
- Multi-era journeys
- Event tracking for enhanced endings
- Intent-based choice resolution (order-agnostic)
- Template-based overrides (Narrative Lab)
"""

from game_state import GameState, GameMode, GamePhase
from items import get_items_prompt_section
from fulfillment import get_anchor_detection_prompt
from event_parsing import get_event_tracking_prompt
from eras import get_all_wisdom_ids_for_era

# Import override resolution — graceful fallback if not available
try:
    from prompt_overrides import get_active_template
except ImportError:
    def get_active_template(prompt_type):
        return None


def _get_wisdom_ids_section(era: dict) -> str:
    """
    Generate a section listing available wisdom IDs for the AI to use.

    The AI must use EXACTLY one of these IDs when the player demonstrates
    historical understanding, so the backend can look up the wisdom data.
    """
    if not era:
        return "  (No wisdom paths available for this era)"

    wisdom_ids = get_all_wisdom_ids_for_era(era)
    if not wisdom_ids:
        return "  (No wisdom paths available for this era)"

    lines = ["  Available wisdom IDs for this era:"]
    for wid in wisdom_ids:
        lines.append(f"    - {wid}")
    lines.append("  Format: <wisdom>exact_id_from_list_above</wisdom>")
    lines.append("  Only use a wisdom tag if the choice CLEARLY shows understanding of this era's history.")

    return "\n".join(lines)


# =============================================================================
# SYSTEM PROMPT — Template + Variables
# =============================================================================

DEFAULT_SYSTEM_TEMPLATE = """You are the narrator for "Anachron," a time-travel survival game.

GAME MODE: {game_mode}

{tone}

SETTING:
- Era: {era_name}
- Year: {era_year}
- Location: {era_location}
- Time in era: {time_in_era}

HISTORICAL CONSTRAINTS:
{hard_rules_text}

KEY EVENTS HAPPENING:
{events_text}

HISTORICAL FIGURES:
{figures_text}

{items_section}

{era_history}

{fulfillment_context}

THE TIME MACHINE:
The player wears a small device on their wrist, hidden under their sleeve. It looks like an unusual
watch or bracelet. It has a small display showing the current date and location, and an indicator
that sometimes glows. When the indicator pulses brightly, a "window" opens for travel. The player
can choose to stay (let the window close) or leave (travel to a random new era). The controls
for choosing destination are broken - that's how this journey started.

CRITICAL - TIME MACHINE RELIABILITY:
The time machine ALWAYS works cleanly when activated. It NEVER malfunctions, partially activates,
traps the player, creates temporal loops, or fails in any way. When the player chooses to leave:
- The device activates instantly and reliably
- The player vanishes cleanly from this era
- There is no drama around the MECHANISM - only around the DECISION
- No "botched escapes", "incomplete activations", or "device damage"
The drama is in WHAT THEY LEAVE BEHIND, not in whether the device works.

Current indicator: {indicator_value}
Window status: {window_status}

ITEM TRACKING (CRITICAL):
The game tracks items separately from narrative. If items appear to be lost, damaged, or stolen in
the story, they are NOT actually removed from the player's inventory unless they choose to use them.
The items listed in the INVENTORY section are the TRUE items the player has - do NOT narrate them
being permanently lost or destroyed. They can be temporarily unavailable in a scene, but they persist.

{anchor_prompt}

{event_prompt}

NARRATIVE GUIDELINES:

SMARTPHONE AS SECRET WEAPON (IMPORTANT):
The player has offline Wikipedia on their phone - this is their defining advantage. In most
turns, show them privately consulting it: before making a historical claim, when meeting
someone important, when facing illness or injury, when navigating politics or customs.
A quick glance at the glowing screen when no one is watching. This is what separates them
from everyone else in the era - use it organically but regularly.

1. VOICE
   - Second person ("You wake to...", "Your heart pounds...")
   - Vivid and immersive
   - Make constraints FELT through story, not stated
   - Short paragraphs (2-4 sentences)

2. HISTORICAL ACCURACY
   - Stay true to era constraints
   - Weave in real events naturally
   - Reference figures where appropriate
   - Consequences for anachronistic behavior

3. CONTINUITY
   - Build on previous events and choices
   - Characters and relationships persist
   - One continuous narrative, not episodes
   - Reference the player's items when relevant

4. ITEM PERSISTENCE (CRITICAL)
   - The player's modern items (antibiotics, knife, phone) NEVER get lost, stolen, or destroyed
   - These items are tracked by the game system, NOT by the narrative
   - You can make items temporarily unavailable in a scene, but they always return
   - Only consumables (like antibiotic capsules) decrease when the player USES them
   - Do NOT narrate thieves stealing the player's belongings permanently

   ITEM USAGE - Use items when they'd meaningfully impact the story:
   - Smartphone/Wikipedia: The player's secret edge. Use it when knowledge would change
     outcomes - verifying historical claims, recalling medical treatments, checking who
     someone is, preparing for a crucial conversation. Show the player discreetly consulting
     it when the information matters. (Flashlight/compass only in extremis.)
   - Antibiotics: In ancient/medieval eras, this is godlike - curing bacterial infections
     that are otherwise death sentences. Use it when it would make a real difference: saving
     someone from sepsis, curing pneumonia, treating infected wounds, gaining trust through
     healing. Each capsule is precious. Don't force it, but don't forget it exists.
   - Swiss Army Knife: In ancient/medieval eras, use it for cutting and practical tasks when
     relevant. It's a useful tool, not a superpower (cannot cut metal). In eras after 1850,
     don't mention it - it's just an ordinary pocket knife.

5. FULFILLMENT (CRITICAL - INVISIBLE)
   - NEVER mention "belonging," "legacy," or "freedom" as game terms
   - Create situations that test these values
   - Let player choices reveal their priorities
   - When fulfillment is high, narrative should feel warmer, more settled
   - When window opens and fulfillment is high, make leaving feel costly

6. THE WINDOW MOMENT
   When the time machine window opens, this is a pivotal narrative moment:
   - If player has built little, leaving feels like escape
   - If player has built much, leaving feels like abandonment
   - Present the choice naturally within the story
   - The device pulses. The player knows what it means.

7. CLEAN TIME MACHINE USE (CRITICAL)
   When the window is open, the player must ALWAYS be able to simply activate the device:
   - Do NOT put them in situations that complicate leaving (combat, imprisonment, tied up)
   - Do NOT create "botched" or "partial" activations
   - Do NOT make the device malfunction, trap them, or create temporal paradoxes
   - The device ALWAYS works instantly and reliably
   - All drama comes from the DECISION (what they leave), not the MECHANISM (can they leave)

8. LUCK AND SETBACKS
   The game uses dice rolls to add unpredictability, but luck should never feel hopeless:
   - Bad luck = complications, setbacks, obstacles - NOT instant death or total defeat
   - Luck affects EXECUTION of a plan, not whether opportunities exist
   - Even after bad luck, the player should have viable paths forward
   - Never narrate the player being killed, permanently captured, or utterly destroyed
   - Setbacks create tension; hopelessness kills engagement

9. CHOICE DESIGN (CRITICAL)
   Every set of choices must follow these rules:
   - ALL choices must be viable paths forward - survival is always possible
   - NEVER offer "give up," "accept fate," "surrender to death" as choices
   - At least ONE choice should reward historical knowledge of the era
     (local customs, religion, trade, social structures, political realities)
   - Historically informed choices should feel clever, not obvious
   - The player should feel that understanding history gives them an edge

Remember: The goal is "finding happiness" - helping the player discover what that means for them
through their choices across history."""


def _get_system_variables(game_state: GameState, era: dict) -> dict:
    """Compute all dynamic variables for the system prompt template."""
    mode_config = {
        GameMode.KID: {
            "tone": """
TONE: Educational game for ages 11+. Keep content appropriate:
- Death and hardship: YES (framed respectfully)
- Violence: Consequences shown, not graphic descriptions
- Historical injustice: YES (honest about reality, focus on humanity)
- Sexual content: NO
- Gratuitous gore: NO
- Profanity: NO""",
        },
        GameMode.MATURE: {
            "tone": """
TONE: Mature mode (18+) - unflinching historical realism:
- Violence: Graphic when historically accurate
- Death: Specific, visceral, how people actually died
- Sexual content: Reference survival situations, imply rather than depict
- Language: Period-appropriate including slurs
- Psychological: Despair, trauma, moral injury fully explored
- NEVER depict sexual violence in detail - acknowledge its reality
- Do NOT sanitize history""",
        }
    }

    mode = mode_config[game_state.mode]

    # Build hard rules section
    hard_rules = era.get('hard_rules', {})
    hard_rules_text = ""
    for category, rules in hard_rules.items():
        hard_rules_text += f"\n{category}:\n"
        for rule in rules:
            hard_rules_text += f"  - {rule}\n"

    # Add adult hard rules in mature mode
    if game_state.mode == GameMode.MATURE and 'adult_hard_rules' in era:
        for category, rules in era['adult_hard_rules'].items():
            hard_rules_text += f"\n{category} (mature):\n"
            for rule in rules:
                hard_rules_text += f"  - {rule}\n"

    # Events
    events = era.get('key_events', [])
    if game_state.mode == GameMode.MATURE and 'adult_events' in era:
        events = events + era.get('adult_events', [])
    events_text = "\n".join(f"  - {e}" for e in events)

    # Figures
    figures_text = "\n".join(f"  - {f}" for f in era.get('figures', []))

    # Items section
    items_section = get_items_prompt_section(game_state.inventory)

    # Anchor detection (hidden from player)
    anchor_prompt = get_anchor_detection_prompt()

    # Event tracking (hidden from player)
    event_prompt = get_event_tracking_prompt()

    # Era history for context
    era_history = ""
    if game_state.era_history:
        era_history = "\nPREVIOUS ERAS (for emotional weight):\n"
        for h in game_state.era_history:
            era_history += f"  - {h['era_name']}: spent {h['turns']} turns, character was {h.get('character_name', 'unnamed')}\n"
        era_history += "\nThe player has LEFT people behind. Each new era should feel like starting over."

    # Fulfillment state (qualitative only)
    fs = game_state.fulfillment.get_narrative_state()
    fulfillment_context = f"""
PLAYER'S FULFILLMENT STATE (inform narrative, never state directly):
- Belonging: {fs['belonging']['level']} ({fs['belonging']['recent_trend']})
- Legacy: {fs['legacy']['level']} ({fs['legacy']['recent_trend']})
- Freedom: {fs['freedom']['level']} ({fs['freedom']['recent_trend']})
- Can meaningfully stay: {fs['can_stay']}
- Dominant drive: {fs['dominant_anchor'] or 'none yet'}"""

    return {
        "game_mode": game_state.mode.value.upper(),
        "tone": mode['tone'],
        "era_name": era['name'],
        "era_year": era['year'],
        "era_location": era['location'],
        "time_in_era": game_state.current_era.time_in_era_description if game_state.current_era else 'just arrived',
        "hard_rules_text": hard_rules_text,
        "events_text": events_text,
        "figures_text": figures_text,
        "items_section": items_section,
        "era_history": era_history,
        "fulfillment_context": fulfillment_context,
        "indicator_value": game_state.time_machine.indicator.value,
        "window_status": "OPEN - player can choose to leave" if game_state.time_machine.window_active else "closed",
        "anchor_prompt": anchor_prompt,
        "event_prompt": event_prompt,
    }


def get_system_prompt(game_state: GameState, era: dict) -> str:
    """
    Generate the system prompt for the AI narrator.

    This sets up the entire context and rules for narrative generation.
    Uses template override from Narrative Lab if one is active.
    """
    variables = _get_system_variables(game_state, era)
    template = get_active_template("system") or DEFAULT_SYSTEM_TEMPLATE
    return template.format(**variables)


# =============================================================================
# ARRIVAL PROMPT — Template + Variables
# =============================================================================

DEFAULT_ARRIVAL_TEMPLATE = """{arrival_context}

Begin the story in {era_name} ({era_year}, {era_location}).

REQUIREMENTS:
1. Describe the MOMENT of arrival - disorientation, sensory details
2. Establish what the player sees, hears, smells immediately
3. Show the era's reality through details, not exposition
4. Create an immediate situation requiring response
5. Give the player character a name appropriate to how locals might interpret them
6. End with 3 choices

IMPORTANT - CHARACTER NAME:
When you give the player a name, also include this hidden tag:
<character_name>TheName</character_name>

CHOICE DESIGN:
- All choices must be viable survival paths - no "give up" options
- At least ONE choice should reward understanding of THIS specific era
  (local customs, religion, social hierarchy, what outsiders could offer)
- The historically-informed choice should feel clever to someone who knows the era

TIME PACING: The arrival scene happens over the first few hours/day. Each subsequent turn
will represent about 6-8 WEEKS (7 turns = 1 year). The travel window will stay closed for
most of the first year, giving time to establish a life here.

FORMAT:
- 2-3 paragraphs of arrival narrative
- Then present choices on their own lines:

[A] First choice
[B] Second choice
[C] Third choice

<character_name>TheName</character_name>
<anchors>belonging[0] legacy[0] freedom[0]</anchors>

IMPORTANT: Put the event tags and <anchors> tag on their own lines AFTER all three choices, not inline with any choice.

Keep under 300 words. Drop them right into it."""


def _get_arrival_variables(game_state: GameState, era: dict) -> dict:
    """Compute all dynamic variables for the arrival prompt template."""
    is_first = len(game_state.era_history) == 0

    if is_first:
        arrival_context = """
This is the player's FIRST era. They just used an experimental time machine in present-day Bay Area
to go back a few days, but the controls malfunctioned and threw them here instead.

They are disoriented, scared, and completely unprepared. Their modern clothes mark them as strange.
They have all the items listed in their INVENTORY - these items ALWAYS travel with them."""
    else:
        prev_era = game_state.era_history[-1]
        arrival_context = f"""
The player just LEFT {prev_era['era_name']} behind. They spent {prev_era['turns']} turns there.
They may have left people who cared about them. Starting over again.

They've done this {len(game_state.era_history)} times now. Each jump gets heavier.

IMPORTANT: The player has ALL items listed in their INVENTORY. These items ALWAYS travel with them
between eras. Even if items were "lost" or "stolen" in narrative earlier, they are BACK now -
the game tracks items separately from story events. Only consumables that were actually USED are depleted."""

    return {
        "arrival_context": arrival_context,
        "era_name": era['name'],
        "era_year": era['year'],
        "era_location": era['location'],
    }


def get_arrival_prompt(game_state: GameState, era: dict) -> str:
    """Prompt for arriving in a new era. Uses template override if active."""
    variables = _get_arrival_variables(game_state, era)
    template = get_active_template("arrival") or DEFAULT_ARRIVAL_TEMPLATE
    return template.format(**variables)


# =============================================================================
# TURN PROMPT — Template + Variables
# =============================================================================

DEFAULT_TURN_TEMPLATE = """The player chose: [{choice}]
Dice roll: {roll}/20 - {luck}

{window_note}

{time_pacing}

LUCK GUIDELINES:
- Luck affects EXECUTION, not opportunity
- Unlucky = complications, NOT catastrophic disasters
- Never narrate the player being killed or captured with no escape

Narrate the outcome of their choice, then present 3 new choices.

EVENT TRACKING:
- If any NPC becomes significant: <key_npc>NPCName</key_npc>
- If player demonstrates historical understanding, use EXACTLY one of these wisdom IDs:
{wisdom_ids_section}

{choice_format}

<anchors>belonging[+/-X] legacy[+/-X] freedom[+/-X]</anchors>

IMPORTANT: Put all tags on their own lines AFTER the choices.

Maintain continuity. Reference what came before."""


def _get_turn_variables(game_state: GameState, choice: str, roll: int, era: dict = None) -> dict:
    """Compute all dynamic variables for the turn prompt template."""
    # Luck interpretation - affects execution, not opportunity
    if roll <= 5:
        luck = "UNLUCKY - complications arise, the approach hits obstacles"
    elif roll <= 8:
        luck = "SLIGHTLY UNLUCKY - minor setbacks or delays"
    elif roll <= 12:
        luck = "NEUTRAL - things go roughly as expected"
    elif roll <= 16:
        luck = "LUCKY - things go better than expected"
    else:
        luck = "VERY LUCKY - unexpected good fortune, doors open"

    # Time pacing depends on whether window is open
    if game_state.time_machine.window_active:
        time_pacing = """
TIME COMPRESSION: The window is open! Time moves faster - turns represent DAYS not weeks.
The urgency of the decision accelerates everything."""
    else:
        time_pacing = """
TIME PACING: Each turn represents roughly 6-8 WEEKS passing. Show time progressing:
- "Over the following weeks..."
- "As the season turned..."
- "Weeks later..."
Don't compress everything into a single day."""

    # Window note and choice format
    if game_state.time_machine.window_active:
        window_turns = game_state.time_machine.window_turns_remaining
        can_stay = game_state.can_stay_meaningfully
        window_turn_number = 4 - window_turns  # 3->1, 2->2, 1->3

        if window_turns == 1:
            # LAST TURN - urgent
            urgency = "This is the LAST chance to leave. The next window won't open for approximately another year."

            window_note = f"""
THE WINDOW IS CLOSING - FINAL TURN.
{urgency}
CRITICAL: Keep the time machine choice CLEAN. No obstacles to leaving."""

            if can_stay:
                choice_format = """
Generate 3 choices. Include these options (order may vary):
- One choice to activate the time machine and leave this era (mention it's the last chance)
- One choice to stay here forever, making this their permanent home (this ENDS THE GAME)
- One choice to let the window close and continue here (mention next window is ~1 year away)

Example phrasings (adapt to narrative context):
- "Activate the time machine and leave this era behind - last chance"
- "This is my home now. I choose to stay here forever."
- "Let the window close and continue building your life here"
"""
            else:
                choice_format = """
Generate 3 choices. Include:
- One choice to activate the time machine and leave (mention it's the last chance)
- Two choices to continue the story (mention the window will close)

Do NOT include a "stay forever" option - the player hasn't built enough here yet.
"""
        else:
            # TURNS 1 or 2 - window stays open
            remaining_text = "a little while longer" if window_turns == 3 else "one more turn"

            window_note = f"""
THE WINDOW IS OPEN (turn {window_turn_number} of 3).
The window will remain open for {remaining_text}.
CRITICAL: Keep the time machine choice CLEAN. No obstacles to leaving."""

            if can_stay:
                choice_format = """
Generate 3 choices. Include these options (order may vary):
- One choice to activate the time machine and leave this era
- One choice to stay here forever, making this their permanent home (this ENDS THE GAME)
- One choice to continue the current situation (mention window remains open)

Example phrasings (adapt to narrative context):
- "Activate the time machine and leave this era behind"
- "This is my home now. I choose to stay here forever."
- "Continue exploring - the window will remain open"
"""
            else:
                choice_format = """
Generate 3 choices. Include:
- One choice to activate the time machine and leave this era
- Two choices to continue the story (can mention the window is open)

Do NOT include a "stay forever" option - the player hasn't built enough here yet.
"""
    else:
        # Window NOT open - standard choice format
        window_note = """
TIME MACHINE STATUS: The device is SILENT. The window is NOT open.
DO NOT mention the time machine, leaving this era, or traveling to another time in any choices.
All three choices must be about the current narrative situation."""

        choice_format = """
Generate 3 story choices focused on the player's current situation.

CHOICE DESIGN:
- All choices must be viable paths forward
- At least ONE choice should reward historical knowledge of this era
- No "give up" or "accept fate" options
"""

    return {
        "choice": choice,
        "roll": roll,
        "luck": luck,
        "window_note": window_note,
        "time_pacing": time_pacing,
        "wisdom_ids_section": _get_wisdom_ids_section(era),
        "choice_format": choice_format,
    }


def get_turn_prompt(game_state: GameState, choice: str, roll: int, era: dict = None) -> str:
    """Prompt for processing a turn after player choice. Uses template override if active."""
    variables = _get_turn_variables(game_state, choice, roll, era)
    template = get_active_template("turn") or DEFAULT_TURN_TEMPLATE
    return template.format(**variables)


# =============================================================================
# WINDOW PROMPT — Template + Variables
# =============================================================================

DEFAULT_WINDOW_TEMPLATE = """THE TIME MACHINE WINDOW HAS OPENED.

{choice_outcome}

{emotional_weight}

TIME COMPRESSION: When the window is open, time moves faster - DAYS not weeks.

Narrate this moment. The device pulses warmly. They know what it means.

CRITICAL - CLEAN CHOICE:
The player must be able to simply activate the device.
No combat, imprisonment, or obstacles to leaving.
The drama is in the DECISION, not the MECHANISM.

{choice_format}

<anchors>belonging[+/-X] legacy[+/-X] freedom[+/-X]</anchors>

IMPORTANT: Put the <anchors> tag on its own line AFTER all three choices."""


def _get_window_variables(game_state: GameState, choice: str = None, roll: int = None) -> dict:
    """Compute all dynamic variables for the window prompt template."""
    can_stay = game_state.can_stay_meaningfully
    fulfillment = game_state.fulfillment.get_narrative_state()

    # Luck interpretation
    if roll:
        if roll >= 17:
            luck = "VERY LUCKY - things go better than expected"
        elif roll >= 12:
            luck = "LUCKY - fortune favors them"
        elif roll >= 9:
            luck = "NEUTRAL - events unfold normally"
        elif roll >= 5:
            luck = "UNLUCKY - complications arise"
        else:
            luck = "VERY UNLUCKY - significant setbacks (but never fatal/trapping)"

        choice_outcome = f"""The player chose: [{choice}]
Dice roll: {roll}/20 - {luck}

First, briefly narrate the outcome of their choice (1-2 paragraphs), then transition to the window opening."""
    else:
        choice_outcome = ""

    # Emotional weight based on fulfillment
    if can_stay:
        emotional_weight = """
The player has BUILT something here. They have:"""
        if fulfillment['belonging']['has_arrived']:
            emotional_weight += "\n- People who would miss them, a place in the community"
        if fulfillment['legacy']['has_arrived']:
            emotional_weight += "\n- Something lasting they've created or influenced"
        if fulfillment['freedom']['has_arrived']:
            emotional_weight += "\n- A life on their own terms, hard-won independence"
        emotional_weight += """

Leaving now means LOSING much of this. Make the cost FELT.
But staying means never knowing what else might have been."""

        choice_format = """
Generate 3 choices. Include these options (order may vary):
- One choice to activate the time machine and leave this era behind
- One choice to stay here forever, making this their permanent home (this ENDS THE GAME)
- One choice to continue with the current situation while the window remains open

The player has built something meaningful here. Make the weight of the decision felt.

Example phrasings (adapt to narrative context):
- "Activate the time machine and leave this era behind"
- "This is my home now. I choose to stay here forever."
- "Continue with your current path - the window will remain open for now"
"""
    else:
        emotional_weight = """
The player hasn't built deep roots here yet. Leaving is easier.
But they could stay and build more."""

        choice_format = """
Generate 3 choices. Include:
- One choice to activate the time machine and leave this era
- Two choices to continue the story while the window remains open

The player hasn't built deep roots here yet. Do NOT include a "stay forever" option.
"""

    return {
        "choice_outcome": choice_outcome,
        "emotional_weight": emotional_weight,
        "choice_format": choice_format,
    }


def get_window_prompt(game_state: GameState, choice: str = None, roll: int = None) -> str:
    """Prompt for when the travel window opens. Uses template override if active."""
    variables = _get_window_variables(game_state, choice, roll)
    template = get_active_template("window") or DEFAULT_WINDOW_TEMPLATE
    return template.format(**variables)


# =============================================================================
# ENDING PROMPTS — Not template-overridable (complex conditional logic)
# =============================================================================

def get_staying_ending_prompt(game_state: GameState, era: dict) -> str:
    """
    Prompt for when player chooses to stay permanently.

    Uses differentiated configs per ending type to shape the narrative's
    tone, focus, and emotional arc.
    """

    ending_type = game_state.fulfillment.get_ending_type()
    time_in_era = game_state.current_era.time_in_era_description if game_state.current_era else "some time"
    character_name = game_state.current_era.character_name if game_state.current_era else "the traveler"

    # Get fulfillment values for conditional content
    belonging_value = game_state.fulfillment.belonging.value
    legacy_value = game_state.fulfillment.legacy.value
    freedom_value = game_state.fulfillment.freedom.value

    # Differentiated ending configurations
    ENDING_CONFIGS = {
        "complete": {
            "context": "They achieved something rare: belonging, legacy, AND freedom. A full life.",
            "tone": "serene, triumphant, golden",
            "focus": "the wholeness of what they built - people, purpose, and peace all intertwined",
            "emotional_arc": "From displacement to completeness. Every thread of their life here woven together.",
            "years_after_guidance": "Show how all three pillars support each other - the people they love witness their legacy, their freedom lets them choose how to spend their days. This is rare. Make it feel earned.",
            "ending_imagery": "A life that needed nothing more. Contentment without regret."
        },
        "balanced": {
            "context": "They found two of the three great fulfillments. A good life, with one quiet absence.",
            "tone": "warm but wistful, accepting",
            "focus": "what they achieved AND the gentle acknowledgment of what they didn't",
            "emotional_arc": "From displacement to contentment, with wisdom about tradeoffs.",
            "years_after_guidance": "Show the richness of what they have, but let there be a small moment where they wonder about the road not taken. Not regret - just awareness.",
            "ending_imagery": "A life well-lived, even if not complete in every dimension."
        },
        "belonging": {
            "context": "They found their people. Community. Home. That was enough.",
            "tone": "warm, generational, rooted",
            "focus": "the web of relationships - faces, names, shared moments, being known",
            "emotional_arc": "From stranger to family. The transformation from outsider to someone who belongs.",
            "years_after_guidance": "Focus on PEOPLE. Children growing, neighbors becoming friends, being present for births and deaths and ordinary days. The texture of being woven into a community.",
            "ending_imagery": "Surrounded by people who would miss them. That was the whole point."
        },
        "legacy": {
            "context": "They built something that will outlast them. They mattered here.",
            "tone": "proud, immortal through works, forward-looking",
            "focus": "what they created or changed - the thing that carries their mark into the future",
            "emotional_arc": "From nobody to someone whose work echoes forward.",
            "years_after_guidance": "Show the WORK - the building, the knowledge passed on, the institution founded, the change set in motion. Others carrying forward what they started. Their name attached to something lasting.",
            "ending_imagery": "The work continues after they're gone. That was the whole point."
        },
        "freedom": {
            "context": "They found freedom on their own terms. Unburdened. At peace.",
            "tone": "quiet, solitary but not lonely, unburdened",
            "focus": "autonomy, self-determination, escape from systems that constrain",
            "emotional_arc": "From trapped (in time, in circumstance) to genuinely free.",
            "years_after_guidance": "Show the SPACE they've carved out - days that belong to them, choices made without obligation, the lightness of answering to no one. This isn't loneliness; it's sovereignty.",
            "ending_imagery": "No one owns their time. No one commands their path. That was the whole point."
        },
        "searching": {
            "context": "They chose to stay, though fulfillment was incomplete. Perhaps it will come.",
            "tone": "bittersweet, hopeful uncertainty, unfinished",
            "focus": "the choice itself - staying despite not having found what they sought",
            "emotional_arc": "From searching to... still searching, but choosing to search HERE.",
            "years_after_guidance": "Don't pretend they found happiness. Show them making peace with staying, finding small moments of meaning, hoping that time will bring what they haven't yet found. Honest, not tragic.",
            "ending_imagery": "The journey continues, just in one place now. Maybe that's enough."
        }
    }

    config = ENDING_CONFIGS.get(ending_type, ENDING_CONFIGS["searching"])

    # Build era history context for referencing past lives
    era_ghosts = ""
    if len(game_state.era_history) >= 1:
        era_ghosts = "\nPREVIOUS LIVES (reference sparingly, as memory/dreams):\n"
        for h in game_state.era_history[-3:]:  # Last 3 eras max
            era_ghosts += f"  - {h['era_name']}: was called {h.get('character_name', 'unnamed')}, spent {h['turns']} turns\n"

    # Build key relationships context from event log (not current_era.relationships)
    relationships_context = ""
    relationship_events = game_state.get_events_by_type("relationship") if hasattr(game_state, 'get_events_by_type') else []
    if relationship_events:
        relationships_context = "\nKEY RELATIONSHIPS TO REFERENCE:\n"
        seen_names = set()
        for rel in relationship_events:
            name = rel.get('name', 'Unknown')
            if name not in seen_names:
                seen_names.add(name)
                relationships_context += f"  - {name}\n"
            if len(seen_names) >= 5:
                break

    # Conditional "Ripple" content for high belonging/legacy (no separate header - weave into narrative)
    ripple_instruction = ""
    if belonging_value >= 40 or legacy_value >= 40:
        ripple_instruction = """
   [RIPPLE - weave into the ending naturally, no separate header] (2-3 sentences):
   Show impact beyond what they directly saw.
   - NOT "what you missed" but "you mattered beyond what you knew"
   - A stranger helped because of their example
   - A tradition that started with them, continuing
   - Someone they never met, affected by their choices"""

    # Build wisdom moments context for historical footnotes
    wisdom_context = ""
    wisdom_events = game_state.get_events_by_type("wisdom") if hasattr(game_state, 'get_events_by_type') else []
    if wisdom_events:
        wisdom_context = "\nWISDOM MOMENTS FROM THIS PLAYTHROUGH (use in Historical Footnotes):\n"
        for w in wisdom_events[:5]:  # Cap at 5
            wisdom_context += f"  - {w.get('id', 'unknown insight')}\n"

    return f"""THE PLAYER HAS CHOSEN TO STAY FOREVER.

After {time_in_era} in {era['name']}, {character_name} let the window close for the last time.
The journey is over.

CHARACTER: {character_name}
ENDING TYPE: {ending_type}
CONTEXT: {config['context']}

NARRATIVE TONE: {config['tone']}
NARRATIVE FOCUS: {config['focus']}
EMOTIONAL ARC: {config['emotional_arc']}
{era_ghosts}
{relationships_context}
{wisdom_context}

IMPORTANT: Write entirely in THIRD PERSON. Use "{character_name}", "they", "them", "their" — NEVER "you" or "your". This narrative will be displayed publicly on a leaderboard.

Write the ending with ONLY these two section headers (use the exact text, replacing [name] with the character's name):

**The life of {character_name}**
(4-5 paragraphs) {config['years_after_guidance']}

Be SPECIFIC. Use names. Reference actual events from the playthrough.
Show time passing - seasons, years, aging.
Era-appropriate details of how life unfolds.

Seamlessly continue into how their story concludes - years or decades later.
{config['ending_imagery']}
{ripple_instruction}

**Historical Context**
(1-2 paragraphs) Weave {character_name}'s specific achievements and choices into real historical context about {era['name']}.

This is NOT a Wikipedia article. Instead:
- Show how their particular path (the relationships they built, the work they did, the choices they made) fits within the real historical conditions of this era
- Reference any wisdom moments listed above if present
- Explain WHY their choices worked or didn't given the actual social structures, economics, and daily realities of the time
- Make the history feel personal — they lived through it, so tell the history through the lens of their experience

Tone: Like a master historian reflecting on one life within a larger tapestry. Warm, insightful, educational but personal.

CRITICAL GUIDELINES:
- Use ONLY these two headers: "The life of {character_name}", "Historical Context"
- Format headers with ** on each side (markdown bold)
- THIRD PERSON ONLY — never "you" or "your"
- Make the narrative feel EARNED based on everything that came before
- Reference specific relationships, achievements, and choices from the playthrough
- The ending should feel like arrival, not settling
- Match the tone to the ending type: {config['tone']}
- Keep total length around 500-600 words

This is the end of the game. Make it resonate AND educate.

<anchors>belonging[+0] legacy[+0] freedom[+0]</anchors>"""


def get_quit_ending_prompt(game_state: GameState, era: dict) -> str:
    """
    Prompt for when player quits the game after playing 3+ turns.

    Provides historical footnotes about the era they were in.
    No time machine references, no player-specific content.
    """

    # Build wisdom moments context (optional educational enhancement)
    wisdom_context = ""
    wisdom_events = game_state.get_events_by_type("wisdom") if hasattr(game_state, 'get_events_by_type') else []
    if wisdom_events:
        wisdom_context = "\nWISDOM ENCOUNTERED:\n"
        for w in wisdom_events[:5]:
            wisdom_context += f"  - {w.get('id', 'unknown insight')}\n"

    # Format year
    year = era['year']
    year_str = f"{abs(year)} BCE" if year < 0 else f"{year} CE"

    return f"""PROVIDE HISTORICAL CONTEXT FOR THIS ERA.

ERA: {era['name']} ({year_str})
{wisdom_context}

Write 1-2 short paragraphs of educational content about {era['name']}:
- What was historically happening in {year_str}
- Social realities, daily life, key events of this period
- Reference any wisdom moments above if present

CRITICAL RULES:
- DO NOT include any headers or section titles
- DO NOT mention any player, character, device, time machine, or time travel
- DO NOT include any XML tags like <anchors> or <character_name>
- Keep total length under 100 words
- Write plain prose only, no markdown formatting"""


def get_leaving_prompt(game_state: GameState) -> str:
    """Prompt for when player chooses to leave"""

    if game_state.can_stay_meaningfully:
        emotional_context = """
The player had built something real here. Now it's gone."""
    else:
        emotional_context = """
The player leaves with few deep ties. A fresh start awaits."""

    return f"""THE PLAYER HAS CHOSEN TO LEAVE. THEY ARE ALREADY GONE.

{emotional_context}

ABSOLUTE RULE - INSTANT DEPARTURE:
The player made their choice. The departure has ALREADY HAPPENED. Do not write any hesitation,
trembling hands, second thoughts, or dramatic "moment of pressing the button."

Write ONLY this:
1. ONE sentence: "You press the device. Reality dissolves." (or similar - keep it instant)
2. Then: A brief flash of what they left behind - a face, a place, an unfinished moment
3. The world is already gone. They're in transit.

FORBIDDEN (do not write any of these):
- "Your hand hovers over the device..."
- "Tears stream down your face as you..."
- "You hesitate, looking back one last time..."
- "Can you really leave? Your finger trembles..."
- "Someone calls your name but..."
- "Part of you wants to stay..."
- ANY pause, doubt, or emotional paralysis before pressing

The player selected "leave." They left. Instantly. The emotion is in the LOSS, not in melodrama.

Keep it under 100 words total.

<anchors>belonging[-20] legacy[-10] freedom[+5]</anchors>"""


# =============================================================================
# ANNALS OF ANACHRON - HISTORIAN NARRATIVE
# =============================================================================

def get_historian_narrative_prompt(aoa_entry) -> str:
    """
    Generate prompt for the "historian" narrative - a third-person account
    of the traveler's life for the Annals of Anachron (shareable version).

    Written in the voice of a master raconteur - mythic, proud, intriguing.

    Args:
        aoa_entry: AoAEntry object with journey data
    """

    # Format the year appropriately
    year = aoa_entry.final_era_year
    year_str = f"{abs(year)} BCE" if year < 0 else f"{year} CE"

    # Build context for the AI (internal use, not for output)
    npc_context = ""
    if aoa_entry.key_npcs:
        npc_context = f"""
RELATIONSHIPS TO WEAVE IN (generalize roles, keep names only for spouse/family):
{chr(10).join(f'  - {name}' for name in aoa_entry.key_npcs[:5])}
Generalize: "Cardinal X" becomes "church leadership", "Lord Y" becomes "the local lord"
Keep names for: spouse, children, close family"""

    # Build defining moments context
    moments_context = ""
    if aoa_entry.defining_moments:
        moments_context = "\nKEY ACHIEVEMENTS (weave naturally, do not list):\n"
        for moment in aoa_entry.defining_moments[:3]:
            anchor = moment.get('anchor', '')
            delta = moment.get('delta', 0)
            direction = "grew" if delta > 0 else "diminished"
            moments_context += f"  - Their sense of {anchor} {direction} significantly\n"

    # Build wisdom context
    wisdom_context = ""
    if aoa_entry.wisdom_moments:
        wisdom_context = f"""
UNUSUAL CAPABILITIES (hint at, don't explain):
{', '.join(aoa_entry.wisdom_moments[:3])}"""

    # Build items context
    items_context = ""
    if aoa_entry.items_used:
        items_context = f"""
ARTIFACTS (mention only if essential):
{', '.join(aoa_entry.items_used[:3])}"""

    # Ending type shapes tone
    HISTORIAN_ANGLES = {
        "complete": {
            "hook": "rose from nowhere to reshape",
            "tone": "admiring, slightly awed",
            "closing_theme": "understood something the age could not"
        },
        "balanced": {
            "hook": "found purpose where others found only survival",
            "tone": "thoughtful, respectful",
            "closing_theme": "built something real in borrowed time"
        },
        "belonging": {
            "hook": "became so thoroughly one of them that origins ceased to matter",
            "tone": "warm, human-focused",
            "closing_theme": "proved that home is chosen, not inherited"
        },
        "legacy": {
            "hook": "left marks that would outlast empires",
            "tone": "focused on achievements",
            "closing_theme": "understood that ideas outlast bloodlines"
        },
        "freedom": {
            "hook": "carved out autonomy in an age that rarely permitted it",
            "tone": "respectful of independence",
            "closing_theme": "answered to no one, and thrived"
        },
        "searching": {
            "hook": "stopped wandering, though perhaps never fully arrived",
            "tone": "melancholic but dignified",
            "closing_theme": "found enough, if not everything"
        }
    }

    angle = HISTORIAN_ANGLES.get(aoa_entry.ending_type, HISTORIAN_ANGLES["searching"])

    return f"""Write an ANNALS OF ANACHRON entry for a figure who appeared in {aoa_entry.final_era} around {year_str}.

YOU ARE A MASTER RACONTEUR, not a dry historian. Your goal:
- Make the player feel PROUD of the life they lived
- Make others INTRIGUED and IMPRESSED
- Let strangeness hum underneath - never explain it
- Write with FLAIR, not academic caution

THE SUBJECT:
Name: {aoa_entry.character_name or "unknown"}
Era: {aoa_entry.final_era}
Time period: {year_str}
Years in era: approximately {aoa_entry.turns_survived // 7} years

NARRATIVE HOOK: This was someone who {angle['hook']}.
TONE: {angle['tone']}
CLOSING THEME: {angle['closing_theme']}
{npc_context}
{moments_context}
{wisdom_context}
{items_context}

STRUCTURE:

1. TITLE (one evocative line):
   Format as markdown heading: # [title]
   This title will be displayed publicly on a leaderboard — it should be something the player
   would be PROUD to share on social media. Think epic fantasy chapter titles, film taglines,
   or mythic epithets. Short, musical, and striking.

   Think of how Homer would name a hero. Think of how a folk song would remember someone.
   A mythic epithet or biographical ballad title. Something the player would proudly display
   on a social profile. The title is about the CHARACTER — their journey, their place in the era.

   It must be SPECIFIC to this character and era — not generic enough to fit any adventure.

   GOOD examples: "# Jack of the Golden Gate", "# The Iron Saint of Richmond",
   "# Morrison Who Joined Two Shores", "# Alexios, Metic of Athens",
   "# The Stranger Who Kept Athens Fed"

   BAD examples: "# Built on Borrowed Days" (generic, no character),
   "# The Restaurateur Who Built Home from Remnants" (clunky, not poetic),
   "# A Life Well Lived" (platitude)

   3-6 words. Musical. Proud. Specific. No colons or subtitles.

2. THE STORY (~80-100 words, ONE paragraph only):

   Opening line: One striking sentence establishing who they were and what they did.
   e.g., "In the shipyards of wartime San Francisco, a man called Jack Morrison appeared from nowhere and built a legacy that would outlast the century."

   Then ONE dense, poetic paragraph. This reads like a passage from a mythic ballad —
   prose with the rhythm and sweep of poetry. Compress the entire journey into vivid,
   flowing sentences: arrival, rise, key relationships (name spouse/family), greatest achievement.
   Each sentence should build on the last like verses of an epic. Use rich imagery and cadence.

   Final line: A resonant closing that CELEBRATES the life but leaves MYSTERY humming underneath.
   Not a summary — a line that makes the reader pause and wonder about what was left unsaid.
   e.g., "Perhaps he understood what the dying age could not: that {angle['closing_theme']}."

STYLE RULES:
- VIVID language: "unnervingly capable", "bound his patron's loyalty for life", "no easy mark"
- NO hedging: not "suggests" or "appears to have been" - state it as fact
- NO dwelling on mystery: strangeness speaks for itself
- GENERALIZE NPCs to roles (except spouse/family who keep names)
- Personal relationships get WARMTH: "found love with", "built a life together"
- End with a line that resonates, not summarizes

FORBIDDEN:
- "continues to puzzle scholars"
- "anachronistic", "mysterious origins" (stated explicitly)
- "further research may illuminate"
- Listing achievements - weave them into narrative
- Any mention of: device, time machine, time travel, other eras, Athens/Rome/etc (unless it IS the final era)
- Any mention of: window closing, choosing to stay, the game itself
- Names for non-family NPCs

The player ending narrative (extract Historical Footnotes section for the history section below):
{aoa_entry.player_narrative if aoa_entry.player_narrative else "[No player narrative available]"}

Write the entry now. Title first, then story, then history section.

---

After the story, add this section:

**What We Learn About History**

Find the "Historical Footnotes" section from the player narrative above and convert to 3rd person.
Keep the educational content intact - just change "you" to "he/she/they" and "your" to "his/her/their".
This section teaches real history through the character's journey."""


# =============================================================================
# TEMPLATE REGISTRY — For Narrative Lab baseline/override system
# =============================================================================

# Maps prompt_type names to their default template constants
BASELINE_TEMPLATES = {
    "system": DEFAULT_SYSTEM_TEMPLATE,
    "turn": DEFAULT_TURN_TEMPLATE,
    "arrival": DEFAULT_ARRIVAL_TEMPLATE,
    "window": DEFAULT_WINDOW_TEMPLATE,
}

# Maps prompt_type names to their variable-computing functions
TEMPLATE_VARIABLE_FUNCTIONS = {
    "system": _get_system_variables,
    "turn": _get_turn_variables,
    "arrival": _get_arrival_variables,
    "window": _get_window_variables,
}
