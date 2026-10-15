# 🚛 FreshRoute — Intelligent Distribution Planning for Perishable Produce

FreshRoute is a Python-based decision-support application that helps optimize the distribution of perishable agricultural produce. It compares a basic FIFO (First-In, First-Out) allocation strategy with a greedy optimization approach to support better allocation decisions.

### 🚀 Live Demo

**Try FreshRoute here:** [Launch FreshRoute](https://freshroute-glnnvcyqd4ktmvtrmu6trc.streamlit.app/)


## 🎯 Problem Statement

Perishable agricultural products can lose value when distribution is delayed or inventory is allocated inefficiently. FreshRoute explores how inventory, destination demand, transport capacity, travel time, and shelf life can influence distribution decisions.

## ✨ Features

- **Performance Dashboard:** View key distribution and financial metrics.
- **Inventory Management View:** Explore sample inventory batches and destination demand.
- **FIFO Baseline:** Compare allocation using a basic first-in, first-out approach.
- **Greedy Optimization:** Prioritize inventory with shorter shelf life and destinations with higher estimated margins.
- **Scenario Simulation:** Adjust transportation delays, capacity, and demand.
- **Allocation Decisions:** Inspect allocation quantities and recommendations for discounts on at-risk produce.
- **Visual Comparisons:** Compare baseline and optimized results using charts and tables.

## 🛠️ Technology Stack

- Python
- Streamlit
- Pandas
- NumPy
- Plotly

## 📁 Project Structure

```text
FreshRoute/
├── app.py
├── requirements.txt
├── .gitignore
└── README.md
```

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/luckypathak78/FreshRoute.git
cd FreshRoute
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the environment

**Windows Command Prompt:**

```bash
.venv\Scripts\activate
```

### 4. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 5. Run the application

```bash
streamlit run app.py
```

The application should open in your browser.

## 🧠 How It Works

FreshRoute uses sample inventory and destination data to compare two allocation approaches:

- **FIFO baseline:** Allocates available inventory to matching destinations in the order they appear in the data.
- **Greedy optimization:** Prioritizes batches with shorter shelf life and matching destinations with higher estimated margins, while considering demand, capacity, and whether the produce can arrive before expiry.

The dashboard calculates and compares estimated fulfillment, remaining inventory, transport costs, discounts, and net revenue.

## ⚠️ Limitations

- The current prototype uses predefined sample data.
- The optimization method is a greedy heuristic, not a guaranteed global optimum.
- Results are estimates based on the assumptions and values in the application.
- Remaining unsold inventory is currently counted as spoilage, which may not represent actual expired produce.
- The application does not currently claim live traffic integration or real-world measured waste reduction.

## 🔮 Future Improvements

- Add automated tests for allocation algorithms and metric calculations.
- Improve inventory status tracking to distinguish unsold, dispatched, delivered, and expired produce.
- Add input validation and error handling.
- Support configurable datasets and document their input formats.
- Evaluate the allocation approaches using consistent scenarios.

## 👥 Team Project

Developed as part of the **Wild Bugs Hackathon — Problem Statement PS03**.
