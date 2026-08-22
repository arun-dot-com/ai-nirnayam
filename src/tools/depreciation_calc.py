import logging

logger = logging.getLogger(__name__)

def get_depreciation_percentage(category: str, vehicle_age_years: float, has_zero_dep: bool, part_name: str = "") -> float:
    """
    Calculates the depreciation percentage based on IMT rules and vehicle age.
    """
    if category == "MECHANICAL_EXCLUSION":
        return 100.0  # 100% depreciation = 0% approved
    if category == "CONSUMABLE":
        return 0.0    # Binary coverage check, not depreciation
    if category == "LABOUR_PAINTING":
        return 0.0    # Painting material depreciation is handled in labour_rates tool
        
    # Zero Depreciation Exception: Tyres and tubes still attract 50% depreciation even with Zero Dep (per PCEC-1)
    if has_zero_dep:
        if "tyre" in part_name.lower() or "tire" in part_name.lower() or "tube" in part_name.lower():
            return 50.0
        return 0.0
        
    # Standard IMT Depreciation Slabs
    if category == "PLASTIC_RUBBER":
        return 50.0
    elif category == "GLASS":
        return 0.0
        
    # Metal Age-wise Slabs (IMT Standard)
    if vehicle_age_years <= 0.5:
        return 0.0
    elif vehicle_age_years <= 1.0:
        return 5.0
    elif vehicle_age_years <= 2.0:
        return 10.0
    elif vehicle_age_years <= 3.0:
        return 15.0
    elif vehicle_age_years <= 4.0:
        return 25.0
    elif vehicle_age_years <= 5.0:
        return 35.0
    elif vehicle_age_years <= 10.0:
        return 45.0
    else:
        return 50.0