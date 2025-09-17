# Telco Retention Dashboard API

FastAPI backend for the cognitive AI telco churn prevention dashboard with weekly simulation capabilities.

## Features

- **Weekly Simulation**: Rule-based retention simulation with fresh budget each week
- **Customer Tier Distribution**: 80% Basic, 15% Standard, 4% Premium, 1% Enterprise  
- **Rule-Based Logic**: Automated action assignment based on customer tier
- **CLV Calculation**: Customer Lifetime Value = monthly_value × 12
- **Success Rate Modifiers**: Tier-specific success rate adjustments
- **Budget Constraints**: Automatic action scaling when budget is insufficient
- **CORS Support**: Configured for frontend integration (localhost:8050)

## API Endpoints

### Core Endpoints

- `GET /api/health` - Health check with feature status
- `POST /simulate/week` - Weekly retention simulation
- `GET /api/scenarios` - Available cognitive scenarios
- `POST /api/simulate` - Cognitive team simulation

### Weekly Simulation Endpoint

**POST /simulate/week**

Request body:
```json
{
  "customers_at_risk": 150,
  "weekly_budget": 200000,
  "success_rates": {
    "discount": 0.5,
    "priority_fix": 0.7,
    "executive_escalation": 0.8
  },
  "current_week": 1,
  "simulation_history": []
}
```

Response:
```json
{
  "week": 1,
  "customers_by_tier": {
    "enterprise": 2,
    "premium": 6, 
    "standard": 22,
    "basic": 120
  },
  "actions_taken": {
    "discount_20": 120,
    "discount_30": 22,
    "priority_fix": 6,
    "executive_escalation": 2
  },
  "customers_saved": {
    "basic": 48,
    "standard": 9,
    "premium": 4,
    "enterprise": 1
  },
  "clv_protected": 38520.0,
  "budget_spent": 33400.0,
  "cumulative_clv": 38520.0
}
```

## Business Logic

### Customer Tier Distribution
- **Basic (80%)**: CLV < $1000, Monthly: $45
- **Standard (15%)**: CLV $1000-3000, Monthly: $75  
- **Premium (4%)**: CLV > $3000, Monthly: $120
- **Enterprise (1%)**: CLV > $10000, Monthly: $250

### Rule-Based Action Assignment
- **Basic Customers** → 20% Discount Offer ($200 cost)
- **Standard Customers** → 30% Discount Offer ($400 cost)
- **Premium Customers** → Priority Technical Fix ($800 cost)
- **Enterprise Customers** → Executive Escalation ($1500 cost)

### Success Rate Modifiers
- **Enterprise**: 1.2x (20% boost)
- **Premium**: 1.0x (no change)
- **Standard**: 0.9x (10% reduction)
- **Basic**: 0.8x (20% reduction)

Final success rate = base_success_rate × tier_modifier

### CLV Calculation
Customer Lifetime Value = monthly_spend × 12 months

## Installation & Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the server:
```bash
cd backend
python3 start_server.py
```

Or directly with uvicorn:
```bash
cd backend
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

## Testing

Test the API with curl:

```bash
# Health check
curl http://localhost:8000/api/health

# Weekly simulation
curl -X POST http://localhost:8000/simulate/week \
  -H 'Content-Type: application/json' \
  -d '{
    "customers_at_risk": 150,
    "weekly_budget": 200000,
    "success_rates": {
      "discount": 0.5,
      "priority_fix": 0.7,
      "executive_escalation": 0.8
    },
    "current_week": 1,
    "simulation_history": []
  }'
```

## Validation Rules

### Request Validation
- `customers_at_risk`: 50-500
- `weekly_budget`: $50,000-$500,000
- `current_week`: 1-52
- `success_rates`: All rates between 0.0 and 1.0

### Business Rules
- Fresh budget each week (no carry-over)
- Customer distribution ensures minimum 1 per tier
- Actions scaled proportionally if budget insufficient
- CLV calculated as monthly × 12
- Cumulative CLV tracks across all simulation weeks

## Architecture

- **FastAPI**: Modern, fast web framework
- **Pydantic**: Data validation and serialization
- **CORS**: Cross-origin resource sharing for frontend
- **Modular Design**: Separate simulator and models
- **Rule-Based Logic**: Deterministic customer processing

## Files

- `server.py` - FastAPI application and routes
- `models.py` - Pydantic data models and validation
- `simulator.py` - Retention simulation engines
- `start_server.py` - Server startup script
- `requirements.txt` - Python dependencies

The API is designed to integrate seamlessly with frontend dashboards running on localhost:8050 or other configured origins.