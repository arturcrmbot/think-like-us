"""
Pydantic models for Telco Retention Dashboard
Defines data structures for API requests/responses and business logic
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import random

class CustomerTier(str, Enum):
    """Customer value tier classification"""
    ENTERPRISE = "enterprise"  # CLV > $10000
    PREMIUM = "premium"       # CLV > $3000
    STANDARD = "standard"     # CLV $1000-3000  
    BASIC = "basic"           # CLV < $1000

class RiskLevel(str, Enum):
    """Customer churn risk level"""
    LOW = "low"           # < 30%
    MEDIUM = "medium"     # 30-60%
    HIGH = "high"         # 60-85%
    CRITICAL = "critical" # > 85%

class InterventionType(str, Enum):
    """Types of retention interventions"""
    DISCOUNT = "discount"
    ESCALATION = "escalation"
    PLAN_CHANGE = "plan_change"
    DEVICE_OFFER = "device_offer"
    ACCOUNT_MANAGEMENT = "account_management"

class Customer(BaseModel):
    """Customer data model"""
    id: str = Field(..., description="Unique customer identifier")
    name: str = Field(..., description="Customer name")
    tier: CustomerTier = Field(..., description="Customer value tier")
    risk_level: RiskLevel = Field(..., description="Churn risk level")
    monthly_spend: float = Field(..., ge=0, description="Monthly spending amount")
    tenure_months: int = Field(..., ge=0, description="Months as customer")
    clv: float = Field(..., ge=0, description="Customer lifetime value")
    usage_pattern: Dict[str, Any] = Field(default_factory=dict, description="Usage metrics")
    support_history: List[Dict[str, Any]] = Field(default_factory=list, description="Support ticket history")
    billing_history: List[Dict[str, Any]] = Field(default_factory=list, description="Billing issue history")
    last_updated: datetime = Field(default_factory=datetime.now)

class Scenario(BaseModel):
    """Simulation scenario definition"""
    id: str = Field(..., description="Unique scenario identifier")
    name: str = Field(..., description="Human-readable scenario name")
    description: str = Field(..., description="Scenario description")
    customer_profile: Dict[str, Any] = Field(..., description="Customer characteristics for scenario")
    expected_outcomes: Dict[str, float] = Field(..., description="Expected success rates")
    tags: List[str] = Field(default_factory=list, description="Scenario tags for filtering")
    created_date: datetime = Field(default_factory=datetime.now)

class CollaborationEntry(BaseModel):
    """Entry in team collaboration log"""
    agent: str = Field(..., description="Agent/role name")
    timestamp: datetime = Field(default_factory=datetime.now)
    message: str = Field(..., description="Agent message/analysis")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

class RetentionAction(BaseModel):
    """Specific retention action"""
    type: InterventionType = Field(..., description="Type of intervention")
    description: str = Field(..., description="Action description")
    cost: float = Field(..., ge=0, description="Estimated cost")
    success_probability: float = Field(..., ge=0, le=1, description="Estimated success rate")
    execution_time_hours: int = Field(..., ge=0, description="Time to execute")

class RetentionStrategy(BaseModel):
    """Complete retention strategy"""
    customer_id: str = Field(..., description="Target customer")
    scenario_id: str = Field(..., description="Associated scenario")
    actions: List[RetentionAction] = Field(..., description="Ordered list of actions")
    total_cost: float = Field(..., ge=0, description="Total strategy cost")
    expected_clv_protection: float = Field(..., ge=0, description="Expected CLV saved")
    roi_estimate: float = Field(..., description="Return on investment estimate")
    confidence_score: float = Field(..., ge=0, le=1, description="Strategy confidence")

class SimulationRequest(BaseModel):
    """Request to run simulation"""
    scenario_id: str = Field(..., description="Scenario to simulate")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Additional parameters")
    include_traditional_comparison: bool = Field(default=True, description="Include traditional approach results")

class SimulationResponse(BaseModel):
    """Simulation results"""
    scenario_id: str = Field(..., description="Simulated scenario")
    simulation_timestamp: datetime = Field(..., description="When simulation was run")
    collaboration_log: List[CollaborationEntry] = Field(..., description="Team collaboration process")
    strategy: Optional[RetentionStrategy] = Field(default=None, description="Recommended strategy")
    metrics: Dict[str, Any] = Field(..., description="Simulation metrics")
    
    # Dashboard-specific fields
    retention_rates: List[float] = Field(..., description="[Cognitive, Traditional] success rates")
    risk_distribution: List[int] = Field(..., description="Risk level distribution counts")
    total_customers: int = Field(..., description="Total customers in simulation")
    at_risk_customers: int = Field(..., description="Customers at risk")
    retention_rate: float = Field(..., description="Overall retention rate")
    clv_protected: float = Field(..., description="Total CLV protected")

class AnalyticsSummary(BaseModel):
    """Dashboard analytics summary"""
    total_customers: int = Field(..., description="Total customer count")
    at_risk_customers: int = Field(..., description="At-risk customer count") 
    scenarios_available: int = Field(..., description="Available scenarios")
    avg_clv: float = Field(..., description="Average customer lifetime value")
    tier_distribution: Dict[str, int] = Field(..., description="Customers by tier")
    success_rates: Dict[str, float] = Field(default_factory=dict, description="Historical success rates")
    last_updated: datetime = Field(default_factory=datetime.now)

class SystemHealth(BaseModel):
    """System health status"""
    status: str = Field(..., description="Overall system status")
    components: Dict[str, str] = Field(..., description="Component statuses")
    uptime_seconds: int = Field(..., description="System uptime")
    last_check: datetime = Field(default_factory=datetime.now)

class ExportRequest(BaseModel):
    """Data export request"""
    filename: str = Field(..., description="Export filename")
    data_type: str = Field(..., description="Type of data to export")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Export filters")
    format: str = Field(default="json", description="Export format")

# Weekly Simulation Models

class WeeklySuccessRates(BaseModel):
    """Success rates for different retention actions"""
    discount: float = Field(..., ge=0, le=1, description="Discount offer success rate")
    priority_fix: float = Field(..., ge=0, le=1, description="Priority technical fix success rate")
    executive_escalation: float = Field(..., ge=0, le=1, description="Executive escalation success rate")

class CustomerTierDistribution(BaseModel):
    """Customer tier distribution percentages"""
    basic: float = Field(0.80, ge=0, le=1, description="Percentage of basic customers")
    standard: float = Field(0.15, ge=0, le=1, description="Percentage of standard customers")
    premium: float = Field(0.04, ge=0, le=1, description="Percentage of premium customers")
    enterprise: float = Field(0.01, ge=0, le=1, description="Percentage of enterprise customers")

class MonthlyRevenue(BaseModel):
    """Monthly revenue by customer tier"""
    basic: float = Field(35.0, ge=10, le=100, description="Monthly revenue from basic customers")
    standard: float = Field(65.0, ge=20, le=200, description="Monthly revenue from standard customers")
    premium: float = Field(120.0, ge=50, le=500, description="Monthly revenue from premium customers")
    enterprise: float = Field(250.0, ge=100, le=1000, description="Monthly revenue from enterprise customers")

class InterventionCosts(BaseModel):
    """Dynamic intervention costs"""
    discount_duration_months: int = Field(6, ge=3, le=12, description="Duration of discount in months")
    priority_fix: float = Field(250.0, ge=100, le=1000, description="Fixed cost for priority fix")
    executive_escalation: float = Field(400.0, ge=300, le=2000, description="Fixed cost for executive escalation")

class SystemConfiguration(BaseModel):
    """Complete system configuration - no hardcoded values"""
    customer_distribution: CustomerTierDistribution = Field(default_factory=CustomerTierDistribution, description="Customer tier distribution")
    monthly_revenue: MonthlyRevenue = Field(default_factory=MonthlyRevenue, description="Monthly revenue by tier")
    intervention_costs: InterventionCosts = Field(default_factory=InterventionCosts, description="Intervention costs")
    
    def get_annual_clv(self) -> Dict[str, float]:
        """Calculate annual CLV from monthly revenue"""
        return {
            'basic': self.monthly_revenue.basic * 12,
            'standard': self.monthly_revenue.standard * 12,
            'premium': self.monthly_revenue.premium * 12,
            'enterprise': self.monthly_revenue.enterprise * 12
        }

class WeeklySimulationRequest(BaseModel):
    """Request for weekly retention simulation"""
    customers_at_risk: int = Field(..., ge=50, le=500, description="Number of customers at risk this week")
    weekly_budget: float = Field(..., ge=5000, le=50000, description="Weekly budget for retention actions")
    success_rates: WeeklySuccessRates = Field(..., description="Success rates for different actions")
    intervention_costs: Optional[InterventionCosts] = Field(None, description="Dynamic intervention costs")
    current_week: int = Field(..., ge=1, le=52, description="Current week number (1-52)")
    system_config: Optional[SystemConfiguration] = Field(default_factory=SystemConfiguration, description="System configuration parameters")
    simulation_history: List[Dict[str, Any]] = Field(default_factory=list, description="Previous weeks' results")
    team_histories: Optional[Dict[str, List[Dict[str, Any]]]] = Field(default_factory=dict, description="Team-specific histories for learning")
    allocations: Optional[Dict[str, int]] = Field(None, description="Agent-determined allocations (optional)")

class CustomersByTier(BaseModel):
    """Customer distribution by tier for a week"""
    enterprise: int = Field(..., ge=0, description="Enterprise tier customers")
    premium: int = Field(..., ge=0, description="Premium tier customers")
    standard: int = Field(..., ge=0, description="Standard tier customers")
    basic: int = Field(..., ge=0, description="Basic tier customers")

class ActionsTaken(BaseModel):
    """Actions taken during the week"""
    discount_20: int = Field(..., ge=0, description="20% discount offers (Basic tier)")
    discount_30: int = Field(..., ge=0, description="30% discount offers (Standard tier)")
    priority_fix: int = Field(..., ge=0, description="Priority technical fixes (Premium tier)")
    executive_escalation: int = Field(..., ge=0, description="Executive escalations (Enterprise tier)")

class CustomersSaved(BaseModel):
    """Customers successfully retained by tier"""
    enterprise: int = Field(..., ge=0, description="Enterprise customers saved")
    premium: int = Field(..., ge=0, description="Premium customers saved")
    standard: int = Field(..., ge=0, description="Standard customers saved")
    basic: int = Field(..., ge=0, description="Basic customers saved")

class WeeklySimulationResponse(BaseModel):
    """Response from weekly retention simulation"""
    week: int = Field(..., description="Week number")
    customers_by_tier: CustomersByTier = Field(..., description="Customer distribution by tier")
    actions_taken: ActionsTaken = Field(..., description="Actions taken during the week")
    customers_saved: CustomersSaved = Field(..., description="Customers saved by tier")
    clv_protected: float = Field(..., description="Total CLV protected this week")
    budget_spent: float = Field(..., description="Budget spent this week")
    cumulative_clv: float = Field(..., description="Cumulative CLV protected across all weeks")

# Agent Decision Models

class AgentConversationEntry(BaseModel):
    """Single entry in agent conversation log"""
    agent: str = Field(..., description="Agent name")
    timestamp: str = Field(..., description="Message timestamp")
    message: str = Field(..., description="Agent message content")

class AgentDecisionRequest(BaseModel):
    """Request for agent-based decision making"""
    customers_at_risk: int = Field(..., ge=50, le=500, description="Number of customers at risk this week")
    weekly_budget: float = Field(..., ge=5000, le=50000, description="Weekly budget for retention actions")
    success_rates: WeeklySuccessRates = Field(..., description="Current success rates for different actions")
    current_week: int = Field(..., ge=1, le=52, description="Current week number (1-52)")
    simulation_history: List[Dict[str, Any]] = Field(default_factory=list, description="Previous weeks' results")

class AgentAllocationDecision(BaseModel):
    """Agent's allocation decision for the week"""
    discount_20: int = Field(..., ge=0, description="20% discount offers (Basic tier)")
    discount_30: int = Field(..., ge=0, description="30% discount offers (Standard tier)")
    priority_fix: int = Field(..., ge=0, description="Priority technical fixes (Premium tier)")
    executive_escalation: int = Field(..., ge=0, description="Executive escalations (Enterprise tier)")
    budget_allocation: Dict[str, float] = Field(..., description="Budget allocation by tier")
    reasoning: str = Field(..., description="Reasoning behind allocation")

