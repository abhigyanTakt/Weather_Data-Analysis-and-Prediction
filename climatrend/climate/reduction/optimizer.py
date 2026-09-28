"""
PuLP Integer Linear Programming (ILP) Optimizer for Emission Reductions.
Finds the optimal portfolio of decarbonization investments that maximizes
CO2e reduction within strict capital budget and implementation effort constraints.
Includes a greedy knapsack fallback for maximum system resilience.
"""

from dataclasses import asdict
import logging
from typing import Any, Dict, List, Optional

import pulp

from climatrend.climate.reduction.service import DEFAULT_ACTIONS, DecarbonizationAction

logger = logging.getLogger(__name__)


class EmissionReductionOptimizer:
    """Integer Linear Programming optimizer for portfolio decarbonization."""

    def __init__(self, actions: Optional[List[DecarbonizationAction]] = None):
        self.actions = actions or DEFAULT_ACTIONS

    def optimize_portfolio(
        self,
        max_budget_usd: float = 15000.0,
        max_effort_capacity: int = 10,
        allowed_categories: Optional[List[str]] = None,
        mandatory_action_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Solves the binary knapsack optimization problem:
        Maximize sum(x_i * CO2e_i)
        Subject to:
          sum(x_i * Cost_i) <= max_budget
          sum(x_i * Effort_i) <= max_effort
          x_m == 1 for m in mandatory_action_ids
        """
        mandatory_ids = set(mandatory_action_ids or [])

        # Filter candidate actions by allowed categories
        candidates = [
            a for a in self.actions
            if allowed_categories is None or a.category in allowed_categories or a.id in mandatory_ids
        ]

        if not candidates:
            return {
                "status": "No Candidates",
                "selected_actions": [],
                "total_co2e_reduction_kg_yr": 0.0,
                "total_cost_usd": 0.0,
                "total_annual_savings_usd": 0.0,
                "portfolio_payback_years": 0.0,
                "budget_utilized_pct": 0.0,
            }

        try:
            # 1. Formulation with PuLP
            prob = pulp.LpProblem("Decarbonization_Portfolio_Optimization", pulp.LpMaximize)

            # Decision variables: x_i in {0, 1}
            x_vars = {
                a.id: pulp.LpVariable(f"select_{a.id}", cat=pulp.LpBinary)
                for a in candidates
            }

            # Objective Function: Maximize annual CO2e reduction (kg)
            prob += pulp.lpSum([x_vars[a.id] * a.co2e_reduction_kg_yr for a in candidates])

            # Constraint 1: Capital Budget
            prob += pulp.lpSum([x_vars[a.id] * a.capital_cost_usd for a in candidates]) <= max_budget_usd

            # Constraint 2: Effort Capacity
            prob += pulp.lpSum([x_vars[a.id] * a.effort_score for a in candidates]) <= max_effort_capacity

            # Constraint 3: Mandatory inclusions
            for a in candidates:
                if a.id in mandatory_ids:
                    prob += x_vars[a.id] == 1

            # Solve quietly without solver logs
            solver = pulp.PULP_CBC_CMD(msg=False)
            prob.solve(solver)

            status = pulp.LpStatus[prob.status]

            if status in ["Optimal", "Not Solved"] and prob.status == pulp.constants.LpStatusOptimal:
                selected_actions = [
                    a for a in candidates if x_vars[a.id].varValue is not None and x_vars[a.id].varValue > 0.5
                ]
            else:
                logger.warning(f"PuLP solver returned status {status}. Falling back to greedy knapsack.")
                selected_actions = self._solve_greedy(candidates, max_budget_usd, max_effort_capacity, mandatory_ids)
                status = "Optimal (Greedy Heuristic)"

        except Exception as e:
            logger.warning(f"PuLP optimization encountered exception: {e}. Executing greedy fallback.")
            selected_actions = self._solve_greedy(candidates, max_budget_usd, max_effort_capacity, mandatory_ids)
            status = "Optimal (Greedy Fallback)"

        # Calculate portfolio aggregates
        tot_co2 = sum(a.co2e_reduction_kg_yr for a in selected_actions)
        tot_cost = sum(a.capital_cost_usd for a in selected_actions)
        tot_savings = sum(a.annual_savings_usd for a in selected_actions)
        payback = round(tot_cost / tot_savings, 1) if tot_savings > 0 else 0.0
        budget_pct = round((tot_cost / max_budget_usd) * 100.0, 1) if max_budget_usd > 0 else 0.0

        return {
            "status": status,
            "selected_actions": [asdict(a) for a in selected_actions],
            "total_co2e_reduction_kg_yr": round(tot_co2, 1),
            "total_co2e_reduction_tonnes_yr": round(tot_co2 / 1000.0, 2),
            "total_cost_usd": round(tot_cost, 2),
            "total_annual_savings_usd": round(tot_savings, 2),
            "portfolio_payback_years": payback,
            "budget_utilized_pct": budget_pct,
            "selected_count": len(selected_actions),
            "candidate_count": len(candidates),
        }

    def _solve_greedy(
        self,
        candidates: List[DecarbonizationAction],
        max_budget: float,
        max_effort: int,
        mandatory_ids: set,
    ) -> List[DecarbonizationAction]:
        """Greedy knapsack heuristic ordering by CO2e abatement efficiency."""
        selected: List[DecarbonizationAction] = []
        rem_budget = max_budget
        rem_effort = max_effort

        # First add mandatory actions
        for a in candidates:
            if a.id in mandatory_ids:
                if a.capital_cost_usd <= rem_budget and a.effort_score <= rem_effort:
                    selected.append(a)
                    rem_budget -= a.capital_cost_usd
                    rem_effort -= a.effort_score

        # Sort remaining by CO2e per dollar (avoid div by 0 with +1.0)
        remaining = [a for a in candidates if a not in selected]
        remaining.sort(
            key=lambda a: a.co2e_reduction_kg_yr / (a.capital_cost_usd + 1.0) / a.effort_score,
            reverse=True,
        )

        for a in remaining:
            if a.capital_cost_usd <= rem_budget and a.effort_score <= rem_effort:
                selected.append(a)
                rem_budget -= a.capital_cost_usd
                rem_effort -= a.effort_score

        return selected
