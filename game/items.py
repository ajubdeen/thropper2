"""
Anachron - Items Module

Manages the player's items:
- Fixed starting items (modern tech from the future)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from copy import deepcopy
import re

from config import STARTING_ITEMS


@dataclass
class Item:
    """A single item in the player's inventory"""
    
    id: str
    name: str
    description: str
    uses: Optional[int]  # None = unlimited
    max_uses: Optional[int]  # Original use count
    utility: str
    risk: str
    hooks: List[str]
    
    # Additional properties
    features: List[str] = field(default_factory=list)  # For complex items like phone
    
    # State
    is_depleted: bool = False
    is_revealed: bool = False  # Has this been shown to people in current era?
    times_used: int = 0
    
    @property
    def uses_remaining(self) -> Optional[int]:
        """How many uses left, or None if unlimited"""
        if self.uses is None:
            return None
        return max(0, self.uses)
    
    @property
    def is_consumable(self) -> bool:
        """Does this item have limited uses?"""
        return self.max_uses is not None
    
    @property
    def is_modern(self) -> bool:
        """Is this a modern item from the future?"""
        return True  # All items are modern now
    
    def use(self, count: int = 1) -> bool:
        """Use the item. Returns True if successful."""
        if self.is_depleted:
            return False
        
        self.times_used += count
        
        if self.uses is not None:
            self.uses = max(0, self.uses - count)
            if self.uses == 0:
                self.is_depleted = True
        
        return True
    
    def reveal(self):
        """Mark item as revealed to people in this era"""
        self.is_revealed = True
    
    def reset_for_new_era(self):
        """Reset era-specific state (revealed status)"""
        self.is_revealed = False
    
    def to_narrative_dict(self) -> dict:
        """Info for AI narrator"""
        return {
            "name": self.name,
            "description": self.description,
            "utility": self.utility,
            "risk": self.risk,
            "hooks": self.hooks,
            "features": self.features,
            "uses_remaining": self.uses_remaining,
            "is_depleted": self.is_depleted,
            "is_revealed": self.is_revealed,
            "is_modern": self.is_modern,
            "times_used": self.times_used
        }


@dataclass
class Inventory:
    """Player's inventory - just the three modern items"""
    
    modern_items: List[Item] = field(default_factory=list)
    
    @classmethod
    def create_starting(cls) -> "Inventory":
        """Create inventory with fixed starting items"""
        modern_items = []
        
        for item_data in STARTING_ITEMS:
            item = Item(
                id=item_data["id"],
                name=item_data["name"],
                description=item_data["description"],
                uses=item_data.get("uses"),
                max_uses=item_data.get("uses"),
                utility=item_data["utility"],
                risk=item_data["risk"],
                hooks=item_data.get("hooks", []),
                features=item_data.get("features", []),
            )
            modern_items.append(item)
        
        return cls(modern_items=modern_items)
    
    @property
    def all_items(self) -> List[Item]:
        """All items"""
        return self.modern_items
    
    @property
    def available_items(self) -> List[Item]:
        """Items that aren't depleted"""
        return [i for i in self.all_items if not i.is_depleted]
    
    def get_item(self, item_id: str) -> Optional[Item]:
        """Get item by ID"""
        for item in self.all_items:
            if item.id == item_id:
                return item
        return None
    
    def use_item(self, item_id: str, count: int = 1) -> bool:
        """Use an item by ID. Returns True if successful."""
        item = self.get_item(item_id)
        if item:
            return item.use(count)
        return False
    
    def reset_for_new_era(self):
        """Reset era-specific state for all items"""
        for item in self.all_items:
            item.reset_for_new_era()
    
    def display_items(self) -> str:
        """Format items for display to player"""
        lines = []
        
        for item in self.modern_items:
            if item.is_depleted:
                lines.append(f"  - {item.name}: [DEPLETED]")
            else:
                uses_str = f" ({item.uses} uses left)" if item.uses is not None else ""
                lines.append(f"  - {item.name}{uses_str}")
                lines.append(f"    {item.description}")
        
        return "\n".join(lines)
    
    def to_narrative_dict(self) -> Dict:
        """Get all items as narrative dicts for AI context"""
        return {
            "modern_items": [item.to_narrative_dict() for item in self.modern_items],
            "available_count": len(self.available_items),
            "depleted_count": len([i for i in self.modern_items if i.is_depleted])
        }


def get_items_prompt_section(inventory: Inventory) -> str:
    """Generate the items section for AI system prompt."""
    lines = ["PLAYER'S INVENTORY:"]
    lines.append("")
    lines.append("*** CRITICAL: Items listed here are what the player ACTUALLY has. ***")
    lines.append("*** Do NOT narrate these items being lost, stolen, destroyed, or taken away. ***")
    lines.append("*** They persist across the entire game unless the player USES a consumable. ***")
    lines.append("")
    
    # Modern items
    lines.append("MODERN ITEMS (from the future):")
    for item in inventory.modern_items:
        if item.is_depleted:
            lines.append(f"  - {item.name}: DEPLETED")
        else:
            uses_str = f" ({item.uses} uses left)" if item.uses is not None else ""
            revealed_str = " - REVEALED in this era" if item.is_revealed else ""
            lines.append(f"  - {item.name}{uses_str}{revealed_str}")
            lines.append(f"    {item.description}")
            lines.append(f"    Utility: {item.utility}")
            lines.append(f"    Risk: {item.risk}")
            if item.features:
                lines.append(f"    Features: {', '.join(item.features)}")
        lines.append("")
    
    return "\n".join(lines)


def parse_item_usage(response: str, inventory: Inventory) -> List[str]:
    """
    Parse AI response to detect item usage.
    Returns list of item IDs that were used.
    """
    used_items = []
    response_lower = response.lower()
    
    use_indicators = [
        "use", "used", "using", "uses",
        "take out", "took out", "pulls out", "pull out",
        "show", "showed", "showing", "shows",
        "give", "gave", "giving", "gives",
        "consult", "consulted", "check", "checked",
        "swallow", "take", "took", "administer",
        "cut", "cutting", "cuts",
        "light", "lit", "shine", "shining",
    ]
    
    for item in inventory.all_items:
        if item.is_depleted:
            continue
            
        item_name_lower = item.name.lower()
        # Check for partial matches too (e.g., "phone" matches "Smartphone")
        name_parts = item_name_lower.split()
        
        for name_part in name_parts:
            if len(name_part) < 4:  # Skip short words
                continue
            if name_part in response_lower:
                for indicator in use_indicators:
                    pattern = rf'{indicator}.{{0,50}}{re.escape(name_part)}|{re.escape(name_part)}.{{0,50}}{indicator}'
                    if re.search(pattern, response_lower):
                        used_items.append(item.id)
                        break
    
    return list(set(used_items))