class AgentDecisionResponse(BaseModel):
    """Response from agent decision making"""
    allocation_decisions: AgentAllocationDecision = Field(..., description="Agent's allocation decisions")
    reasoning_summary: str = Field(..., description="Summary of key reasoning points")
    conversation_log: List[AgentConversationEntry] = Field(..., description="Full agent conversation")
    adapted_success_rates: Dict[str, float] = Field(..., description="Adapted success rate predictions")
    timestamp: str = Field(..., description="Decision timestamp")
    processing_time_ms: Optional[int] = Field(default=None, description="Time taken for decision")

class ParallelSimulationRequest(BaseModel):
    """Request for parallel rule-based and agent-based simulation"""
    customers_at_risk: int = Field(..., ge=50, le=500, description="Number of customers at risk this week")
    weekly_budget: float = Field(..., ge=5000, le=50000, description="Weekly budget for retention actions")
    success_rates: WeeklySuccessRates = Field(..., description="Success rates for different actions")
    current_week: int = Field(..., ge=1, le=52, description="Current week number (1-52)")
    simulation_history: List[Dict[str, Any]] = Field(default_factory=list, description="Previous weeks' results")

class ParallelSimulationResponse(BaseModel):
    """Response from parallel simulation comparison"""
    week: int = Field(..., description="Week number")
    rule_based_result: WeeklySimulationResponse = Field(..., description="Rule-based system results")
    agent_based_result: WeeklySimulationResponse = Field(..., description="Agent-based system results")
    agent_decision_data: AgentDecisionResponse = Field(..., description="Agent decision process data")
    comparison_metrics: Dict[str, Any] = Field(..., description="Comparison between both systems")
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

