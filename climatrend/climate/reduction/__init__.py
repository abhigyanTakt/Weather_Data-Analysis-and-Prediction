"""
Greenhouse-Gas Emission Reduction Recommendations & Optimization.
"""

from climatrend.climate.reduction.optimizer import EmissionReductionOptimizer
from climatrend.climate.reduction.service import DEFAULT_ACTIONS, DecarbonizationAction, DecarbonizationService

__all__ = [
    "DecarbonizationAction",
    "DecarbonizationService",
    "EmissionReductionOptimizer",
    "DEFAULT_ACTIONS",
]
