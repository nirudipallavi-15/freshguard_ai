"""
FreshGuard AI - Streamlit Dashboard
Agentic AI for Zero-Waste Grocery Management
"""

import streamlit as st

# Optional pandas import - falls back to native Python data structures if pandas/C-extensions are restricted by Windows Application Control
try:
    import pandas as pd
except Exception:
    pd = None

from data import load_grocery_data
from agents import CoordinatorAgent
from eval import EvaluationEngine

# Configure Page
st.set_page_config(
    page_title="FreshGuard AI — Zero-Waste Grocery Management",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }
    .badge-critical { color: #ef4444; font-weight: bold; }
    .badge-high { color: #f97316; font-weight: bold; }
    .badge-medium { color: #eab308; font-weight: bold; }
    .badge-low { color: #10b981; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "inventory" not in st.session_state:
    st.session_state.inventory = load_grocery_data()
if "decision_log" not in st.session_state:
    st.session_state.decision_log = []

# Sidebar Controls: Scenarios & Disruption Simulation
st.sidebar.title("🌱 FreshGuard AI")
st.sidebar.caption("Zero-Waste Hackathon Edition")
st.sidebar.markdown("---")

st.sidebar.subheader("🔬 Scenario Simulator")
scenario = st.sidebar.selectbox(
    "Preset Disruption Scenario",
    [
        "Standard Mid-Week",
        "Weekend Surge (+50% Demand)",
        "Rainy Slump (-40% Demand)",
        "Heatwave Shock (-2 Days Shelf Life)",
        "Store Imbalance (Downtown Overstocked)",
    ],
    index=0
)

# Scenario parameter mapping
demand_mult = 1.0
shelf_delta = 0

if scenario == "Weekend Surge (+50% Demand)":
    demand_mult = 1.5
elif scenario == "Rainy Slump (-40% Demand)":
    demand_mult = 0.6
elif scenario == "Heatwave Shock (-2 Days Shelf Life)":
    shelf_delta = -2
elif scenario == "Store Imbalance (Downtown Overstocked)":
    demand_mult = 1.0

# Sliders for fine-tuning
st.sidebar.markdown("#### Fine-Tune Shock Parameters")
demand_mult = st.sidebar.slider("Demand Multiplier", 0.5, 2.0, demand_mult, 0.1)
shelf_delta = st.sidebar.slider("Shelf-Life Delta (Days)", -3, 2, shelf_delta, 1)

if st.sidebar.button("🔄 Reset Demo to Initial State"):
    st.session_state.inventory = load_grocery_data()
    st.session_state.decision_log = []
    st.rerun()

# Run Coordinator Agent
recommendations = CoordinatorAgent.synthesize(
    st.session_state.inventory,
    demand_multiplier=demand_mult,
    shelf_life_delta=shelf_delta
)

# Merge human decisions
rec_map = {r["id"]: r for r in recommendations}
for entry in st.session_state.decision_log:
    if entry["id"] in rec_map:
        rec_map[entry["id"]]["approval_status"] = entry["status"]
        rec_map[entry["id"]]["planner_notes"] = entry["notes"]

# Run Evaluation Benchmark
metrics = EvaluationEngine.run_comparison(
    st.session_state.inventory,
    recommendations,
    demand_multiplier=demand_mult,
    shelf_life_delta=shelf_delta
)

# Header
st.title("🌱 FreshGuard AI — Zero-Waste Grocery Management")
st.write("Autonomous Multi-Agent System for Grocery Freshness, Dynamic Markdowns, Replenishment & Cross-Store Balancing")

# Top KPI Metric Cards
col1, col2, col3, col4 = st.columns(4)

total_skus = len(recommendations)
high_risk = sum(1 for r in recommendations if r["risk_level"] in ("CRITICAL", "HIGH", "EXPIRED"))
stockout_alerts = sum(1 for r in recommendations if r["action"] in ("REPLENISH", "TRANSFER_IN"))
salvaged_val = sum(r["expected_effect"].get("salvaged_revenue", 0.0) for r in recommendations)

with col1:
    st.metric("📦 Monitored SKUs", total_skus, help="Total active product-store instances")
with col2:
    st.metric("⚠️ Perishability Risk", f"{high_risk} ", delta=f"{metrics['freshguard_ai']['waste_units']} units at risk", delta_color="inverse")
with col3:
    st.metric("📉 Stockout Alerts", f"{stockout_alerts} ", help="SKUs breached below reorder point")
with col4:
    st.metric("💰 Salvaged Revenue", f"₹{salvaged_val:.2f}", delta=f"-{metrics['improvements']['waste_reduction_pct']}% waste")

st.markdown("---")

# Main Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Live Inventory & Recommendations",
    "🤖 Multi-Agent Architecture",
    "✍️ Planner Approvals & Decision Log",
    "📊 Baseline Benchmark & Evaluation"
])

# ----------------- TAB 1: INVENTORY & RECOMMENDATIONS -----------------
with tab1:
    st.subheader("Store Inventory & Multi-Agent Proposals")
    
    # Filter Row
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        store_filter = st.selectbox("Store Filter", ["All Stores", "Downtown Market", "Suburban Hub"])
    with fcol2:
        risk_filter = st.selectbox("Risk Filter", ["All Risks", "CRITICAL", "HIGH", "MEDIUM", "LOW", "EXPIRED"])
    with fcol3:
        search_query = st.text_input("Search Product / SKU", "").lower()

    # Filtered Records
    filtered_recs = recommendations
    if store_filter != "All Stores":
        filtered_recs = [r for r in filtered_recs if r["store"] == store_filter]
    if risk_filter != "All Risks":
        filtered_recs = [r for r in filtered_recs if r["risk_level"] == risk_filter]
    if search_query:
        filtered_recs = [r for r in filtered_recs if search_query in r["name"].lower() or search_query in r["sku"].lower()]

    # Format Table DataFrame
    table_data = []
    for r in filtered_recs:
        table_data.append({
            "Product ID": r["sku"],
            "Product": r["name"],
            "Store": r["store"],
            "Stock": r["current_stock"],
            "Forecast (/day)": r["daily_forecast"],
            "Days Left": r["effective_days"],
            "Price": f"₹{r['unit_price']:.2f}",
            "Risk": r["risk_level"],
            "Action": r["action_label"],
            "Confidence": f"{r['confidence']}%",
            "Status": r["approval_status"]
        })

    if pd is not None:
        st.dataframe(pd.DataFrame(table_data), use_container_width=True)
    else:
        st.dataframe(table_data, use_container_width=True)

    # Interactive Product Inspector & Approval Form
    st.markdown("### 🔎 Product Inspector & Planner Action")
    selected_sku = st.selectbox(
        "Select Product to Review & Decide",
        [f"{r['id']} | {r['name']} ({r['store']})" for r in filtered_recs] if filtered_recs else []
    )

    if selected_sku:
        sel_id = selected_sku.split(" | ")[0]
        sel_rec = next((r for r in recommendations if r["id"] == sel_id), None)
        
        if sel_rec:
            st.info(f"**Coordinator Rationale:** {sel_rec['rationale']}")
            
            pcol1, pcol2, pcol3 = st.columns(3)
            with pcol1:
                st.write(f"**Proposed Quantity / Discount:** {sel_rec['proposed_quantity']} units / {sel_rec['proposed_discount_pct']}%")
            with pcol2:
                planner_note = st.text_input("Planner Audit Notes", value=sel_rec["planner_notes"], key=f"note_{sel_id}")
            with pcol3:
                st.write(f"**Simulated Effect:** {sel_rec['expected_effect'].get('simulated_benefit', 'Safe turnover')}")

            bcol1, bcol2, bcol3 = st.columns(3)
            with bcol1:
                if st.button("✅ Approve Recommendation", key=f"app_{sel_id}"):
                    st.session_state.decision_log = [d for d in st.session_state.decision_log if d["id"] != sel_id]
                    st.session_state.decision_log.append({
                        "id": sel_id, "name": sel_rec["name"], "store": sel_rec["store"],
                        "action": sel_rec["action_label"], "status": "APPROVED", "notes": planner_note or "Approved as-is."
                    })
                    st.success("Proposal approved!")
                    st.rerun()
            with bcol2:
                if st.button("✏️ Modify & Approve", key=f"mod_{sel_id}"):
                    st.session_state.decision_log = [d for d in st.session_state.decision_log if d["id"] != sel_id]
                    st.session_state.decision_log.append({
                        "id": sel_id, "name": sel_rec["name"], "store": sel_rec["store"],
                        "action": sel_rec["action_label"], "status": "MODIFIED", "notes": planner_note or "Modified parameters approved."
                    })
                    st.warning("Modified proposal approved!")
                    st.rerun()
            with bcol3:
                if st.button("❌ Reject Proposal", key=f"rej_{sel_id}"):
                    st.session_state.decision_log = [d for d in st.session_state.decision_log if d["id"] != sel_id]
                    st.session_state.decision_log.append({
                        "id": sel_id, "name": sel_rec["name"], "store": sel_rec["store"],
                        "action": sel_rec["action_label"], "status": "REJECTED", "notes": planner_note or "Dismissed by planner."
                    })
                    st.error("Proposal rejected.")
                    st.rerun()

# ----------------- TAB 2: AGENT ARCHITECTURE -----------------
with tab2:
    st.subheader("Multi-Agent Architecture & Governance")
    st.markdown("""
    FreshGuard AI orchestrates **five specialized autonomous agent modules** to balance waste, margins, and customer availability:
    
    1. **Demand Agent:** Computes transparent 7-day weighted moving average and demand volatility. *(Explicitly labeled as a transparent baseline forecast, not a black-box ML model).*
    2. **Freshness Agent:** Calculates perishability risk and flags surplus inventory unlikely to sell before expiration.
    3. **Replenishment Agent:** Identifies lead-time stockout risks and enforces strict guardrails against over-ordering near-expiry inventory.
    4. **Markdown Agent:** Formulates tiered promotional discounts (20%, 30%, 50%) based on remaining shelf-life days and retail price elasticity simulations.
    5. **Coordinator Agent:** Resolves trade-offs, evaluates cross-store shuttles, enforces food safety guardrails (never sell expired food), and submits proposals for human planner review.
    """)

# ----------------- TAB 3: PLANNER AUDIT LOG -----------------
with tab3:
    st.subheader("Human Planner Governance & Decision Log")
    if not st.session_state.decision_log:
        st.info("No planner decisions recorded yet. Inspect and decide on proposals in the inventory tab.")
    else:
        if pd is not None:
            st.dataframe(pd.DataFrame(st.session_state.decision_log), use_container_width=True)
        else:
            st.dataframe(st.session_state.decision_log, use_container_width=True)

# ----------------- TAB 4: EVALUATION & BENCHMARK -----------------
with tab4:
    st.subheader("Baseline Policy vs. FreshGuard AI Benchmark")
    
    ecol1, ecol2 = st.columns(2)
    with ecol1:
        st.markdown("### 🏢 Traditional Baseline Policy")
        st.caption("Fixed reorder threshold (order 25 when stock < 15), zero proactive markdowns, siloed stores.")
        st.write(f"**Projected Waste Units:** {metrics['baseline']['waste_units']} units")
        st.write(f"**Discarded Waste Cost:** ₹{metrics['baseline']['waste_cost']:.2f}")
        st.write(f"**Stockout Units:** {metrics['baseline']['stockout_units']} units")
        st.write(f"**Lost Customer Sales:** ₹{metrics['baseline']['lost_revenue']:.2f}")
        st.write(f"**Food Waste to Landfill:** {metrics['baseline']['food_waste_kg']} kg")
        st.write(f"**Landfill GHG Emissions:** {metrics['baseline']['co2e_emissions_kg']} kg CO₂e")

    with ecol2:
        st.markdown("### 🌱 FreshGuard Agentic AI Policy")
        st.caption("Freshness-aware replenishment, cross-store shuttles, dynamic markdowns.")
        st.write(f"**Projected Waste Units:** {metrics['freshguard_ai']['waste_units']} units ({metrics['improvements']['waste_reduction_pct']}% reduction)")
        st.write(f"**Discarded Waste Cost:** ₹{metrics['freshguard_ai']['waste_cost']:.2f}")
        st.write(f"**Stockout Units:** {metrics['freshguard_ai']['stockout_units']} units")
        st.write(f"**Salvaged Revenue:** +₹{metrics['freshguard_ai']['salvaged_revenue']:.2f}")
        st.write(f"**Food Waste to Landfill:** {metrics['freshguard_ai']['food_waste_kg']} kg")
        st.write(f"**GHG Emissions Avoided:** {metrics['improvements']['co2e_avoided_kg']} kg CO₂e saved")

    st.markdown("---")
    st.markdown("#### 📋 Assumptions & Mathematical Model")
    for a in metrics["assumptions"]:
        st.markdown(f"- {a}")