# AutoRun Simulation Models

class AutoRunRequest(BaseModel):
    """Request to start a 5-week automated simulation"""
    session_name: Optional[str] = Field(None, description="Optional name for this simulation session")
    starting_parameters: Optional[Dict[str, Any]] = Field(None, description="Optional starting parameters override")
    save_conversations: bool = Field(True, description="Whether to save full team conversations")

class AutoRunSession(BaseModel):
    """AutoRun simulation session tracking"""
    session_id: str = Field(..., description="Unique session identifier")
    session_name: Optional[str] = Field(None, description="Human-readable session name")
    status: str = Field(..., description="Current session status (running, completed, failed)")
    current_week: int = Field(0, description="Current week being processed (0-5)")
    total_weeks: int = Field(5, description="Total weeks in simulation")
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = Field(None, description="When session completed")
    error_message: Optional[str] = Field(None, description="Error message if failed")

class WeeklyEvent(BaseModel):
    """Market event or parameter change for a specific week"""
    week: int = Field(..., ge=1, le=10, description="Week number")
    event_type: str = Field(..., description="Type of event (market, technical, business, customer)")
    description: str = Field(..., description="Human-readable event description")
    parameter_changes: Dict[str, Any] = Field(..., description="Parameters affected by this event")
    impact_reasoning: str = Field(..., description="Game Master's reasoning for this change")

