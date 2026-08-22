import pytest
from src.tools.part_classifier import classify_part
from src.tools.depreciation_calc import get_depreciation_percentage
from src.tools.labour_rates import calculate_painting_costs

def test_part_classifier():
    """Test deterministic classification of garage estimate items."""
    assert classify_part("Front Bumper") == "PLASTIC_RUBBER"
    assert classify_part("Left Headlamp Assembly") == "GLASS"
    assert classify_part("Front Left Fender") == "METAL"
    assert classify_part("Engine Sump Replacement") == "MECHANICAL_EXCLUSION"
    assert classify_part("Nut, Bolt, and Washer") == "CONSUMABLE"
    assert classify_part("Denting and Painting Labour") == "LABOUR_PAINTING"

def test_depreciation_calc_standard():
    """Test standard IMT depreciation slabs."""
    # Metal, 3.5 years old, no zero dep -> 25%
    assert get_depreciation_percentage("METAL", 3.5, False) == 25.0
    # Plastic, any age, no zero dep -> 50%
    assert get_depreciation_percentage("PLASTIC_RUBBER", 1.0, False) == 50.0
    # Glass, any age -> 0%
    assert get_depreciation_percentage("GLASS", 5.0, False) == 0.0
    # Mechanical exclusion -> 100%
    assert get_depreciation_percentage("MECHANICAL_EXCLUSION", 2.0, False) == 100.0

def test_depreciation_calc_zero_dep():
    """Test Zero Depreciation exceptions."""
    # Metal, 3.5 years old, WITH zero dep -> 0%
    assert get_depreciation_percentage("METAL", 3.5, True) == 0.0
    # Tyre with zero dep -> 50% (explicit exception per PCEC-1)
    assert get_depreciation_percentage("PLASTIC_RUBBER", 2.0, True, part_name="New Tyre") == 50.0

def test_labour_rates():
    """Test IMT painting cost split and depreciation logic."""
    # Total painting claimed: 4000, no zero dep
    result = calculate_painting_costs(4000.0, has_zero_dep=False, vehicle_age_years=3.0)
    assert result["material_cost_inr"] == 1000.0  # 25%
    assert result["labour_cost_inr"] == 3000.0    # 75%
    assert result["material_depreciation_percentage"] == 50.0
    assert result["material_depreciation_inr"] == 500.0
    assert result["net_approved_painting_inr"] == 3500.0  # 3000 + (1000 - 500)
    
    # With zero dep, depreciation on material should be waived
    result_zd = calculate_painting_costs(4000.0, has_zero_dep=True, vehicle_age_years=3.0)
    assert result_zd["material_depreciation_percentage"] == 0.0
    assert result_zd["net_approved_painting_inr"] == 4000.0