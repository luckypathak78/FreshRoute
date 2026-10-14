import pandas as pd
import pytest

from app import run_optimization, run_baseline, calculate_metrics


# ============================================================
# TEST DATA HELPERS
# ============================================================

def make_inventory(
    quantity=10,
    shelf_life=5,
    produce="Tomatoes",
    cost=10.0,
):
    return pd.DataFrame([
        {
            "batch_id": "B1",
            "produce": produce,
            "quantity_kg": quantity,
            "shelf_life_days": shelf_life,
            "cost_per_kg": cost,
        }
    ])


def make_destinations(
    demand=10,
    capacity=10,
    travel_time=2,
    produce="Tomatoes",
    price=20.0,
    transport_cost=2.0,
):
    return pd.DataFrame([
        {
            "destination_id": "D1",
            "name": "Test Destination",
            "produce": produce,
            "demand_kg": demand,
            "selling_price": price,
            "travel_time_days": travel_time,
            "transport_cost_per_kg": transport_cost,
            "max_capacity_kg": capacity,
        }
    ])


# ============================================================
# 1. INVENTORY LIMIT
# ============================================================

def test_inventory_limit():
    inventory = make_inventory(quantity=10)
    destinations = make_destinations(demand=20, capacity=20)

    allocations, remaining, _ = run_optimization(
        inventory, destinations
    )

    allocated = allocations["allocated_qty_kg"].sum()

    assert allocated <= 10
    assert remaining["B1"] >= 0
    assert allocated + remaining["B1"] == pytest.approx(10)


# ============================================================
# 2. DESTINATION DEMAND LIMIT
# ============================================================

def test_destination_demand_limit():
    inventory = make_inventory(quantity=20)
    destinations = make_destinations(demand=5, capacity=20)

    allocations, _, remaining_demand = run_optimization(
        inventory, destinations
    )

    allocated = allocations["allocated_qty_kg"].sum()

    assert allocated <= 5
    assert remaining_demand[("D1", "Tomatoes")] >= 0


# ============================================================
# 3. SHELF-LIFE FEASIBILITY
# ============================================================

def test_shelf_life_feasibility():
    inventory = make_inventory(quantity=10, shelf_life=2)
    destinations = make_destinations(
        demand=10,
        capacity=10,
        travel_time=2,
    )

    allocations, remaining, _ = run_optimization(
        inventory, destinations
    )

    assert allocations.empty
    assert remaining["B1"] == pytest.approx(10)


# ============================================================
# 4. ZERO DEMAND
# ============================================================

def test_zero_demand():
    inventory = make_inventory(quantity=10)
    destinations = make_destinations(demand=0, capacity=10)

    allocations, remaining, remaining_demand = run_optimization(
        inventory, destinations
    )

    assert allocations.empty
    assert remaining["B1"] == pytest.approx(10)
    assert remaining_demand[("D1", "Tomatoes")] == pytest.approx(0)


# ============================================================
# 5. INSUFFICIENT INVENTORY
# ============================================================

def test_insufficient_inventory():
    inventory = make_inventory(quantity=3)
    destinations = make_destinations(demand=10, capacity=10)

    allocations, remaining, remaining_demand = run_optimization(
        inventory, destinations
    )

    allocated = allocations["allocated_qty_kg"].sum()

    assert allocated == pytest.approx(3)
    assert remaining["B1"] == pytest.approx(0)
    assert remaining_demand[("D1", "Tomatoes")] == pytest.approx(7)


# ============================================================
# 6. DELIVERY DELAY
# ============================================================

def test_delivery_delay_makes_route_infeasible():
    inventory = make_inventory(quantity=10, shelf_life=3)
    destinations = make_destinations(
        demand=10,
        capacity=10,
        travel_time=2,
    )

    allocations, _, _ = run_optimization(
        inventory,
        destinations,
        delay_days=1,
    )

    assert allocations.empty


# ============================================================
# 7. TRANSPORTATION CAPACITY
# ============================================================

def test_transportation_capacity():
    inventory = pd.DataFrame([
        {
            "batch_id": "B1",
            "produce": "Tomatoes",
            "quantity_kg": 10,
            "shelf_life_days": 5,
            "cost_per_kg": 10.0,
        },
        {
            "batch_id": "B2",
            "produce": "Tomatoes",
            "quantity_kg": 10,
            "shelf_life_days": 6,
            "cost_per_kg": 12.0,
        },
    ])

    destinations = make_destinations(
        demand=20,
        capacity=7,
    )

    allocations, _, _ = run_optimization(
        inventory, destinations
    )

    allocated = allocations["allocated_qty_kg"].sum()

    assert allocated <= 7
    assert allocated == pytest.approx(7)


