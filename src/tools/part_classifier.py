import logging

logger = logging.getLogger(__name__)

def classify_part(part_name: str) -> str:
    """
    Classifies a garage estimate line item into a standard IMT category.
    Uses deterministic keyword matching for 100% reliability.
    """
    name_lower = part_name.lower()

        return "MECHANICAL_EXCLUSION"
    # 1. Mechanical / Consequential Exclusions (Highest Priority)
    if any(kw in name_lower for kw in ["engine", "engine sump", "consequential", "wear and tear", "rust", "mechanical breakdown"]):
        return "MECHANICAL_EXCLUSION"
        
    # 2. Consumables
    if any(kw in name_lower for kw in ["nut", "bolt", "screw", "washer", "clip", "grease", "lubricant", "oil", "filter", "coolant", "brake fluid", "bearing", "distilled water", "consumable"]):
        return "CONSUMABLE"
        
    # 3. Labour & Painting
    if any(kw in name_lower for kw in ["labour", "labor", "fitting", "installation", "removal", "paint", "painting", "denting", "polishing", "buffing"]):
        return "LABOUR_PAINTING"
        
    # 4. Plastic / Rubber / Nylon
    if any(kw in name_lower for kw in ["plastic", "rubber", "nylon", "tyre", "tire", "tube", "bumper", "trim", "moulding", "dashboard", "handle", "cover", "hose", "seal", "gasket", "battery", "air bag"]):
        return "PLASTIC_RUBBER"
        
    # 5. Glass
    if any(kw in name_lower for kw in ["glass", "windshield", "windscreen", "window", "mirror", "lamp", "headlamp", "taillamp", "light assembly"]):
        return "GLASS"
        
    # 6. Metal (Default for structural body parts like fenders, doors, bonnets)
    return "METAL"