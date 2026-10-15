import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="FreshRoute | Agricultural Produce Allocation",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 1. SAMPLE DATA GENERATION (Deterministic)
# -----------------------------------------------------------------------------
@st.cache_data
def load_base_data():
    # Inventory Batches
    inventory_data = [
        {"batch_id": "B001", "produce": "Tomatoes", "quantity_kg": 500, "shelf_life_days": 3, "cost_per_kg": 15.0},
        {"batch_id": "B002", "produce": "Tomatoes", "quantity_kg": 300, "shelf_life_days": 1, "cost_per_kg": 12.0},
        {"batch_id": "B003", "produce": "Apples", "quantity_kg": 800, "shelf_life_days": 14, "cost_per_kg": 40.0},
        {"batch_id": "B004", "produce": "Bananas", "quantity_kg": 600, "shelf_life_days": 4, "cost_per_kg": 20.0},
        {"batch_id": "B005", "produce": "Potatoes", "quantity_kg": 1000, "shelf_life_days": 30, "cost_per_kg": 10.0},
        {"batch_id": "B006", "produce": "Leafy Greens", "quantity_kg": 250, "shelf_life_days": 2, "cost_per_kg": 25.0}
    ]
    
    # Destinations & Demand (Produce, Demand KG, Selling Price/kg, Travel Time Days, Transport Cost/kg, Max Capacity KG)
    destinations_data = [
        {"destination_id": "D1", "name": "Metro Supermarket", "produce": "Tomatoes", "demand_kg": 400, "selling_price": 30.0, "travel_time_days": 1, "transport_cost_per_kg": 2.0, "max_capacity_kg": 600},
        {"destination_id": "D2", "name": "Local Grocery Co-op", "produce": "Tomatoes", "demand_kg": 250, "selling_price": 28.0, "travel_time_days": 2, "transport_cost_per_kg": 3.5, "max_capacity_kg": 300},
        {"destination_id": "D3", "name": "Fresh Mart Downtown", "produce": "Apples", "demand_kg": 500, "selling_price": 65.0, "travel_time_days": 3, "transport_cost_per_kg": 3.0, "max_capacity_kg": 700},
        {"destination_id": "D4", "name": "Suburban Wholesale", "produce": "Apples", "demand_kg": 400, "selling_price": 60.0, "travel_time_days": 5, "transport_cost_per_kg": 4.5, "max_capacity_kg": 500},
        {"destination_id": "D5", "name": "City Express Market", "produce": "Bananas", "demand_kg": 500, "selling_price": 35.0, "travel_time_days": 2, "transport_cost_per_kg": 2.5, "max_capacity_kg": 600},
        {"destination_id": "D6", "name": "Bulk Food Distributor", "produce": "Potatoes", "demand_kg": 900, "selling_price": 18.0, "travel_time_days": 4, "transport_cost_per_kg": 1.5, "max_capacity_kg": 1200},
        {"destination_id": "D7", "name": "Downtown Organic Hub", "produce": "Leafy Greens", "demand_kg": 200, "selling_price": 45.0, "travel_time_days": 1, "transport_cost_per_kg": 2.0, "max_capacity_kg": 250}
    ]
    
    return pd.DataFrame(inventory_data), pd.DataFrame(destinations_data)