# ============================================================
# 8. FINANCIAL AND OPERATIONAL METRICS
# ============================================================

def test_financial_and_operational_metrics():
    inventory = make_inventory(quantity=20)

    destinations = make_destinations(
        demand=20,
        capacity=20,
        price=20.0,
        transport_cost=2.0,
    )

    allocations = pd.DataFrame([
        {
            "batch_id": "B1",
            "destination_id": "D1",
            "produce": "Tomatoes",
            "allocated_qty_kg": 10,
            "travel_time_days": 2,
            "shelf_life_days": 5,
            "transport_cost_per_kg": 2.0,
            "selling_price_per_kg": 20.0,
            "discount_pct": 0.20,
            "reason": "Test allocation",
        }
    ])

    remaining_inventory = {"B1": 10}

    metrics = calculate_metrics(
        inventory,
        destinations,
        allocations,
        remaining_inventory,
    )

    assert metrics["initial_inventory"] == pytest.approx(20)
    assert metrics["total_demand"] == pytest.approx(20)
    assert metrics["qty_dispatched"] == pytest.approx(10)
    assert metrics["qty_delivered"] == pytest.approx(10)
    assert metrics["fulfillment_pct"] == pytest.approx(50)

    # Remaining inventory is the current spoilage proxy.
    assert metrics["spoilage_qty"] == pytest.approx(10)
    assert metrics["spoilage_pct"] == pytest.approx(50)

    assert metrics["gross_revenue"] == pytest.approx(200)
    assert metrics["discount_amount"] == pytest.approx(40)
    assert metrics["transport_costs"] == pytest.approx(20)
    assert metrics["net_revenue"] == pytest.approx(140)


# ============================================================
# 9. ZERO TOTAL DEMAND METRIC
# ============================================================

def test_zero_total_demand_has_zero_fulfillment():
    inventory = make_inventory(quantity=10)
    destinations = make_destinations(
        demand=0,
        capacity=10,
    )

    allocations, remaining, _ = run_optimization(
        inventory, destinations
    )

    metrics = calculate_metrics(
        inventory,
        destinations,
        allocations,
        remaining,
    )

    assert metrics["total_demand"] == pytest.approx(0)
    assert metrics["fulfillment_pct"] == pytest.approx(0)


# ============================================================
# 10. BASELINE SHELF-LIFE REGRESSION TEST
# EXPECTED TO EXPOSE A POTENTIAL BUG IN CURRENT CODE
# ============================================================

def test_baseline_shelf_life_feasibility():
    inventory = make_inventory(quantity=10, shelf_life=2)

    destinations = make_destinations(
        demand=10,
        capacity=10,
        travel_time=2,
    )

    allocations, _, _ = run_baseline(
        inventory, destinations
    )

    assert allocations.empty, (
        "Baseline allocated produce even though travel time "
        "equals shelf life."
    )


# ============================================================
# 11. INDEPENDENT CAPACITY FOR MULTIPLE DESTINATIONS
# ============================================================

def test_capacity_is_tracked_independently_per_destination():
    inventory = make_inventory(quantity=20)

    destinations = pd.DataFrame([
        {
            "destination_id": "D1",
            "name": "Destination 1",
            "produce": "Tomatoes",
            "demand_kg": 20,
            "selling_price": 20.0,
            "travel_time_days": 1,
            "transport_cost_per_kg": 2.0,
            "max_capacity_kg": 5,
        },
        {
            "destination_id": "D2",
            "name": "Destination 2",
            "produce": "Tomatoes",
            "demand_kg": 20,
            "selling_price": 19.0,
            "travel_time_days": 1,
            "transport_cost_per_kg": 2.0,
            "max_capacity_kg": 7,
        },
    ])

    allocations, _, _ = run_optimization(
        inventory, destinations
    )

    allocated_per_destination = (
        allocations.groupby("destination_id")["allocated_qty_kg"].sum()
    )

    assert allocated_per_destination["D1"] <= 5
    assert allocated_per_destination["D2"] <= 7
    assert allocated_per_destination["D1"] == pytest.approx(5)
    assert allocated_per_destination["D2"] == pytest.approx(7)