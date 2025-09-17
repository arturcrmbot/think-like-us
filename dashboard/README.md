# Telco Retention Dashboard Frontend

Interactive dashboard for the Cognitive AI Architecture for B2C Mobile Carrier Churn Prevention system.

## Quick Start

1. **Start the Backend API** (required):
   ```bash
   cd ../backend
   python start_server.py
   ```
   The API will run on `http://localhost:8000`

2. **Start the Frontend Dashboard**:
   ```bash
   cd dashboard
   python serve.py
   ```
   The dashboard will be available at `http://localhost:8050`

3. **Open your browser** and navigate to:
   `http://localhost:8050/index.html`

## Features

### Control Panel
- **Customers at Risk Slider**: 50-500 customers per week
- **Weekly Budget Slider**: £50k-£500k budget allocation
- **Success Rate Sliders**:
  - Discount Success Rate: 10%-50%
  - Priority Fix Success Rate: 30%-80%
  - Executive Escalation Success Rate: 50%-90%

### Simulation Controls
- **Start Simulation**: Begin 52-week simulation
- **Next Week**: Manual step-through mode
- **Pause/Resume**: Control auto-advance
- **Reset**: Clear all data and restart

### Real-Time Visualization
- **CLV Protected Chart**: Cumulative customer lifetime value saved
- **Budget Remaining Chart**: Track budget consumption over time
- **Weekly Stats**: Current week performance metrics
- **Summary Statistics**: Overall simulation results

### Auto-Advance Feature
- Automatically progresses through weeks every 10 seconds
- Can be paused/resumed at any time
- Visual countdown indicator
- Pauses when browser tab is hidden

## How It Works

1. **Configure Parameters**: Use sliders to set customer risk levels, budget constraints, and success rates
2. **Start Simulation**: Click "Start Simulation" to begin the 52-week simulation
3. **Monitor Progress**: Watch real-time charts and statistics as the simulation progresses
4. **Analyze Results**: Review CLV protection, budget efficiency, and ROI metrics
5. **Adjust Strategy**: Change parameters mid-simulation to see impact on outcomes

## API Integration

The dashboard communicates with the backend API at `http://localhost:8000`:

- `GET /api/health` - API health check
- `POST /simulate/week` - Weekly simulation endpoint

Each week, the dashboard sends:
```json
{
  "customers_at_risk": 100,
  "weekly_budget": 100000,
  "success_rates": {
    "discount": 0.25,
    "priority_fix": 0.65,
    "executive_escalation": 0.75
  },
  "current_week": 1,
  "simulation_history": []
}
```

## Technical Stack

- **Frontend**: Vanilla JavaScript, Chart.js for visualization
- **Styling**: Modern CSS3 with glassmorphism effects
- **API**: RESTful integration with FastAPI backend
- **Server**: Python HTTP server on port 8050

## File Structure

```
dashboard/
├── index.html          # Main dashboard interface
├── app.js              # JavaScript application logic
├── styles.css          # Professional styling and responsive design
├── serve.py            # Python HTTP server for port 8050
└── README.md           # This documentation
```

## Browser Compatibility

- Chrome/Chromium 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## Troubleshooting

### Dashboard won't load
- Ensure the frontend server is running: `python serve.py`
- Check browser console for JavaScript errors
- Verify all files are present in the dashboard directory

### API connection failed
- Ensure backend server is running on port 8000
- Check API health status indicator in top-right corner
- Verify CORS settings allow localhost:8050

### Charts not displaying
- Ensure Chart.js is loading (check browser console)
- Verify canvas elements are present in DOM
- Check for JavaScript errors in browser console

### Simulation errors
- Check that all slider values are within valid ranges
- Ensure API is responding correctly to POST requests
- Review browser network tab for failed requests

## Customization

The dashboard can be customized by modifying:

- **styles.css**: Update colors, fonts, and layout
- **app.js**: Modify simulation logic and API endpoints
- **index.html**: Add new components or modify structure
- **serve.py**: Change port or add custom headers

## Performance

The dashboard is optimized for:
- Real-time updates with minimal lag
- Smooth chart animations
- Responsive design for mobile/tablet
- Efficient API communication
- Memory management for long-running simulations