# -----------------------------------------------------------------------------
# 2. OPTIMIZATION & BASELINE ALGORITHMS
# -----------------------------------------------------------------------------
def run_optimization(inv_df, dest_df, delay_days=0, capacity_multiplier=1.0, demand_multiplier=1.0):
    inv = inv_df.copy()
    dest = dest_df.copy()
    
    # Apply scenario multipliers
    dest["demand_kg"] = dest["demand_kg"] * demand_multiplier
    dest["max_capacity_kg"] = dest["max_capacity_kg"] * capacity_multiplier
    dest["effective_travel_time"] = dest["travel_time_days"] + delay_days
    
    allocations = []
    
    # Sort inventory by urgency (shelf life ascending) then cost
    inv = inv.sort_values(by=["shelf_life_days", "cost_per_kg"])
    
    # Track remaining quantities
    inv_remaining = inv.set_index("batch_id")["quantity_kg"].to_dict()
    dest_remaining_demand = dest.set_index(["destination_id", "produce"])["demand_kg"].to_dict()
    dest_capacity = dest.set_index("destination_id")["max_capacity_kg"].to_dict()
    
    # Track total allocated per destination for capacity checks
    dest_allocated_total = {d: 0.0 for d in dest_capacity.keys()}

    for _, b_row in inv.iterrows():
        b_id = b_row["batch_id"]
        produce = b_row["produce"]
        shelf_life = b_row["shelf_life_days"]
        
        # Find matching destinations for this produce type
        matching_dests = dest[dest["produce"] == produce].copy()
        
        # Filter out routes where travel time >= shelf life (cannot arrive before expiry)
        matching_dests = matching_dests[matching_dests["effective_travel_time"] < shelf_life]
        
        if matching_dests.empty:
            continue
            
        # Calculate net margin per kg for sorting destinations (selling price - transport cost)
        matching_dests["margin"] = matching_dests["selling_price"] - matching_dests["transport_cost_per_kg"]
        matching_dests = matching_dests.sort_values(by="margin", ascending=False)
        
        for _, d_row in matching_dests.iterrows():
            d_id = d_row["destination_id"]
            
            avail_inv = inv_remaining.get(b_id, 0)
            if avail_inv <= 0:
                break
                
            key = (d_id, produce)
            dem = dest_remaining_demand.get(key, 0)
            if dem <= 0:
                continue
                
            cap_left = dest_capacity.get(d_id, 0) - dest_allocated_total.get(d_id, 0)
            if cap_left <= 0:
                continue
                
            # Allocate amount
            allocated_qty = min(avail_inv, dem, cap_left)
            if allocated_qty <= 0:
                continue
                
            inv_remaining[b_id] -= allocated_qty
            dest_remaining_demand[key] -= allocated_qty
            dest_allocated_total[d_id] += allocated_qty
            
            # Check for discount recommendation (if shelf life <= 2 days, suggest 20% discount)
            discount_pct = 0.20 if shelf_life <= 2 else 0.0
            
            allocations.append({
                "batch_id": b_id,
                "destination_id": d_id,
                "produce": produce,
                "allocated_qty_kg": allocated_qty,
                "travel_time_days": d_row["effective_travel_time"],
                "shelf_life_days": shelf_life,
                "transport_cost_per_kg": d_row["transport_cost_per_kg"],
                "selling_price_per_kg": d_row["selling_price"],
                "discount_pct": discount_pct,
                "reason": f"Allocated successfully (Margin: ${d_row['margin']:.2f}/kg, Shelf Life: {shelf_life}d > Travel: {d_row['effective_travel_time']}d)"
            })
            
    alloc_df = pd.DataFrame(allocations)
    if alloc_df.empty:
        alloc_df = pd.DataFrame(columns=["batch_id", "destination_id", "produce", "allocated_qty_kg", "travel_time_days", "shelf_life_days", "transport_cost_per_kg", "selling_price_per_kg", "discount_pct", "reason"])
        
    return alloc_df, inv_remaining, dest_remaining_demand

