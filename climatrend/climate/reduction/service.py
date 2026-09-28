"""
Greenhouse-Gas Emission Reduction Recommendations Service.
Provides a comprehensive catalog of decarbonization actions across Energy,
Transport, Buildings, Food, and Nature-Based Solutions.
Computes ROI, abatement cost ($/tonne CO2e), and payback periods.
"""

from dataclasses import asdict, dataclass
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DecarbonizationAction:
    id: str
    title: str
    category: str  # Energy, Transport, Buildings, Food, Nature
    co2e_reduction_kg_yr: float  # Annual kg CO2e saved
    capital_cost_usd: float  # Upfront cost in USD
    annual_savings_usd: float  # Annual operational energy/fuel/cost savings
    payback_years: float  # Calculated payback period
    effort_score: int  # 1 (Easy/Fast) to 5 (Major civil works / complex)
    description: str
    co_benefits: List[str]


# Standard Decarbonization Actions grounded in Project Drawdown and IEA Net Zero guidelines
DEFAULT_ACTIONS: List[DecarbonizationAction] = [
    DecarbonizationAction(
        id="solar_pv_5kw",
        title="Rooftop Solar PV (5 kW Grid-Tied)",
        category="Energy",
        co2e_reduction_kg_yr=5200.0,
        capital_cost_usd=6500.0,
        annual_savings_usd=1100.0,
        payback_years=5.9,
        effort_score=3,
        description="Install high-efficiency monocrystalline solar panels with net-metering inverter.",
        co_benefits=["Energy Independence", "Hedge against utility inflation", "Increases property value"],
    ),
    DecarbonizationAction(
        id="ev_transition",
        title="Electric Vehicle (EV) Transition",
        category="Transport",
        co2e_reduction_kg_yr=3800.0,
        capital_cost_usd=12000.0,  # Premium over ICE or lease differential
        annual_savings_usd=1650.0,
        payback_years=7.3,
        effort_score=2,
        description="Replace gasoline commuter vehicle with a battery electric vehicle (BEV).",
        co_benefits=["Zero tailpipe emissions", "Lower maintenance costs", "Regenerative braking efficiency"],
    ),
    DecarbonizationAction(
        id="heat_pump_hvac",
        title="Air-Source Heat Pump HVAC",
        category="Buildings",
        co2e_reduction_kg_yr=2900.0,
        capital_cost_usd=5500.0,
        annual_savings_usd=750.0,
        payback_years=7.3,
        effort_score=3,
        description="Replace gas/oil boiler or resistive heating with a high-COP inverter heat pump.",
        co_benefits=["Year-round heating and cooling", "Improved indoor air quality", "Eliminates gas leak risk"],
    ),
    DecarbonizationAction(
        id="building_insulation",
        title="Building Envelope Insulation & Air Sealing",
        category="Buildings",
        co2e_reduction_kg_yr=2100.0,
        capital_cost_usd=2800.0,
        annual_savings_usd=580.0,
        payback_years=4.8,
        effort_score=2,
        description="Upgrade attic and exterior wall insulation to R-49 and seal drafts with aerobarriers.",
        co_benefits=["Acoustic noise reduction", "Thermal comfort", "Prevents moisture and mold"],
    ),
    DecarbonizationAction(
        id="commercial_led",
        title="Full-Facility Smart LED Retrofit",
        category="Energy",
        co2e_reduction_kg_yr=1400.0,
        capital_cost_usd=1200.0,
        annual_savings_usd=420.0,
        payback_years=2.9,
        effort_score=1,
        description="Retrofit all incandescent/fluorescent fixtures with daylight-sensing smart LEDs.",
        co_benefits=["Rapid payback (< 3 yrs)", "Reduced heat load in summer", "Long lifespan (50,000 hrs)"],
    ),
    DecarbonizationAction(
        id="smart_thermostat",
        title="Smart Thermostat & Zone Automation",
        category="Buildings",
        co2e_reduction_kg_yr=850.0,
        capital_cost_usd=350.0,
        annual_savings_usd=180.0,
        payback_years=1.9,
        effort_score=1,
        description="Implement occupancy-aware thermostats with predictive heating/cooling scheduling.",
        co_benefits=["Remote control via mobile app", "Demand-response grid rebates", "Instant setup"],
    ),
    DecarbonizationAction(
        id="plant_rich_diet",
        title="Institutional / Household Plant-Rich Diet",
        category="Food",
        co2e_reduction_kg_yr=1200.0,
        capital_cost_usd=0.0,
        annual_savings_usd=350.0,
        payback_years=0.0,
        effort_score=2,
        description="Shift meals towards plant proteins, legumes, and sustainably sourced produce.",
        co_benefits=["Cardiovascular health", "Reduced water and land footprint", "Direct grocery savings"],
    ),
    DecarbonizationAction(
        id="composting_zero_waste",
        title="Organic Composting & Zero-Waste Protocol",
        category="Food",
        co2e_reduction_kg_yr=650.0,
        capital_cost_usd=150.0,
        annual_savings_usd=80.0,
        payback_years=1.9,
        effort_score=1,
        description="Divert organic kitchen/yard waste from landfills to aerobic composting systems.",
        co_benefits=["Diverts methane from landfills", "Produces nutrient-rich soil amendment", "Reduces trash bills"],
    ),
    DecarbonizationAction(
        id="urban_micro_forest",
        title="Urban Miyawaki Micro-Forest & Tree Canopy",
        category="Nature",
        co2e_reduction_kg_yr=950.0,
        capital_cost_usd=1800.0,
        annual_savings_usd=120.0,  # Shading & cooling savings
        payback_years=15.0,
        effort_score=3,
        description="Plant dense native pocket forest to sequester carbon, absorb stormwater, and cool local microclimate.",
        co_benefits=["Biodiversity haven", "Urban heat island mitigation", "Stormwater retention"],
    ),
    DecarbonizationAction(
        id="clean_commute_program",
        title="Active Commuting & E-Bike Integration",
        category="Transport",
        co2e_reduction_kg_yr=1100.0,
        capital_cost_usd=1400.0,
        annual_savings_usd=620.0,
        payback_years=2.3,
        effort_score=1,
        description="Incorporate electric cargo/commuter bike for trips under 10 km.",
        co_benefits=["Improved cardiovascular fitness", "Zero congestion time", "Negligible parking costs"],
    ),
]


class DecarbonizationService:
    """Service providing decarbonization action queries and analytics."""

    def __init__(self, actions: Optional[List[DecarbonizationAction]] = None):
        self.actions = actions or DEFAULT_ACTIONS

    def get_all_actions(self) -> List[Dict[str, Any]]:
        """Returns all available decarbonization actions as dictionaries."""
        return [asdict(a) for a in self.actions]

    def get_actions_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Filters actions by domain category."""
        return [asdict(a) for a in self.actions if a.category.lower() == category.lower()]

    def calculate_marginal_abatement_cost(self, action: DecarbonizationAction, lifetime_years: int = 15) -> float:
        """
        Calculates the Marginal Abatement Cost (MAC) in $/tonne CO2e.
        MAC = (Net Lifetime Cost) / (Lifetime Tonnes CO2e Avoided)
        Negative MAC indicates net financial savings over the asset lifetime.
        """
        net_lifetime_cost = action.capital_cost_usd - (action.annual_savings_usd * lifetime_years)
        lifetime_tonnes_co2e = (action.co2e_reduction_kg_yr * lifetime_years) / 1000.0
        if lifetime_tonnes_co2e <= 0:
            return 0.0
        return round(net_lifetime_cost / lifetime_tonnes_co2e, 2)
