# Multi-Team AI Decision-Making Framework

A framework for comparing different AI decision-making approaches using multi-agent systems. Features parallel team execution with AutoGen SelectorGroupChat and an AI Game Master for automated evaluation.

## Installation

### Prerequisites
- Python 3.9+
- Docker (optional, for containerized deployment)
- Azure OpenAI API access or OpenAI-compatible endpoint

### Quick Start

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/think-like-us.git
cd think-like-us
```

2. **Set up environment**
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API credentials:
# AZURE_OPENAI_API_KEY=your_key
# AZURE_OPENAI_ENDPOINT=your_endpoint
# AZURE_OPENAI_MODEL_NAME=your_model_deployment
# AZURE_OPENAI_API_VERSION=2024-10-01-preview
```

3. **Install dependencies**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

4. **Run the application**
```bash
# Automated launch (opens browser automatically)
./scripts/run_dashboard.sh     # Linux/macOS
./scripts/run_dashboard.ps1    # Windows PowerShell

# Or manually:
python backend/server.py        # Start API (port 8001)
python -m http.server 8050 -d dashboard  # Start web UI (port 8050)
```

Access the dashboard at http://localhost:8050

## Usage

### Web Dashboard
- Configure simulation parameters via the web interface
- Compare three team approaches: Rule-based, Cognitive, and Corporate
- Run manual weekly simulations or automated 5-week evaluations
- View team decision processes and performance metrics

### API Endpoints
- `GET /api/health` - System health check
- `POST /simulate/week` - Run single week simulation
- `POST /simulate/compare` - Compare all teams
- `POST /simulate/autorun` - Start 5-week automated evaluation

## Architecture

```
├── backend/           # FastAPI server and business logic
├── dashboard/         # Web frontend (HTML/JS)
├── agents/           # Multi-agent team definitions
├── scripts/          # Utility and launch scripts
└── tests/            # Test suites
```

### Key Components
- **AutoGen Framework**: Powers multi-agent team collaboration
- **Game Master**: AI evaluator for team performance
- **Parallel Execution**: Teams process simultaneously for efficiency
- **Session Persistence**: Results saved for analysis

## Model Compatibility

- **Recommended**: GPT-5, GPT-5-chat, or latest models for optimal reasoning
- **Compatible**: Any Azure OpenAI or OpenAI-compatible chat model
- Configurable via environment variables

## Docker Deployment

```bash
docker-compose up --build
```

Services available at:
- Dashboard: http://localhost:8050
- API: http://localhost:8001

## License

MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.