def run_baseline(inv_df, dest_df, delay_days=0, capacity_multiplier=1.0, demand_multiplier=1.0):
    # Baseline: First-in, first-out naive allocation without margin sorting or shelf-life safety checks
    inv = inv_df.copy()
    dest = dest_df.copy()
    dest["demand_kg"] = dest["demand_kg"] * demand_multiplier
    dest["max_capacity_kg"] = dest["max_capacity_kg"] * capacity_multiplier
    dest["effective_travel_time"] = dest["travel_time_days"] + delay_days
    
    allocations = []
    inv_remaining = inv.set_index("batch_id")["quantity_kg"].to_dict()
    dest_remaining_demand = dest.set_index(["destination_id", "produce"])["demand_kg"].to_dict()
    dest_capacity = dest.set_index("destination_id")["max_capacity_kg"].to_dict()
    dest_allocated_total = {d: 0.0 for d in dest_capacity.keys()}
    
    for _, b_row in inv.iterrows():
        b_id = b_row["batch_id"]
        produce = b_row["produce"]
        shelf_life = b_row["shelf_life_days"]
        
        matching_dests = dest[dest["produce"] == produce]
        for _, d_row in matching_dests.iterrows():
            d_id = d_row["destination_id"]
            avail_inv = inv_remaining.get(b_id, 0)
            if avail_inv <= 0:
                break
            key = (d_id, produce)
            dem = dest_remaining_demand.get(key, 0)
            if dem <= 0:
                continue
            cap_left = dest_capacity.get(d_id, 0) - dest_allocated_total.get(d_id, 0)
            if cap_left <= 0:
                continue
                
            allocated_qty = min(avail_inv, dem, cap_left)
            if allocated_qty <= 0:
                continue
                
            inv_remaining[b_id] -= allocated_qty
            dest_remaining_demand[key] -= allocated_qty
            dest_allocated_total[d_id] += allocated_qty
            
            # Baseline does not factor smart discounts
            allocations.append({
                "batch_id": b_id,
                "destination_id": d_id,
                "produce": produce,
                "allocated_qty_kg": allocated_qty,
                "travel_time_days": d_row["effective_travel_time"],
                "shelf_life_days": shelf_life,
                "transport_cost_per_kg": d_row["transport_cost_per_kg"],
                "selling_price_per_kg": d_row["selling_price"],
                "discount_pct": 0.0,
                "reason": "Baseline FIFO allocation"
            })
            
    alloc_df = pd.DataFrame(allocations)
    if alloc_df.empty:
        alloc_df = pd.DataFrame(columns=["batch_id", "destination_id", "produce", "allocated_qty_kg", "travel_time_days", "shelf_life_days", "transport_cost_per_kg", "selling_price_per_kg", "discount_pct", "reason"])
    return alloc_df, inv_remaining, dest_remaining_demand

# -----------------------------------------------------------------------------
# 3. METRIC CALCULATIONS
# -----------------------------------------------------------------------------

def calculate_metrics(inv_df, dest_df, alloc_df, inv_remaining_dict, demand_multiplier=1.0):
    initial_inventory = inv_df["quantity_kg"].sum()
    total_demand = (dest_df["demand_kg"] * demand_multiplier).sum()

    qty_dispatched = (
        alloc_df["allocated_qty_kg"].sum()
        if not alloc_df.empty else 0.0
    )

    # A shipment is feasible if it can arrive before its shelf life ends.
    if not alloc_df.empty:
        arrival_feasible = (
            alloc_df["travel_time_days"] < alloc_df["shelf_life_days"]
        )
        feasible_allocations = alloc_df[arrival_feasible]
        at_risk_allocations = alloc_df[~arrival_feasible]

        qty_delivered = feasible_allocations["allocated_qty_kg"].sum()
        qty_at_expiry_risk = at_risk_allocations["allocated_qty_kg"].sum()

        # Costs are incurred for every dispatched allocation.
        transport_costs = (
            alloc_df["allocated_qty_kg"]
            * alloc_df["transport_cost_per_kg"]
        ).sum()

        # Count revenue only for quantities estimated to arrive in time.
        gross_revenue = (
            feasible_allocations["allocated_qty_kg"]
            * feasible_allocations["selling_price_per_kg"]
        ).sum()

        discount_amount = (
            feasible_allocations["allocated_qty_kg"]
            * feasible_allocations["selling_price_per_kg"]
            * feasible_allocations["discount_pct"]
        ).sum()
    else:
        qty_delivered = 0.0
        qty_at_expiry_risk = 0.0
        transport_costs = 0.0
        gross_revenue = 0.0
        discount_amount = 0.0

    fulfillment_pct = (
        qty_delivered / total_demand * 100
        if total_demand > 0 else 0.0
    )

    # Remaining stock is unsold, not necessarily expired.
    unsold_inventory = sum(inv_remaining_dict.values())
    spoilage_qty = unsold_inventory
    spoilage_pct = (
        spoilage_qty / initial_inventory * 100
        if initial_inventory > 0 else 0.0
    )

    net_revenue = gross_revenue - discount_amount - transport_costs

    return {
        "initial_inventory": initial_inventory,
        "total_demand": total_demand,
        "qty_dispatched": qty_dispatched,
        "qty_delivered": qty_delivered,
        "qty_at_expiry_risk": qty_at_expiry_risk,
        "fulfillment_pct": fulfillment_pct,
        "spoilage_qty": spoilage_qty,
        "spoilage_pct": spoilage_pct,
        "transport_costs": transport_costs,
        "gross_revenue": gross_revenue,
        "discount_amount": discount_amount,
        "net_revenue": net_revenue
    }