class WeeklyAutoRunResult(BaseModel):
    """Results from a single week of AutoRun simulation"""
    week: int = Field(..., ge=1, le=10, description="Week number")
    session_id: str = Field(..., description="Session identifier")
    
    # Game Master outputs
    game_master_parameters: Dict[str, Any] = Field(..., description="Parameters set by Game Master")
    game_master_reasoning: str = Field(..., description="Game Master's reasoning for parameters")
    events: List[WeeklyEvent] = Field(default_factory=list, description="Events for this week")
    
    # Team results
    team_results: Dict[str, WeeklySimulationResponse] = Field(..., description="Results from all teams")
    
    # Game Master evaluation
    game_master_evaluation: Dict[str, Any] = Field(..., description="Game Master's team performance evaluation")
    
    # Metadata
    processed_at: datetime = Field(default_factory=datetime.now)
    processing_time_seconds: float = Field(..., description="Time taken to process this week")

class MultiWeekAnalysis(BaseModel):
    """Analysis across multiple weeks of AutoRun simulation"""
    session_id: str = Field(..., description="Session identifier")
    weeks_analyzed: int = Field(..., description="Number of weeks included in analysis")
    
    # Performance trends
    team_performance_trends: Dict[str, List[float]] = Field(..., description="Performance scores over time by team")
    adaptation_indicators: Dict[str, Dict[str, Any]] = Field(..., description="Evidence of team learning/adaptation")
    
    # Comparative analysis
    overall_rankings: Dict[str, int] = Field(..., description="Final team rankings")
    strength_analysis: Dict[str, List[str]] = Field(..., description="Identified strengths per team")
    weakness_analysis: Dict[str, List[str]] = Field(..., description="Identified weaknesses per team")
    
    # Scenario insights
    challenging_weeks: List[int] = Field(..., description="Weeks that proved most challenging")
    parameter_impact_analysis: Dict[str, float] = Field(..., description="Which parameters most affected outcomes")
    
    # Final recommendations
    game_master_final_report: str = Field(..., description="Game Master's comprehensive final analysis")
    recommended_approach: str = Field(..., description="Recommended decision-making approach")
    hybrid_suggestions: List[str] = Field(default_factory=list, description="Suggestions for hybrid approaches")
    
    generated_at: datetime = Field(default_factory=datetime.now)

class AutoRunStatusResponse(BaseModel):
    """Real-time status response for AutoRun simulation"""
    session: AutoRunSession = Field(..., description="Session information")
    current_week_progress: Optional[Dict[str, Any]] = Field(None, description="Current week processing status")
    completed_weeks: List[WeeklyAutoRunResult] = Field(default_factory=list, description="Results from completed weeks")
    estimated_time_remaining: Optional[int] = Field(None, description="Estimated seconds remaining")

class AutoRunCompleteResponse(BaseModel):
    """Final response when AutoRun simulation completes"""
    session: AutoRunSession = Field(..., description="Final session information")
    weekly_results: List[WeeklyAutoRunResult] = Field(..., description="All weekly results")
    final_analysis: MultiWeekAnalysis = Field(..., description="Comprehensive multi-week analysis")
    data_file_path: str = Field(..., description="Path to saved session data file")