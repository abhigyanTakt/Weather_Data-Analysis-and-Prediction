"""
Unit tests for Feature 4: Greenhouse-Gas Emission Reduction Recommendations & PuLP Optimizer.
"""

import pytest

from climatrend.climate.reduction.optimizer import EmissionReductionOptimizer
from climatrend.climate.reduction.service import DEFAULT_ACTIONS, DecarbonizationAction, DecarbonizationService


def test_decarbonization_service():
    service = DecarbonizationService()
    actions = service.get_all_actions()
    assert len(actions) >= 8

    energy_actions = service.get_actions_by_category("Energy")
    assert len(energy_actions) >= 1
    assert all(a["category"] == "Energy" for a in energy_actions)

    action = DEFAULT_ACTIONS[0]
    mac = service.calculate_marginal_abatement_cost(action, lifetime_years=10)
    assert isinstance(mac, float)


def test_optimizer_budget_and_effort_constraints():
    optimizer = EmissionReductionOptimizer()
    budget = 10000.0
    effort = 6

    res = optimizer.optimize_portfolio(max_budget_usd=budget, max_effort_capacity=effort)

    assert "selected_actions" in res
    assert res["total_cost_usd"] <= budget
    tot_effort = sum(a["effort_score"] for a in res["selected_actions"])
    assert tot_effort <= effort
    assert res["total_co2e_reduction_kg_yr"] > 0
    assert res["portfolio_payback_years"] >= 0


def test_optimizer_mandatory_inclusion():
    optimizer = EmissionReductionOptimizer()
    # Force 'commercial_led' to be included
    res = optimizer.optimize_portfolio(
        max_budget_usd=15000.0,
        max_effort_capacity=10,
        mandatory_action_ids=["commercial_led"],
    )
    selected_ids = [a["id"] for a in res["selected_actions"]]
    assert "commercial_led" in selected_ids


def test_optimizer_greedy_fallback():
    optimizer = EmissionReductionOptimizer()
    candidates = DEFAULT_ACTIONS[:4]
    greedy_res = optimizer._solve_greedy(
        candidates=candidates,
        max_budget=8000.0,
        max_effort=5,
        mandatory_ids=set(),
    )
    assert len(greedy_res) >= 1
    tot_cost = sum(a.capital_cost_usd for a in greedy_res)
    assert tot_cost <= 8000.0
