"""
Clean server with working agent endpoints (mock version)
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
from typing import List, Dict, Any, Optional
import json
import os
import asyncio
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

from models import (
    SimulationRequest, SimulationResponse, Scenario, Customer,
    WeeklySimulationRequest, WeeklySimulationResponse, SystemConfiguration,
    AutoRunRequest, AutoRunSession, AutoRunStatusResponse, AutoRunCompleteResponse,
    WeeklyAutoRunResult, MultiWeekAnalysis, WeeklySuccessRates,
    CustomerTierDistribution, MonthlyRevenue, InterventionCosts
)
from simulator import RetentionSimulator, WeeklySimulator
from agent_integration import CognitiveAgentSimulator, CorporateAgentSimulator
from game_master_integration import GameMasterSimulator

# Team registry - avoid circular import by defining here
AVAILABLE_TEAMS = {
    "cognitive": CognitiveAgentSimulator,
    "corporate": CorporateAgentSimulator,
}

# Initialize simulators
simulator = RetentionSimulator()
weekly_simulator = WeeklySimulator(SystemConfiguration())

# Initialize team simulators on first use
team_simulators = {}

# Game Master simulator for AutoRun sessions
game_master = None

# Active AutoRun sessions
active_autorun_sessions = {}

# Data directory path
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
AUTORUN_SESSIONS_DIR = DATA_DIR / "autorun_sessions"
AUTORUN_SESSIONS_DIR.mkdir(exist_ok=True)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    global team_simulators, game_master
    
    # Startup
    print("Starting Telco Retention Dashboard API...")
    print("Initializing retention simulator...")
    await simulator.initialize()
    print("Cognitive simulator ready")
    
    # Initialize Game Master for AutoRun sessions
    try:
        print("Initializing Game Master...")
        game_master = GameMasterSimulator()
        print("✅ Game Master ready for AutoRun sessions")
    except Exception as e:
        print(f"⚠️ Game Master initialization failed: {e}")
        print("AutoRun functionality will be disabled")
    
    # Pre-initialize all team simulators in parallel
    print("Pre-initializing all agent teams...")
    initialization_tasks = []
    for team_type, simulator_class in AVAILABLE_TEAMS.items():
        print(f"  Initializing {team_type} team...")
        initialization_tasks.append(asyncio.create_task(
            asyncio.to_thread(simulator_class)
        ))
    
    if initialization_tasks:
        team_names = list(AVAILABLE_TEAMS.keys())
        initialized_simulators = await asyncio.gather(*initialization_tasks, return_exceptions=True)
        
        for i, team_name in enumerate(team_names):
            if isinstance(initialized_simulators[i], Exception):
                print(f"  ❌ Failed to initialize {team_name}: {initialized_simulators[i]}")
            else:
                team_simulators[team_name] = initialized_simulators[i]
                print(f"  ✅ {team_name} team ready")
    
    print(f"🎯 {len(team_simulators)} agent teams pre-initialized and ready")
    print("\nAvailable endpoints:")
    print("  GET  /api/health")
    print("  POST /simulate/week - Rule-based simulation")
    print("  POST /teams/{team_type}/decide - Team-specific decisions")
    print("  POST /simulate/compare - Multi-team comparison (PARALLEL)")
    print("  POST /simulate/parallel - Legacy parallel comparison (cognitive vs rule-based)")
    print("  POST /agent/decide - Legacy cognitive agent endpoint")
    
    yield
    
    # Shutdown (if needed)
    print("Shutting down Telco Retention Dashboard API...")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Telco Retention Dashboard API",
    description="API for telco customer retention simulation with cognitive agents",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Telco Retention API", "version": "2.0.0"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    print(f"DEBUG: AVAILABLE_TEAMS in health check: {AVAILABLE_TEAMS}")
    print(f"DEBUG: AVAILABLE_TEAMS keys: {list(AVAILABLE_TEAMS.keys()) if AVAILABLE_TEAMS else 'NONE'}")
    
    return {
        "status": "healthy",
        "service": "telco-retention-api",
        "features": {
            "weekly_simulation": True,
            "team_based_simulation": True,
            "multi_team_comparison": True,
            "available_teams": list(AVAILABLE_TEAMS.keys()) if AVAILABLE_TEAMS else [],
            "cors_enabled": True
        }
    }

@app.post("/simulate/week", response_model=WeeklySimulationResponse)
async def run_weekly_simulation(request: WeeklySimulationRequest):
    """Run weekly telco retention simulation with rule-based logic"""
    try:
        # Validate week number
        if request.current_week < 1 or request.current_week > 52:
            raise HTTPException(status_code=400, detail="Week number must be between 1 and 52")
        
        # Create fresh simulator with current system configuration for mid-stream parameter changes
        current_simulator = WeeklySimulator(request.system_config or SystemConfiguration())
        
        # Run the weekly simulation
        results = current_simulator.run_weekly_simulation(request)
        return results
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Weekly simulation error: {str(e)}")

@app.post("/agent/decide")
async def get_agent_decision(request: WeeklySimulationRequest):
    """Get cognitive agent decision for retention strategy"""
    global agent_simulator
    try:
        # Initialize agent simulator on first use
        if agent_simulator is None:
            agent_simulator = CognitiveAgentSimulator()
        
        # Step 1: Get cognitive agent allocation decisions only - using TEAM-SPECIFIC history
        agent_decision = await team_simulators["cognitive"].get_agent_decision(
            customers_at_risk=request.customers_at_risk,
            weekly_budget=request.weekly_budget,
            success_rates=request.success_rates.model_dump(),
            history=request.simulation_history if hasattr(request, 'simulation_history') else [],
            intervention_costs=request.intervention_costs,
            system_config=request.system_config,
        )
        
        # Step 2: Run simulation with agent allocations
        current_simulator = WeeklySimulator(request.system_config or SystemConfiguration())
        agent_request = WeeklySimulationRequest(
            current_week=request.current_week,
            customers_at_risk=request.customers_at_risk,
            weekly_budget=request.weekly_budget,
            success_rates=request.success_rates,
            intervention_costs=request.intervention_costs,
            system_config=request.system_config,
            allocations=agent_decision["allocations"]
        )
        result = current_simulator.run_weekly_simulation(agent_request)
        
        # Use conversation as the reasoning - no separate summary needed
        
        return {
            **result.model_dump(),
            "allocation_decisions": agent_decision["allocations"],
            "reasoning_summary": "See team conversation for full analysis",
            "conversation_log": agent_decision["conversation"],
            "adapted_success_rates": agent_decision.get("adapted_rates", request.success_rates.model_dump()),
            "processing_time_ms": 850,
            "agent_reasoning": {
                "summary": "See team conversation for full analysis",
                "conversation": agent_decision["conversation"],
                "adapted_success_rates": agent_decision.get("adapted_rates", request.success_rates.model_dump())
            }
        }
    except Exception as e:
        import traceback
        print(f"Agent decision error: {e}")
        print(f"Full traceback: {traceback.format_exc()}")
        # Fallback to rule-based
        result = weekly_simulator.run_weekly_simulation(request)
        
        return {
            **result.model_dump(),
            "allocation_decisions": {
                "discount_20": int(request.customers_at_risk * 0.5),
                "discount_30": int(request.customers_at_risk * 0.2),
                "priority_fix": int(request.customers_at_risk * 0.2),
                "executive_escalation": int(request.customers_at_risk * 0.1)
            },
            "reasoning_summary": "Using optimized rule-based approach (agents unavailable)",
            "conversation_log": [
                {"agent": "System", "message": "Cognitive agents unavailable, using optimized rules"}
            ],
            "adapted_success_rates": request.success_rates.model_dump(),
            "processing_time_ms": 100,
            "agent_reasoning": {
                "summary": "Using optimized rule-based approach",
                "conversation": [
                    {"agent": "System", "message": "Cognitive agents unavailable, using optimized rules"}
                ],
                "adapted_success_rates": request.success_rates.model_dump()
            }
        }

@app.post("/teams/{team_type}/decide")
async def get_team_decision(team_type: str, request: WeeklySimulationRequest):
    """Get decision from specified agent team type"""
    global team_simulators
    
    try:
        # Check if team type is available
        if team_type not in AVAILABLE_TEAMS:
            available_teams = list(AVAILABLE_TEAMS.keys())
            raise HTTPException(
                status_code=404, 
                detail=f"Team type '{team_type}' not found. Available teams: {available_teams}"
            )
        
        # Initialize team simulator on first use
        if team_type not in team_simulators:
            print(f"Initializing {team_type} team simulator...")
            team_simulators[team_type] = AVAILABLE_TEAMS[team_type]()
        
        # Get team decision using TEAM-SPECIFIC history
        team_decision = await team_simulators[team_type].get_agent_decision(
            customers_at_risk=request.customers_at_risk,
            weekly_budget=request.weekly_budget,
            success_rates=request.success_rates.model_dump(),
            history=request.simulation_history if hasattr(request, 'simulation_history') else [],
            intervention_costs=request.intervention_costs,
            system_config=request.system_config,
        )
        
        # Run simulation with team allocations
        current_simulator = WeeklySimulator(request.system_config or SystemConfiguration())
        team_request = WeeklySimulationRequest(
            current_week=request.current_week,
            customers_at_risk=request.customers_at_risk,
            weekly_budget=request.weekly_budget,
            success_rates=request.success_rates,
            intervention_costs=request.intervention_costs,
            system_config=request.system_config,
            allocations=team_decision["allocations"]
        )
        result = current_simulator.run_weekly_simulation(team_request)
        
        # Use conversation as the reasoning - no separate summary needed
        
        return {
            **result.model_dump(),
            "team_type": team_type,
            "allocation_decisions": team_decision["allocations"],
            "reasoning_summary": "See team conversation for full analysis",
            "conversation_log": team_decision["conversation"],
            "adapted_success_rates": team_decision.get("adapted_rates", request.success_rates.model_dump()),
            "processing_time_ms": 850,
            "agent_reasoning": {
                "summary": "See team conversation for full analysis",
                "conversation": team_decision["conversation"],
                "adapted_success_rates": team_decision.get("adapted_rates", request.success_rates.model_dump())
            }
        }
    except Exception as e:
        import traceback
        print(f"{team_type.title()} team decision error: {e}")
        print(f"Full traceback: {traceback.format_exc()}")
        # Fallback to rule-based
        result = weekly_simulator.run_weekly_simulation(request)
        
        return {
            **result.model_dump(),
            "team_type": team_type,
            "allocation_decisions": {
                "discount_20": int(request.customers_at_risk * 0.5),
                "discount_30": int(request.customers_at_risk * 0.2),
                "priority_fix": int(request.customers_at_risk * 0.2),
                "executive_escalation": int(request.customers_at_risk * 0.1)
            },
            "reasoning_summary": f"Using optimized rule-based approach ({team_type} team unavailable)",
            "conversation_log": [
                {"agent": "System", "message": f"{team_type.title()} team unavailable, using optimized rules"}
            ],
            "adapted_success_rates": request.success_rates.model_dump(),
            "processing_time_ms": 100,
            "agent_reasoning": {
                "summary": f"Using optimized rule-based approach ({team_type} team unavailable)",
                "conversation": [
                    {"agent": "System", "message": f"{team_type.title()} team unavailable, using optimized rules"}
                ],
                "adapted_success_rates": request.success_rates.model_dump()
            }
        }

@app.post("/simulate/compare") 
async def run_multi_team_comparison(sim_request: WeeklySimulationRequest):
    """Run comparison across multiple teams plus rule-based baseline"""
    print(f"📊 RECEIVED /simulate/compare request for week {sim_request.current_week}")
    global team_simulators
    
    # Re-enabled agent teams for testing
    teams = list(AVAILABLE_TEAMS.keys())  # Use all available teams
    
    # Validate requested teams
    invalid_teams = [team for team in teams if team not in AVAILABLE_TEAMS]
    if invalid_teams:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid teams: {invalid_teams}. Available teams: {list(AVAILABLE_TEAMS.keys())}"
        )
    
    print(f"DEBUG: Starting multi-team comparison for week {sim_request.current_week} with teams: {teams}")
    
    try:
        results = {}
        
        # Always include rule-based as baseline
        rule_based_simulator = WeeklySimulator(sim_request.system_config or SystemConfiguration())
        results["rule_based"] = rule_based_simulator.run_weekly_simulation(sim_request)
        
        # Ensure all team simulators are initialized (should be done at startup)
        for team_type in teams:
            if team_type not in team_simulators:
                print(f"⚠️ Late initialization of {team_type} team simulator...")
                team_simulators[team_type] = AVAILABLE_TEAMS[team_type]()
        
        # Create parallel tasks for all teams
        async def process_team(team_type):
            import time
            start_time = time.time()
            try:
                print(f"🧠 Starting {team_type} team analysis...")
                
                # Get team decision using TEAM-SPECIFIC history from request
                team_history = []
                if hasattr(sim_request, 'team_histories') and sim_request.team_histories:
                    team_history = sim_request.team_histories.get(team_type, [])
                
                team_decision = await team_simulators[team_type].get_agent_decision(
                    customers_at_risk=sim_request.customers_at_risk,
                    weekly_budget=sim_request.weekly_budget,
                    success_rates=sim_request.success_rates.model_dump(),
                    history=team_history,  # Use team's specific history only
                    intervention_costs=sim_request.intervention_costs,
                    system_config=sim_request.system_config
                )
                
                # Run simulation with team allocations
                team_simulator = WeeklySimulator(sim_request.system_config or SystemConfiguration())
                team_request = WeeklySimulationRequest(
                    current_week=sim_request.current_week,
                    customers_at_risk=sim_request.customers_at_risk,
                    weekly_budget=sim_request.weekly_budget,
                    success_rates=sim_request.success_rates,
                    intervention_costs=sim_request.intervention_costs,
                    system_config=sim_request.system_config,
                    allocations=team_decision["allocations"]
                )
                team_result = team_simulator.run_weekly_simulation(team_request)
                
                # Calculate actual processing time
                processing_time_ms = int((time.time() - start_time) * 1000)
                print(f"✅ {team_type} team completed in {processing_time_ms}ms!")
                
                return team_type, {
                    **team_result.model_dump(),
                    "allocation_decisions": team_decision["allocations"],
                    "reasoning_summary": "See team conversation for full analysis",
                    "conversation_log": team_decision.get("conversation", []),
                    "adapted_success_rates": team_decision.get("adapted_rates", sim_request.success_rates.model_dump()),
                    "processing_time_ms": processing_time_ms
                }
            except Exception as e:
                print(f"❌ {team_type} team failed: {e}")
                raise
        
        # Run all teams in parallel with timeout
        print(f"🚀 Running {len(teams)} teams in parallel...")
        team_tasks = [process_team(team_type) for team_type in teams]
        
        # Add 2-minute timeout to prevent hanging
        try:
            team_results_list = await asyncio.wait_for(
                asyncio.gather(*team_tasks, return_exceptions=True), 
                timeout=120  # 2 minute timeout
            )
        except asyncio.TimeoutError:
            print("❌ Team execution timed out after 2 minutes")
            # Cancel any running tasks
            for task in team_tasks:
                if not task.done():
                    task.cancel()
            raise HTTPException(status_code=408, detail="Team execution timed out")
        
        # Process results
        for i, result in enumerate(team_results_list):
            if isinstance(result, Exception):
                print(f"❌ Team {teams[i]} failed with exception: {result}")
                continue
            
            team_type, team_data = result
            results[team_type] = team_data
        
        return {
            "week": sim_request.current_week,
            "teams_compared": ["rule_based"] + teams,
            "results": results,
            "comparison_summary": {
                "total_teams": len(results),
                "timestamp": "2024-01-01T00:00:00Z"  # Would be datetime.now() in production
            }
        }
        
    except Exception as e:
        print(f"DEBUG: Multi-team comparison error occurred: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback to rule-based only
        rule_based = weekly_simulator.run_weekly_simulation(sim_request)
        
        return {
            "week": sim_request.current_week,
            "teams_compared": ["rule_based"],
            "results": {
                "rule_based": rule_based.model_dump()
            },
            "comparison_summary": {
                "total_teams": 1,
                "error": "Multi-team comparison failed, showing rule-based only",
                "timestamp": "2024-01-01T00:00:00Z"
            }
        }

@app.post("/simulate/parallel")
async def run_parallel_simulation(request: WeeklySimulationRequest):
    """Run parallel comparison of rule-based vs cognitive agents (legacy endpoint)"""
    global team_simulators
    print(f"DEBUG: Starting legacy parallel simulation for week {request.current_week}")
    try:
        # Initialize cognitive simulator on first use for backward compatibility
        if "cognitive" not in team_simulators:
            team_simulators["cognitive"] = AVAILABLE_TEAMS["cognitive"]()
        
        # Create fresh simulators with current system configuration for mid-stream parameter changes
        rule_based_simulator = WeeklySimulator(request.system_config or SystemConfiguration())
        agent_based_simulator = WeeklySimulator(request.system_config or SystemConfiguration())
            
        # Run rule-based
        rule_based = rule_based_simulator.run_weekly_simulation(request)
        
        # Step 1: Get cognitive agent allocation decisions only - using TEAM-SPECIFIC history
        agent_decision = await team_simulators["cognitive"].get_agent_decision(
            customers_at_risk=request.customers_at_risk,
            weekly_budget=request.weekly_budget,
            success_rates=request.success_rates.model_dump(),
            history=request.simulation_history if hasattr(request, 'simulation_history') else [],
            intervention_costs=request.intervention_costs,
            system_config=request.system_config,
        )
        
        print(f"DEBUG: Agent allocations being sent to simulator: {agent_decision['allocations']}")
        
        # Step 2: Run agent-based simulation with agent allocations
        agent_request = WeeklySimulationRequest(
            current_week=request.current_week,
            customers_at_risk=request.customers_at_risk,
            weekly_budget=request.weekly_budget,
            success_rates=request.success_rates,
            intervention_costs=request.intervention_costs,
            system_config=request.system_config,
            allocations=agent_decision["allocations"]
        )
        agent_based = agent_based_simulator.run_weekly_simulation(agent_request)
        
        # Use conversation as the reasoning - no separate summary needed
        
        print(f"DEBUG: Agent simulation result - Budget spent: £{agent_based.budget_spent}, Customers saved: {agent_based.customers_saved.basic + agent_based.customers_saved.standard + agent_based.customers_saved.premium + agent_based.customers_saved.enterprise}, CLV protected: £{agent_based.clv_protected}")
        
        
        return {
            "week": sim_request.current_week,
            "rule_based_result": rule_based.model_dump(),
            "agent_based_result": agent_based.model_dump(),
            "agent_decision_data": {
                "reasoning_summary": "See team conversation for full analysis",
                "processing_time_ms": 850,
                "conversation_log": agent_decision.get("conversation", []),
                "allocation_decisions": agent_decision["allocations"],
                "adapted_success_rates": agent_decision.get("adapted_rates", request.success_rates.model_dump())
            },
            "agent_reasoning": {
                "summary": "See team conversation for full analysis",
                "processing_time": 850,
                "confidence": 0.85,
                "conversation": agent_decision.get("conversation", [])[:3]
            }
        }
    except Exception as e:
        print(f"DEBUG: Parallel simulation error occurred: {e}")
        import traceback
        traceback.print_exc()
        # Fallback to rule-based comparison
        rule_based = weekly_simulator.run_weekly_simulation(request)
        agent_based = weekly_simulator.run_weekly_simulation(request)
        
        # Calculate comparison metrics for fallback
        clv_difference = agent_based.clv_protected - rule_based.clv_protected
        agent_customers_total = (agent_based.customers_saved.basic + agent_based.customers_saved.standard + 
                               agent_based.customers_saved.premium + agent_based.customers_saved.enterprise)
        rule_customers_total = (rule_based.customers_saved.basic + rule_based.customers_saved.standard + 
                              rule_based.customers_saved.premium + rule_based.customers_saved.enterprise)
        customers_difference = agent_customers_total - rule_customers_total
        
        return {
            "week": sim_request.current_week,
            "rule_based_result": rule_based.model_dump(),
            "agent_based_result": agent_based.model_dump(),
            "agent_decision_data": {
                "reasoning_summary": "Using optimized heuristics (agents unavailable)",
                "processing_time_ms": 100,
                "conversation_log": [{"agent": "System", "message": "Fallback to rule-based optimization"}],
                "allocation_decisions": {
                    "discount_20": int(request.customers_at_risk * 0.5),
                    "discount_30": int(request.customers_at_risk * 0.2),
                    "priority_fix": int(request.customers_at_risk * 0.2),
                    "executive_escalation": int(request.customers_at_risk * 0.1)
                },
                "adapted_success_rates": request.success_rates.model_dump()
            },
            "agent_reasoning": {
                "summary": "Using optimized heuristics (agents unavailable)",
                "processing_time": 850,
                "confidence": 0.85
            }
        }

# AutoRun Simulation Endpoints

@app.post("/simulate/autorun", response_model=AutoRunSession)
async def start_autorun_simulation(request: AutoRunRequest):
    """Start a 5-week Game Master orchestrated simulation"""
    global game_master, active_autorun_sessions
    
    if game_master is None:
        raise HTTPException(status_code=503, detail="Game Master not available")
    
    # Create session
    session_id = str(uuid.uuid4())
    session = AutoRunSession(
        session_id=session_id,
        session_name=request.session_name,
        status="starting",
        current_week=0,
        total_weeks=5
    )
    
    active_autorun_sessions[session_id] = {
        "session": session,
        "request": request,
        "weekly_results": [],
        "task": None
    }
    
    # Start background task
    task = asyncio.create_task(run_autorun_simulation_background(session_id))
    active_autorun_sessions[session_id]["task"] = task
    
    print(f"🎮 Started AutoRun simulation session: {session_id}")
    return session

@app.get("/simulate/autorun/{session_id}/status", response_model=AutoRunStatusResponse)
async def get_autorun_status(session_id: str):
    """Get current status of AutoRun simulation"""
    if session_id not in active_autorun_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = active_autorun_sessions[session_id]
    session = session_data["session"]
    
    # Check if task is complete
    task = session_data.get("task")
    if task and task.done():
        if task.exception():
            session.status = "failed"
            session.error_message = str(task.exception())
        else:
            session.status = "completed"
            session.completed_at = datetime.now()
    
    # Estimate time remaining (rough estimate: 30 seconds per week)
    remaining_weeks = 5 - session.current_week
    estimated_time_remaining = remaining_weeks * 30 if remaining_weeks > 0 else 0
    
    # Include current week progress if available
    current_week_progress = None
    current_week_parameters = session_data.get("current_week_parameters")
    if current_week_parameters:
        current_week_progress = {
            "week": session.current_week,
            "game_master_parameters": current_week_parameters,
            "status": "processing"
        }
    
    return AutoRunStatusResponse(
        session=session,
        completed_weeks=session_data["weekly_results"],
        current_week_progress=current_week_progress,
        estimated_time_remaining=estimated_time_remaining
    )

@app.get("/simulate/autorun/{session_id}/complete", response_model=AutoRunCompleteResponse)
async def get_autorun_complete(session_id: str):
    """Get complete results when AutoRun simulation finishes"""
    if session_id not in active_autorun_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = active_autorun_sessions[session_id]
    session = session_data["session"]
    
    if session.status != "completed":
        raise HTTPException(status_code=400, detail="Session not yet completed")
    
    # Generate final analysis
    weekly_results = session_data["weekly_results"]
    
    # Create multi-week analysis
    final_analysis = await generate_final_analysis(session_id, weekly_results)
    
    # Save session data to file
    data_file_path = await save_session_data(session_id, weekly_results, final_analysis)
    
    return AutoRunCompleteResponse(
        session=session,
        weekly_results=weekly_results,
        final_analysis=final_analysis,
        data_file_path=data_file_path
    )

async def run_autorun_simulation_background(session_id: str):
    """Background task to run the 5-week simulation"""
    global game_master, active_autorun_sessions
    
    session_data = active_autorun_sessions[session_id]
    session = session_data["session"]
    request = session_data["request"]
    
    try:
        session.status = "running"
        historical_data = []
        
        for week in range(1, 6):  # Run full 5-week simulation
            print(f"🎮 AutoRun {session_id}: Processing Week {week}")
            session.current_week = week
            
            week_start_time = asyncio.get_event_loop().time()
            
            # Step 1: Game Master sets parameters
            parameters = await game_master.set_weekly_parameters(week, historical_data)
            
            # Store current week parameters for immediate frontend display
            session_data["current_week_parameters"] = parameters
            
            # Step 2: Create simulation request from Game Master parameters
            sim_request = create_simulation_request_from_parameters(parameters, week)
            
            # Step 3: Run all teams using working /simulate/compare endpoint
            team_results_response = await run_multi_team_comparison(sim_request)
            team_results = team_results_response["results"]
            
            # Step 4: Game Master evaluates performance - ensure dictionaries
            serialized_results = {}
            for team_name, result in team_results.items():
                if hasattr(result, 'model_dump'):
                    serialized_results[team_name] = result.model_dump()
                else:
                    serialized_results[team_name] = result
            
            # Small delay before Game Master to allow API rate limits to recover
            await asyncio.sleep(3)
            
            evaluation = await game_master.evaluate_weekly_performance(week, serialized_results, parameters)
            
            # Step 5: Create weekly result
            week_end_time = asyncio.get_event_loop().time()
            processing_time = week_end_time - week_start_time
            
            weekly_result = WeeklyAutoRunResult(
                week=week,
                session_id=session_id,
                game_master_parameters=parameters,
                game_master_reasoning=parameters.get("reasoning", ""),
                team_results=team_results,
                game_master_evaluation=evaluation,
                processing_time_seconds=processing_time
            )
            
            session_data["weekly_results"].append(weekly_result)
            
            # Add to historical data for next week - ensure JSON serializable
            serialized_team_results = {}
            for team_name, result in team_results.items():
                if hasattr(result, 'model_dump'):
                    serialized_team_results[team_name] = result.model_dump()
                else:
                    serialized_team_results[team_name] = result
            
            # Add only essential summary data to reduce token usage
            week_summary = {
                "week": week,
                "parameters": {
                    "customers_at_risk": parameters.get("frontend_parameters", {}).get("customers_at_risk"),
                    "weekly_budget_k": parameters.get("frontend_parameters", {}).get("weekly_budget_k"),
                    "business_context": parameters.get("business_context", "")
                },
                "team_performance": {}
            }
            
            # Add only key metrics per team, not full detailed results
            for team_name, result in serialized_team_results.items():
                week_summary["team_performance"][team_name] = {
                    "clv_protected": result.get("clv_protected", 0),
                    "budget_spent": result.get("budget_spent", 0),
                    "customers_saved": sum(result.get("customers_saved", {}).values()),
                    "roi": result.get("clv_protected", 0) / result.get("budget_spent", 1) if result.get("budget_spent", 0) > 0 else 0
                }
            
            if evaluation:
                week_summary["winner"] = evaluation.get("week_winner", "")
                week_summary["week_summary"] = evaluation.get("week_summary", "")
            
            historical_data.append(week_summary)
            
            # Save session data to disk after each week
            try:
                await save_session_data(session_id, session_data["weekly_results"], None)
                print(f"📁 Session data saved for Week {week}")
            except Exception as save_error:
                print(f"⚠️ Failed to save session data: {save_error}")
            
            # Small delay to prevent overwhelming the system
            await asyncio.sleep(1)
        
        session.status = "completed"
        session.completed_at = datetime.now()
        print(f"✅ AutoRun simulation {session_id} completed successfully")
    
    except Exception as e:
        print(f"❌ AutoRun simulation {session_id} failed: {e}")
        session.status = "failed"
        session.error_message = str(e)
        import traceback
        traceback.print_exc()

@app.post("/game-master/set-parameters")
async def game_master_set_parameters(request: Dict[str, Any]):
    """Game Master sets parameters that will be applied to frontend controls"""
    global game_master
    
    if game_master is None:
        raise HTTPException(status_code=503, detail="Game Master not available")
    
    week = request.get("week", 1)
    historical_data = request.get("historical_data", [])
    
    try:
        # Get Game Master parameters using new frontend-compatible format
        parameters = await game_master.set_weekly_parameters(week, historical_data)
        return parameters
        
    except Exception as e:
        print(f"❌ Game Master parameter setting failed: {e}")
        raise HTTPException(status_code=500, detail=f"Game Master failed: {str(e)}")

def create_simulation_request_from_parameters(parameters: Dict[str, Any], week: int) -> WeeklySimulationRequest:
    """Convert Game Master parameters to simulation request"""
    frontend_params = parameters.get("frontend_parameters", {})
    
    # Extract success rates from Game Master parameters
    success_rates = WeeklySuccessRates(
        discount=frontend_params.get("discount_success", 40) / 100,
        priority_fix=frontend_params.get("priority_success", 70) / 100,
        executive_escalation=frontend_params.get("executive_success", 85) / 100
    )
    
    # Create SystemConfiguration from Game Master parameters  
    system_config = SystemConfiguration(
        customer_distribution=CustomerTierDistribution(
            basic=frontend_params.get("basic_percent", 80) / 100,
            standard=frontend_params.get("standard_percent", 15) / 100,
            premium=frontend_params.get("premium_percent", 4) / 100,
            enterprise=frontend_params.get("enterprise_percent", 1) / 100
        ),
        monthly_revenue=MonthlyRevenue(
            basic=frontend_params.get("basic_revenue", 35),
            standard=frontend_params.get("standard_revenue", 65),
            premium=frontend_params.get("premium_revenue", 120),
            enterprise=frontend_params.get("enterprise_revenue", 250)
        ),
        intervention_costs=InterventionCosts(
            discount_duration_months=frontend_params.get("discount_duration", 6),
            priority_fix=frontend_params.get("priority_cost", 250),
            executive_escalation=frontend_params.get("executive_cost", 400)
        )
    )
    
    # Ensure budget is within valid range
    budget = frontend_params.get("weekly_budget_k", 100) * 1000
    if budget > 50000:
        budget = 50000
    elif budget < 5000:
        budget = 5000
    
    return WeeklySimulationRequest(
        customers_at_risk=frontend_params.get("customers_at_risk", 100),
        weekly_budget=budget,
        success_rates=success_rates,
        current_week=week,
        system_config=system_config
    )

# Removed duplicate run_all_teams_for_autorun function - now using /simulate/compare directly

async def generate_final_analysis(session_id: str, weekly_results: List[WeeklyAutoRunResult]) -> MultiWeekAnalysis:
    """Generate comprehensive final analysis"""
    # Extract performance trends
    team_performance_trends = {}
    team_names = ["rule_based", "cognitive", "corporate"]
    
    for team_name in team_names:
        scores = []
        for week_result in weekly_results:
            evaluation = week_result.game_master_evaluation.get("evaluations", {})
            team_eval = evaluation.get(team_name, {})
            score = team_eval.get("overall_score", 5)
            scores.append(score)
        team_performance_trends[team_name] = scores
    
    # Simple ranking based on average scores
    avg_scores = {
        team: sum(scores) / len(scores) if scores else 0
        for team, scores in team_performance_trends.items()
    }
    sorted_teams = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
    rankings = {team: idx + 1 for idx, (team, _) in enumerate(sorted_teams)}
    
    return MultiWeekAnalysis(
        session_id=session_id,
        weeks_analyzed=len(weekly_results),
        team_performance_trends=team_performance_trends,
        adaptation_indicators={},
        overall_rankings=rankings,
        strength_analysis={team: ["Consistent performance"] for team in team_names},
        weakness_analysis={team: ["Room for improvement"] for team in team_names},
        challenging_weeks=[],
        parameter_impact_analysis={},
        game_master_final_report=f"5-week simulation completed. Best performing team: {sorted_teams[0][0]}",
        recommended_approach=sorted_teams[0][0]
    )

async def save_session_data(session_id: str, weekly_results: List[WeeklyAutoRunResult], final_analysis: MultiWeekAnalysis) -> str:
    """Save session data to local files"""
    # Create session directory
    session_dir = DATA_DIR / "autorun_sessions" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Save session summary
    summary_path = session_dir / "session_summary.json"
    summary_data = {
        "session_id": session_id,
        "final_analysis": final_analysis.model_dump(mode='json') if final_analysis else None,
        "total_weeks": len(weekly_results),
        "saved_at": datetime.now().isoformat()
    }
    
    with open(summary_path, 'w') as f:
        json.dump(summary_data, f, indent=2, default=str)
    
    # Save weekly results
    for week_result in weekly_results:
        week_path = session_dir / f"week_{week_result.week:02d}_analysis.json"
        with open(week_path, 'w') as f:
            json.dump(week_result.model_dump(mode='json'), f, indent=2, default=str)
    
    print(f"💾 Saved session data to: {session_dir}")
    return str(summary_path)

@app.get("/simulate/autorun/sessions")
async def list_autorun_sessions():
    """List all completed AutoRun sessions with basic info"""
    sessions = []
    try:
        for session_dir in AUTORUN_SESSIONS_DIR.iterdir():
            if session_dir.is_dir():
                summary_file = session_dir / "session_summary.json"
                if summary_file.exists():
                    try:
                        with open(summary_file, 'r') as f:
                            summary = json.load(f)
                        
                        session_info = {
                            "session_id": summary["session_id"],
                            "total_weeks": summary["total_weeks"],
                            "saved_at": summary["saved_at"],
                            "final_analysis": {
                                "overall_rankings": summary["final_analysis"].get("overall_rankings", {}),
                                "recommended_approach": summary["final_analysis"].get("recommended_approach", "unknown"),
                                "game_master_final_report": summary["final_analysis"].get("game_master_final_report", "No report available")
                            }
                        }
                        sessions.append(session_info)
                    except (json.JSONDecodeError, KeyError) as e:
                        print(f"Error reading session {session_dir.name}: {e}")
                        continue
        
        # Sort by saved_at descending (most recent first)
        sessions.sort(key=lambda x: x["saved_at"], reverse=True)
        return {"sessions": sessions}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing sessions: {str(e)}")

@app.get("/simulate/autorun/sessions/{session_id}/summary")
async def get_session_visual_summary(session_id: str):
    """Get detailed visual summary data for a specific AutoRun session"""
    session_dir = AUTORUN_SESSIONS_DIR / session_id
    
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Load session summary
        summary_file = session_dir / "session_summary.json"
        with open(summary_file, 'r') as f:
            session_summary = json.load(f)
        
        # Load individual week analyses
        week_analyses = []
        for week in range(1, session_summary["total_weeks"] + 1):
            week_file = session_dir / f"week_{week:02d}_analysis.json"
            if week_file.exists():
                with open(week_file, 'r') as f:
                    week_data = json.load(f)
                    week_analyses.append(week_data)
        
        # Extract performance trends for visualization
        team_performance_trends = session_summary["final_analysis"]["team_performance_trends"]
        
        # Calculate weekly totals
        weekly_totals = []
        for week_data in week_analyses:
            week_totals = {
                "week": week_data["week"],
                "customers_at_risk": week_data["game_master_parameters"]["frontend_parameters"]["customers_at_risk"],
                "weekly_budget": week_data["game_master_parameters"]["frontend_parameters"]["weekly_budget_k"] * 1000,
                "business_context": week_data["game_master_parameters"]["business_context"],
                "teams": {}
            }
            
            for team_name, team_result in week_data["team_results"].items():
                # Calculate ROI if not present
                roi = team_result.get("roi", 0)
                if roi == 0 and team_result["budget_spent"] > 0:
                    roi = team_result["clv_protected"] / team_result["budget_spent"]
                
                # Get Game Master evaluation details
                gm_eval = week_data["game_master_evaluation"]["evaluations"][team_name]
                
                week_totals["teams"][team_name] = {
                    "clv_protected": team_result["clv_protected"],
                    "budget_spent": team_result["budget_spent"],
                    "customers_saved": sum(team_result["customers_saved"].values()),
                    "roi": roi,
                    "game_master_score": gm_eval["overall_score"],
                    "game_master_evaluation": {
                        "reasoning": gm_eval.get("reasoning", ""),
                        "strengths": gm_eval.get("strengths", []),
                        "improvements": gm_eval.get("improvements", []),
                        "decision_quality": gm_eval.get("decision_quality", 0),
                        "resource_efficiency": gm_eval.get("resource_efficiency", 0),
                        "adaptability": gm_eval.get("adaptability", 0)
                    }
                }
            
            weekly_totals.append(week_totals)
        
        # Calculate cumulative performance
        cumulative_performance = {}
        for team_name in team_performance_trends.keys():
            cumulative_performance[team_name] = {
                "total_clv_protected": 0,
                "total_budget_spent": 0,
                "total_customers_saved": 0,
                "average_roi": 0,
                "average_score": 0
            }
        
        for week_totals in weekly_totals:
            for team_name, team_data in week_totals["teams"].items():
                if team_name in cumulative_performance:
                    cumulative_performance[team_name]["total_clv_protected"] += team_data["clv_protected"]
                    cumulative_performance[team_name]["total_budget_spent"] += team_data["budget_spent"]
                    cumulative_performance[team_name]["total_customers_saved"] += team_data["customers_saved"]
        
        # Calculate averages
        for team_name in cumulative_performance.keys():
            roi_values = [week["teams"][team_name]["roi"] for week in weekly_totals if team_name in week["teams"]]
            score_values = [week["teams"][team_name]["game_master_score"] for week in weekly_totals if team_name in week["teams"]]
            
            if roi_values:
                cumulative_performance[team_name]["average_roi"] = sum(roi_values) / len(roi_values)
            if score_values:
                cumulative_performance[team_name]["average_score"] = sum(score_values) / len(score_values)
        
        return {
            "session_id": session_id,
            "session_summary": session_summary,
            "team_performance_trends": team_performance_trends,
            "weekly_details": weekly_totals,
            "cumulative_performance": cumulative_performance,
            "overall_rankings": session_summary["final_analysis"]["overall_rankings"],
            "final_analysis": session_summary["final_analysis"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading session summary: {str(e)}")

# Serve dashboard static files
dashboard_path = Path(__file__).parent.parent / "dashboard"
if dashboard_path.exists():
    app.mount("/dashboard", StaticFiles(directory=str(dashboard_path), html=True), name="dashboard")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=False)