# -----------------------------------------------------------------------------
# 4. STREAMLIT DASHBOARD INTERFACE
# -----------------------------------------------------------------------------
def main():
    st.title("🚛 FreshRoute: Perishable Produce Allocation & Decision Support")
    st.markdown("**Wild Bugs Hackathon | Problem Statement PS03** — Optimizing agricultural supply chain distribution, minimizing spoilage, and maximizing net revenue.")
    
    inv_df, dest_df = load_base_data()
    
    # Sidebar Controls & Scenarios
    st.sidebar.header("🎛️ Scenario Simulation Controls")
    delay_days = st.sidebar.slider("Transportation Delay (Days)", 0, 3, 0, help="Simulates unexpected transit delays across all routes.")
    capacity_mult = st.sidebar.slider("Vehicle Capacity Multiplier", 0.5, 1.5, 1.0, 0.1, help="Adjusts destination and vehicle receiving capacity.")
    demand_mult = st.sidebar.slider("Demand Multiplier", 0.5, 2.0, 1.0, 0.1, help="Scales market demand up or down.")
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Rerun Analysis", type="primary"):
        st.rerun()
        
    # Run Optimization & Baseline
    opt_alloc, opt_inv_rem, opt_dem_rem = run_optimization(inv_df, dest_df, delay_days, capacity_mult, demand_mult)
    base_alloc, base_inv_rem, base_dem_rem = run_baseline(inv_df, dest_df, delay_days, capacity_mult, demand_mult)
    
    opt_metrics = calculate_metrics(inv_df, dest_df, opt_alloc, opt_inv_rem, demand_mult)
    base_metrics = calculate_metrics(inv_df, dest_df, base_alloc, base_inv_rem, demand_mult)
    
    # Urgent Batch Warnings
    urgent_batches = inv_df[inv_df["shelf_life_days"] <= 2]
    if not urgent_batches.empty:
        st.warning(f"⚠️ **Urgent Alert:** {len(urgent_batches)} inventory batch(es) have a shelf life of 2 days or less! Prioritized in optimized allocation with dynamic discounting.")

    # Tabs for Organization
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Performance Dashboard", "📦 Inventory & Destinations", "🚚 Allocation & Decisions", "📈 Baseline Comparison", "ℹ️ Documentation & Metrics"])
    
    with tab1:
        st.subheader("Executive Summary Metrics")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Net Revenue", f"${opt_metrics['net_revenue']:,.2f}", f"${opt_metrics['net_revenue'] - base_metrics['net_revenue']:,.2f} vs Baseline")
        col2.metric("Demand Fulfillment", f"{opt_metrics['fulfillment_pct']:.1f}%", f"{opt_metrics['fulfillment_pct'] - base_metrics['fulfillment_pct']:+.1f}%")
        col3.metric("Estimated Spoilage", f"{opt_metrics['spoilage_qty']:,.0f} kg", f"{opt_metrics['spoilage_pct']:.1f}%")
        col4.metric("Transport Costs", f"${opt_metrics['transport_costs']:,.2f}")
        
        st.markdown("---")
        
        # Visual Comparison Charts
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.markdown("### Financial Performance Comparison")
            fin_df = pd.DataFrame({
                "Metric": ["Gross Revenue", "Discounts", "Transport Costs", "Net Revenue"],
                "Baseline": [base_metrics["gross_revenue"], base_metrics["discount_amount"], base_metrics["transport_costs"], base_metrics["net_revenue"]],
                "Optimized": [opt_metrics["gross_revenue"], opt_metrics["discount_amount"], opt_metrics["transport_costs"], opt_metrics["net_revenue"]]
            })
            fig_fin = px.bar(fin_df, x="Metric", y=["Baseline", "Optimized"], barmode="group", title="Revenue & Cost Breakdown ($)")
            st.plotly_chart(fig_fin, use_container_width=True)
            
        with col_chart2:
            st.markdown("### Volume Allocation Comparison")
            vol_df = pd.DataFrame({
                "Category": ["Initial Inventory", "Dispatched", "Spoilage / Unsold"],
                "Baseline": [base_metrics["initial_inventory"], base_metrics["qty_dispatched"], base_metrics["spoilage_qty"]],
                "Optimized": [opt_metrics["initial_inventory"], opt_metrics["qty_dispatched"], opt_metrics["spoilage_qty"]]
            })
            fig_vol = px.bar(vol_df, x="Category", y=["Baseline", "Optimized"], barmode="group", title="Volume Metrics (KG)")
            st.plotly_chart(fig_vol, use_container_width=True)

    with tab2:
        st.subheader("Inventory Batches")
        st.dataframe(inv_df, use_container_width=True)
        
        st.subheader("Destination Demands & Capacities")
        st.dataframe(dest_df, use_container_width=True)

    with tab3:
        st.subheader("Optimized Allocation Decisions")
        if not opt_alloc.empty:
            st.dataframe(opt_alloc, use_container_width=True)
        else:
            st.info("No valid allocations made under current constraints (e.g. transit delays exceeding shelf life).")
            
        st.subheader("Discount Recommendations for At-Risk Produce")
        at_risk = opt_alloc[opt_alloc["discount_pct"] > 0]
        if not at_risk.empty:
            st.dataframe(at_risk[["batch_id", "produce", "destination_id", "allocated_qty_kg", "shelf_life_days", "discount_pct"]], use_container_width=True)
        else:
            st.success("No active discount recommendations required for current allocations.")
    with tab4:
        st.subheader("Baseline vs. Optimized Side-by-Side Table")

        comparison_df = pd.DataFrame({
            "Metric": [
                "Initial Inventory (kg)",
                "Total Demand (kg)",
                "Quantity Dispatched (kg)",
                "Quantity Delivered (kg)",
                "Quantity at Expiry Risk (kg)",
                "Demand Fulfillment (%)",
                "Unsold Inventory (kg)",
                "Unsold Inventory (%)",
                "Gross Revenue ($)",
                "Discount Amount ($)",
                "Transport Costs ($)",
                "Net Revenue ($)"
            ],
            "Baseline (FIFO)": [
                base_metrics["initial_inventory"],
                base_metrics["total_demand"],
                base_metrics["qty_dispatched"],
                base_metrics["qty_delivered"],
                base_metrics["qty_at_expiry_risk"],
                base_metrics["fulfillment_pct"],
                base_metrics["spoilage_qty"],
                base_metrics["spoilage_pct"],
                base_metrics["gross_revenue"],
                base_metrics["discount_amount"],
                base_metrics["transport_costs"],
                base_metrics["net_revenue"]
            ],
            "Optimized (FreshRoute)": [
                opt_metrics["initial_inventory"],
                opt_metrics["total_demand"],
                opt_metrics["qty_dispatched"],
                opt_metrics["qty_delivered"],
                opt_metrics["qty_at_expiry_risk"],
                opt_metrics["fulfillment_pct"],
                opt_metrics["spoilage_qty"],
                opt_metrics["spoilage_pct"],
                opt_metrics["gross_revenue"],
                opt_metrics["discount_amount"],
                opt_metrics["transport_costs"],
                opt_metrics["net_revenue"]
            ]
        })

        st.dataframe(
            comparison_df,
            hide_index=True,
            width="stretch"
        )


        

        st.subheader("Metric Definitions")
        st.markdown("""
        - **Demand Fulfillment Percentage:** Quantity Delivered / Total Demand × 100
        - **Unsold Inventory Percentage:** Unsold Inventory / Initial Inventory × 100
        - **Net Revenue:** Gross Revenue − Discount Amount − Transport Costs
        - **Quantity at Expiry Risk:** Quantity allocated to shipments whose travel time is greater than or equal to shelf life.
        """)


if __name__ == "__main__":
    main()