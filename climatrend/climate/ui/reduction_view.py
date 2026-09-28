"""
Streamlit View Component for Feature 4: Greenhouse-Gas Emission Reduction Recommendations.
Provides interactive scenario modeling and PuLP Integer Linear Programming (ILP)
optimization to maximize CO2e reduction under budget and implementation constraints.
Renders abatement bubble charts, category distributions, and actionable cards.
"""

from typing import Any, Dict, List
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from climatrend.climate.reduction.optimizer import EmissionReductionOptimizer
from climatrend.climate.reduction.service import DEFAULT_ACTIONS, DecarbonizationService


def render_reduction_view(translations: Dict[str, Any] = None) -> None:
    """Renders the GHG Emission Reduction Recommendations & Portfolio Optimizer."""
    t = translations or {}

    st.markdown(
        """
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
            <h3 style="margin:0; color:#f8fafc;">💡 Greenhouse-Gas Emission Reduction Recommendations</h3>
            <span style="color:#10b981; font-size:13px; font-weight:600;">PuLP Integer Linear Programming • Marginal Abatement</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    service = DecarbonizationService()
    optimizer = EmissionReductionOptimizer()
    all_actions = service.get_all_actions()

    # Scenario & Constraint Inputs
    st.markdown("##### ⚙️ Scenario Budget & Implementation Constraints")
    c1, c2, c3 = st.columns([1.5, 1.5, 2])

    with c1:
        budget_limit = st.slider(
            "Capital Budget Available ($ USD)",
            min_value=1000,
            max_value=40000,
            value=15000,
            step=1000,
            format="$%d",
            key="opt_budget_slider",
        )

    with c2:
        effort_limit = st.slider(
            "Max Implementation Capacity (Effort Units)",
            min_value=2,
            max_value=20,
            value=8,
            step=1,
            help="Sum of implementation complexity scores. 1=Easy/Immediate, 5=Major civil engineering.",
            key="opt_effort_slider",
        )

    with c3:
        all_categories = sorted(list({a["category"] for a in all_actions}))
        selected_categories = st.multiselect(
            "Allowed Action Sectors",
            options=all_categories,
            default=all_categories,
            key="opt_category_multiselect",
        )

    # Optimization trigger
    if st.button("🚀 Find Optimal Decarbonization Portfolio", type="primary", use_container_width=True):
        st.session_state["reduction_portfolio"] = optimizer.optimize_portfolio(
            max_budget_usd=budget_limit,
            max_effort_capacity=effort_limit,
            allowed_categories=selected_categories if selected_categories else None,
        )

    # Default run if not yet executed
    if "reduction_portfolio" not in st.session_state:
        st.session_state["reduction_portfolio"] = optimizer.optimize_portfolio(
            max_budget_usd=budget_limit,
            max_effort_capacity=effort_limit,
            allowed_categories=selected_categories if selected_categories else None,
        )

    portfolio = st.session_state["reduction_portfolio"]
    selected_actions = portfolio["selected_actions"]
    selected_ids = {a["id"] for a in selected_actions}

    # Summary Metrics Row
    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.markdown(
            f"""
            <div style="background-color:#1e293b; padding:16px; border-radius:10px; border-left:5px solid #10b981;">
                <span style="font-size:12px; color:#94a3b8; text-transform:uppercase;">Annual CO₂e Reduced</span>
                <div style="font-size:26px; font-weight:700; color:#10b981; margin-top:4px;">
                    {portfolio['total_co2e_reduction_tonnes_yr']:.2f} t / yr
                </div>
                <div style="font-size:12px; color:#cbd5e1; margin-top:4px;">
                    {portfolio['total_co2e_reduction_kg_yr']:.0f} kg CO₂e saved
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m2:
        st.markdown(
            f"""
            <div style="background-color:#1e293b; padding:16px; border-radius:10px; border-left:5px solid #3b82f6;">
                <span style="font-size:12px; color:#94a3b8; text-transform:uppercase;">Capital Invested</span>
                <div style="font-size:26px; font-weight:700; color:#3b82f6; margin-top:4px;">
                    ${portfolio['total_cost_usd']:,.0f}
                </div>
                <div style="font-size:12px; color:#cbd5e1; margin-top:4px;">
                    {portfolio['budget_utilized_pct']:.1f}% of ${budget_limit:,} budget
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m3:
        st.markdown(
            f"""
            <div style="background-color:#1e293b; padding:16px; border-radius:10px; border-left:5px solid #f59e0b;">
                <span style="font-size:12px; color:#94a3b8; text-transform:uppercase;">Annual OPEX Savings</span>
                <div style="font-size:26px; font-weight:700; color:#f59e0b; margin-top:4px;">
                    ${portfolio['total_annual_savings_usd']:,.0f} / yr
                </div>
                <div style="font-size:12px; color:#cbd5e1; margin-top:4px;">
                    Direct utility & fuel savings
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m4:
        st.markdown(
            f"""
            <div style="background-color:#1e293b; padding:16px; border-radius:10px; border-left:5px solid #a855f7;">
                <span style="font-size:12px; color:#94a3b8; text-transform:uppercase;">Portfolio Payback</span>
                <div style="font-size:26px; font-weight:700; color:#a855f7; margin-top:4px;">
                    {portfolio['portfolio_payback_years']:.1f} Years
                </div>
                <div style="font-size:12px; color:#cbd5e1; margin-top:4px;">
                    Status: {portfolio['status']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Interactive Visualizations
    v_col1, v_col2 = st.columns([1.3, 1])

    with v_col1:
        st.markdown("##### 🎯 Abatement Efficiency & Investment Frontier")
        plot_data = []
        for a in all_actions:
            is_chosen = a["id"] in selected_ids
            plot_data.append({
                "Action": a["title"],
                "Category": a["category"],
                "Capital Cost ($)": a["capital_cost_usd"],
                "CO2e Saved (kg/yr)": a["co2e_reduction_kg_yr"],
                "Annual Savings ($)": a["annual_savings_usd"],
                "Payback (yrs)": a["payback_years"],
                "Selected": "Selected in Portfolio" if is_chosen else "Not Selected",
            })
        df_plot = pd.DataFrame(plot_data)

        fig_scatter = px.scatter(
            df_plot,
            x="Capital Cost ($)",
            y="CO2e Saved (kg/yr)",
            color="Category",
            symbol="Selected",
            size="Annual Savings ($)",
            hover_name="Action",
            hover_data=["Payback (yrs)", "Annual Savings ($)"],
            color_discrete_sequence=["#10b981", "#3b82f6", "#f59e0b", "#ec4899", "#8b5cf6"],
        )
        fig_scatter.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(gridcolor='#334155', color='#94a3b8', title="Capital Investment ($ USD)"),
            yaxis=dict(gridcolor='#334155', color='#94a3b8', title="Annual CO₂e Reduction (kg / yr)"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5, font=dict(color="#cbd5e1")),
            height=380,
            margin=dict(l=30, r=20, t=10, b=40),
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    with v_col2:
        st.markdown("##### 📊 Sector Share of CO₂e Savings")
        if selected_actions:
            cat_totals = {}
            for a in selected_actions:
                cat_totals[a["category"]] = cat_totals.get(a["category"], 0.0) + a["co2e_reduction_kg_yr"]

            fig_donut = go.Figure(data=[go.Pie(
                labels=list(cat_totals.keys()),
                values=list(cat_totals.values()),
                hole=0.5,
                marker=dict(colors=["#10b981", "#3b82f6", "#f59e0b", "#ec4899", "#8b5cf6"]),
            )])
            fig_donut.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color="#cbd5e1"),
                margin=dict(l=20, r=20, t=10, b=20),
                height=380,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig_donut, use_container_width=True)
        else:
            st.info("No actions selected under current budget/effort limits. Try increasing budget or effort capacity.")

    # Actionable Intervention Cards
    st.markdown("##### 📋 Recommended Priority Action Items")
    if selected_actions:
        a_col1, a_col2 = st.columns(2)
        for idx, action in enumerate(selected_actions):
            target_col = a_col1 if idx % 2 == 0 else a_col2
            with target_col:
                effort_stars = "⭐" * action["effort_score"]
                co_benefits_tags = " ".join([f"`{cb}`" for cb in action["co_benefits"]])
                st.markdown(
                    f"""
                    <div style="background-color:#1e293b; border-radius:8px; padding:16px; margin-bottom:14px; border-left:4px solid #10b981;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-weight:700; color:#f8fafc; font-size:15px;">{action['title']}</span>
                            <span style="background-color:#10b98122; color:#10b981; font-weight:700; font-size:12px; padding:2px 8px; border-radius:4px;">
                                {action['category']}
                            </span>
                        </div>
                        <p style="margin:8px 0; font-size:13px; color:#cbd5e1;">{action['description']}</p>
                        <div style="display:flex; justify-content:space-between; font-size:12px; color:#94a3b8; margin-top:8px;">
                            <span>Capex: <b style="color:#f8fafc;">${action['capital_cost_usd']:,.0f}</b></span>
                            <span>Annual Savings: <b style="color:#10b981;">${action['annual_savings_usd']:,.0f}/yr</b></span>
                            <span>Payback: <b style="color:#38bdf8;">{action['payback_years']:.1f} yrs</b></span>
                            <span>Effort: {effort_stars}</span>
                        </div>
                        <div style="margin-top:10px; font-size:12px;">
                            <span style="color:#94a3b8;">Co-Benefits:</span> {co_benefits_tags}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.warning("No actions fit into the specified constraint window.")

    # Complete Catalog Table with Export
    with st.expander("📚 Browse Complete Decarbonization Action Catalog"):
        df_all = pd.DataFrame(all_actions)
        df_all["Selected"] = df_all["id"].apply(lambda x: "✅ Yes" if x in selected_ids else "❌ No")
        df_display = df_all[[
            "Selected", "title", "category", "capital_cost_usd",
            "annual_savings_usd", "co2e_reduction_kg_yr", "payback_years", "effort_score"
        ]]
        df_display.columns = [
            "Included", "Action Title", "Category", "Capital Cost ($)",
            "Annual Savings ($)", "CO2e Saved (kg/yr)", "Payback (yrs)", "Effort (1-5)"
        ]
        st.dataframe(df_display, use_container_width=True, hide_index=True)
