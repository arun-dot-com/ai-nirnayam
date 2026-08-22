import logging

logger = logging.getLogger(__name__)

def calculate_painting_costs(total_claimed_painting_inr: float, has_zero_dep: bool, vehicle_age_years: float) -> dict:
    """
    Calculates approved material and labour costs for painting based on IMT rules.
    
    Rule (from Bundled Policy): "In case of a consolidated bill for painting charges, 
    the material component shall be considered as 25% of total painting charges for 
    the purpose of applying the depreciation. The depreciation rate of 50% shall be 
    applied only on the material cost."
    """
    material_cost = total_claimed_painting_inr * 0.25
    labour_cost = total_claimed_painting_inr * 0.75
    
    # Depreciation applies ONLY to the material component
    if has_zero_dep:
        material_depreciation_pct = 0.0
    else:
        material_depreciation_pct = 50.0  # Flat 50% on painting material as per IMT
        
    material_depreciation_inr = material_cost * (material_depreciation_pct / 100.0)
    net_material_cost = material_cost - material_depreciation_inr
    
    return {
        "total_claimed_inr": round(total_claimed_painting_inr, 2),
        "material_cost_inr": round(material_cost, 2),
        "labour_cost_inr": round(labour_cost, 2),
        "material_depreciation_percentage": material_depreciation_pct,
        "material_depreciation_inr": round(material_depreciation_inr, 2),
        "net_approved_painting_inr": round(net_material_cost + labour_cost, 2)
    }