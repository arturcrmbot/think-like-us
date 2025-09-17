"""
Simple integration with cognitive agents for the dashboard
"""
import os
import sys
import asyncio
from typing import Dict, Any, List
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import AutoGen components
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

# Import agent prompts - using retention-specific prompts for better analysis
from agents.cognitive_agents_v2 import AGENT_PROMPTS as COGNITIVE_PROMPTS
from agents.corporate_agents_v2 import AGENT_PROMPTS as CORPORATE_PROMPTS

# Load environment
from dotenv import load_dotenv
from pathlib import Path
# Load .env from parent directory
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

def build_comprehensive_scenario(customers_at_risk: int, weekly_budget: float, success_rates: dict, 
                                 history: list, config, discount_months: int, priority_cost: float, 
                                 executive_cost: float) -> str:
    """Build comprehensive scenario context for optimized agents"""
    
    # Get customer distribution and revenue data
    customer_dist = config.customer_distribution
    monthly_rev = config.monthly_revenue
    annual_clv = config.get_annual_clv()
    
    # Build history context
    history_context = ""
    if history:
        history_context = "\nHISTORICAL PERFORMANCE DATA:\n"
        for i, week_data in enumerate(history, 1):
            history_context += f"Week {i}: Budget £{week_data.get('budget', 0):,}, ROI {week_data.get('roi', 0):.2f}x, Customers saved {week_data.get('customers_saved', 0)}\n"
        history_context += "\nAnalyze these patterns when making decisions.\n"
    
    return f"""
=== CUSTOMER RETENTION OPTIMIZATION CHALLENGE ===

BUSINESS CONTEXT:
You are analyzing a telecommunications company's customer retention situation. The company has identified customers at high risk of canceling their service (churning) and needs to allocate limited resources to retain them effectively.

CURRENT WEEK: {len(history) + 1}
TOTAL CUSTOMERS AT RISK: {customers_at_risk}

CUSTOMER SEGMENTS & VALUE:
The at-risk customers are distributed across four service tiers with different monthly revenue and lifetime values:

1. BASIC TIER ({customer_dist.basic:.0%} of customers):
   - Count: {int(customers_at_risk * customer_dist.basic)} customers
   - Monthly Revenue: £{monthly_rev.basic:.0f} per customer
   - Annual Customer Lifetime Value: £{annual_clv['basic']:.0f} per customer
   - Total Value at Risk: £{int(customers_at_risk * customer_dist.basic * annual_clv['basic']):,}

2. STANDARD TIER ({customer_dist.standard:.0%} of customers):
   - Count: {int(customers_at_risk * customer_dist.standard)} customers  
   - Monthly Revenue: £{monthly_rev.standard:.0f} per customer
   - Annual Customer Lifetime Value: £{annual_clv['standard']:.0f} per customer
   - Total Value at Risk: £{int(customers_at_risk * customer_dist.standard * annual_clv['standard']):,}

3. PREMIUM TIER ({customer_dist.premium:.0%} of customers):
   - Count: {int(customers_at_risk * customer_dist.premium)} customers
   - Monthly Revenue: £{monthly_rev.premium:.0f} per customer
   - Annual Customer Lifetime Value: £{annual_clv['premium']:.0f} per customer  
   - Total Value at Risk: £{int(customers_at_risk * customer_dist.premium * annual_clv['premium']):,}

4. ENTERPRISE TIER ({customer_dist.enterprise:.0%} of customers):
   - Count: {int(customers_at_risk * customer_dist.enterprise)} customers
   - Monthly Revenue: £{monthly_rev.enterprise:.0f} per customer
   - Annual Customer Lifetime Value: £{annual_clv['enterprise']:.0f} per customer
   - Total Value at Risk: £{int(customers_at_risk * customer_dist.enterprise * annual_clv['enterprise']):,}

TOTAL CUSTOMER LIFETIME VALUE AT RISK: £{int(customers_at_risk * customer_dist.basic * annual_clv['basic'] + customers_at_risk * customer_dist.standard * annual_clv['standard'] + customers_at_risk * customer_dist.premium * annual_clv['premium'] + customers_at_risk * customer_dist.enterprise * annual_clv['enterprise']):,}

AVAILABLE RESOURCES:
Weekly Budget: £{weekly_budget:,.0f}

INTERVENTION OPTIONS:
You have four different retention interventions available, each with different costs and success rates:

1. DISCOUNT_20 (20% Discount for {discount_months} months):
   - Success Rate: {success_rates.get('discount', 0.4):.0%} retention probability
   - Cost per customer by tier:
     • Basic: £{monthly_rev.basic * 0.2 * discount_months:.0f}
     • Standard: £{monthly_rev.standard * 0.2 * discount_months:.0f}  
     • Premium: £{monthly_rev.premium * 0.2 * discount_months:.0f}
     • Enterprise: £{monthly_rev.enterprise * 0.2 * discount_months:.0f}

2. DISCOUNT_30 (30% Discount for {discount_months} months):
   - Success Rate: {success_rates.get('discount', 0.4):.0%} retention probability  
   - Cost per customer by tier:
     • Basic: £{monthly_rev.basic * 0.3 * discount_months:.0f}
     • Standard: £{monthly_rev.standard * 0.3 * discount_months:.0f}
     • Premium: £{monthly_rev.premium * 0.3 * discount_months:.0f}
     • Enterprise: £{monthly_rev.enterprise * 0.3 * discount_months:.0f}

3. PRIORITY_FIX (Technical Issue Resolution):
   - Success Rate: {success_rates.get('priority_fix', 0.7):.0%} retention probability
   - Cost: £{priority_cost} per customer (same for all tiers)

4. EXECUTIVE_ESCALATION (Senior Management Intervention):
   - Success Rate: {success_rates.get('executive_escalation', 0.85):.0%} retention probability  
   - Cost: £{executive_cost} per customer (same for all tiers)

{history_context}

YOUR TASK:
Analyze this retention optimization challenge and determine the optimal allocation of interventions across the customer population within the budget constraint. Consider:
- Expected return on investment for each intervention type
- Customer segment value differences  
- Resource efficiency and budget constraints
- Risk vs. reward trade-offs

REQUIRED OUTPUT FORMAT:
ACTION_PLAN_READY
ALLOCATIONS:
discount_20: [number of customers]
discount_30: [number of customers]
priority_fix: [number of customers]
executive_escalation: [number of customers]
"""

class CognitiveAgentSimulator:
    """Simplified cognitive agent simulator for dashboard integration"""
    
    def __init__(self):
        """Initialize the cognitive agent simulator"""
        # Setup Azure OpenAI client
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        model_name = os.getenv("AZURE_OPENAI_MODEL_NAME")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-01-preview")
        
        self.model_client = AzureOpenAIChatCompletionClient(
            azure_endpoint=endpoint,
            api_key=api_key,
            model=model_name,
            api_version=api_version,
            model_capabilities={
                "vision": True,
                "function_calling": True,
                "json_output": True,
                "structured_output": True
            }
        )
        
        # Create cognitive agents
        self.agents = []
        for agent_name, agent_prompt in COGNITIVE_PROMPTS.items():
            agent = AssistantAgent(
                name=agent_name,
                model_client=self.model_client,
                system_message=agent_prompt
            )
            self.agents.append(agent)
            print(f"Created agent: {agent_name}")
        print(f"Total agents created: {len(self.agents)}")
    
    async def get_agent_decision(self, customers_at_risk: int, weekly_budget: float, 
                                 success_rates: Dict[str, float], history: List[Dict], 
                                 intervention_costs=None, system_config=None) -> Dict[str, Any]:
        """
        Get cognitive agent decision for retention strategy
        
        Returns dict with:
        - allocations: How to allocate customers/budget
        - reasoning: Summary of agent thinking
        - conversation: Agent dialogue
        """
        # Create simple scenario prompt with basic history
        history_context = ""
        if history and len(history) > 0:
            recent_weeks = history[-3:] if len(history) > 3 else history
            history_context = "\n\nRecent History:\n"
            for week_data in recent_weeks:
                week_num = week_data.get('week', 0)
                saved = week_data.get('customers_saved', {})
                total_saved = sum([saved.get('basic', 0), saved.get('standard', 0), 
                                 saved.get('premium', 0), saved.get('enterprise', 0)])
                clv = week_data.get('clv_protected', 0)
                history_context += f"- Week {week_num}: Saved {total_saved} customers, £{clv/1000:.0f}k CLV protected\n"
        
        # Import SystemConfiguration if needed
        from models import SystemConfiguration
        
        # Get system configuration - use provided or default
        config = system_config or SystemConfiguration()
        
        # Get actual costs from system configuration
        priority_cost = config.intervention_costs.priority_fix
        executive_cost = config.intervention_costs.executive_escalation
        discount_months = config.intervention_costs.discount_duration_months
        
        # Get customer distribution and revenue data
        customer_dist = config.customer_distribution
        monthly_rev = config.monthly_revenue
        annual_clv = config.get_annual_clv()
        
        # Use comprehensive scenario for optimized agents
        scenario = build_comprehensive_scenario(
            customers_at_risk, weekly_budget, success_rates, history, config,
            discount_months, priority_cost, executive_cost
        )
        
        # Setup agent collaboration with proper termination - allow multiple ACTION_PLAN_READY mentions
        from autogen_agentchat.conditions import MaxMessageTermination
        termination = MaxMessageTermination(8)  # Equal processing time as corporate team
        
        selector_prompt = """Select who speaks next from {participants}.

Follow this sequence:
1. PerceptualCortex observes the data
2. Hippocampus provides historical context
3. PrefrontalCortex decides strategy
4. CerebellumCheck validates

{history}"""
        
        team = SelectorGroupChat(
            participants=self.agents,
            model_client=self.model_client,
            selector_prompt=selector_prompt,
            termination_condition=termination,
            allow_repeated_speaker=False
        )
        
        # Run agent discussion
        print(f"Cognitive agents analyzing week {len(history) + 1}...")
        print(f"Number of agents in team: {len(self.agents)}")
        print(f"Selector prompt preview: {selector_prompt[:100]}...")
        # Add retry logic for rate limits
        import asyncio
        from openai import RateLimitError
        
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))
                    print(f"Retrying after {delay}s delay (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                
                result = await team.run(task=scenario)
                print(f"Team.run completed. Messages: {len(result.messages)}")
                break
                
            except Exception as e:
                error_str = str(e)
                error_type = str(type(e))
                # Check for various 429/rate limit error patterns
                is_rate_limit = (
                    "RateLimitError" in error_type or
                    "429" in error_str or
                    "rate limit" in error_str.lower() or
                    "GroupChatError" in error_type or
                    "Error code: 429" in error_str
                )

                if is_rate_limit:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"Rate limit hit, retrying in {delay}s... (attempt {attempt + 1})")
                        print(f"Error details: {error_type}: {error_str[:200]}")
                        continue
                    else:
                        print("Rate limit retries exhausted, falling back to rule-based")
                        print(f"Final error: {error_type}: {error_str}")
                        raise
                else:
                    print(f"TEAM.RUN ERROR: {e}")
                    import traceback
                    traceback.print_exc()
                    raise
        
        # Debug: Print what agents actually said
        print(f"DEBUG: Total messages: {len(result.messages)}")
        print("DEBUG: Agent messages:")
        for msg in result.messages:
            content = msg.content[:200] if len(msg.content) > 200 else msg.content
            # Fix encoding for Windows console
            content = content.encode('ascii', 'ignore').decode('ascii')
            print(f"  {msg.source}: {content}")
        
        # Extract conversation
        conversation = []
        for msg in result.messages:
            if msg.source != "user":
                conversation.append({
                    "agent": msg.source,
                    "message": msg.content  # Keep full messages
                })
        
        # Parse agent decision from their output
        allocations = {
            "discount_20": 0,
            "discount_30": 0,
            "priority_fix": 0,
            "executive_escalation": 0
        }
        reasoning = "Analyzing situation..."
        
        # Find the LAST message with ACTION_PLAN_READY (final team decision)
        action_ready_count = 0
        last_action_message = None
        
        for msg in result.messages:
            if "ACTION_PLAN_READY" in msg.content:
                action_ready_count += 1
                last_action_message = msg
                print(f"DEBUG: Found ACTION_PLAN_READY #{action_ready_count} in {msg.source}")
                print(f"DEBUG: Content preview: {msg.content[:200]}...")
        
        # Parse the LAST (final) ACTION_PLAN_READY message
        if last_action_message:
            print(f"DEBUG: Using FINAL decision from {last_action_message.source}")
            print(f"DEBUG: Full content: {last_action_message.content}")
            content = last_action_message.content
            
            # Parse allocations from the structured output - simple and reliable approach
            import re
            discount_20_match = re.search(r'discount_20:\s*(\d+)', content, re.IGNORECASE)
            discount_30_match = re.search(r'discount_30:\s*(\d+)', content, re.IGNORECASE)
            priority_fix_match = re.search(r'priority_fix:\s*(\d+)', content, re.IGNORECASE)
            executive_match = re.search(r'executive_escalation:\s*(\d+)', content, re.IGNORECASE)
            reasoning_match = re.search(r'REASONING:(.+?)(?:ACTION_PLAN_READY|$)', content, re.DOTALL | re.IGNORECASE)
            
            if discount_20_match:
                allocations["discount_20"] = int(discount_20_match.group(1))
            if discount_30_match:
                allocations["discount_30"] = int(discount_30_match.group(1))
            if priority_fix_match:
                allocations["priority_fix"] = int(priority_fix_match.group(1))
            if executive_match:
                allocations["executive_escalation"] = int(executive_match.group(1))
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
            
            print(f"DEBUG: FINAL allocations from last message: d20={allocations['discount_20']}, d30={allocations['discount_30']}, pf={allocations['priority_fix']}, ee={allocations['executive_escalation']}")
        else:
            print("DEBUG: No ACTION_PLAN_READY message found!")
        
        # Calculate average discount costs based on actual system configuration
        avg_discount_20_cost = (customer_dist.basic * monthly_rev.basic * 0.2 * discount_months + 
                              customer_dist.standard * monthly_rev.standard * 0.2 * discount_months + 
                              customer_dist.premium * monthly_rev.premium * 0.2 * discount_months + 
                              customer_dist.enterprise * monthly_rev.enterprise * 0.2 * discount_months)
        avg_discount_30_cost = (customer_dist.basic * monthly_rev.basic * 0.3 * discount_months + 
                              customer_dist.standard * monthly_rev.standard * 0.3 * discount_months + 
                              customer_dist.premium * monthly_rev.premium * 0.3 * discount_months + 
                              customer_dist.enterprise * monthly_rev.enterprise * 0.3 * discount_months)
        
        total_cost = (allocations["discount_20"] * avg_discount_20_cost + 
                     allocations["discount_30"] * avg_discount_30_cost +
                     allocations["priority_fix"] * priority_cost +
                     allocations["executive_escalation"] * executive_cost)
        
        print(f"DEBUG: Budget validation - Total cost: £{total_cost}, Budget: £{weekly_budget}")
        
        if total_cost > weekly_budget:
            # Scale down proportionally if over budget
            scale = weekly_budget / total_cost
            print(f"DEBUG: Scaling down by {scale:.3f}")
            for key in allocations:
                old_value = allocations[key]
                allocations[key] = int(allocations[key] * scale)
                print(f"DEBUG: Scaled {key}: {old_value} -> {allocations[key]}")
        
        print(f"DEBUG: FINAL allocations: d20={allocations['discount_20']}, d30={allocations['discount_30']}, pf={allocations['priority_fix']}, ee={allocations['executive_escalation']}")
        
        return {
            "allocations": allocations,
            "conversation": conversation,
            "adapted_rates": {
                "discount": max(0.3, success_rates.get('discount', 0.4) - 0.05),
                "priority_fix": min(0.8, success_rates.get('priority_fix', 0.7) + 0.02),
                "executive_escalation": success_rates.get('executive_escalation', 0.85)
            }
        }

    def get_conversation_summary(self, conversation: List[Dict]) -> str:
        """Extract key insights from team conversation"""
        if not conversation or len(conversation) == 0:
            return "No team discussion available"
        
        # Find the final decision message with ACTION_PLAN_READY
        final_decision = None
        for msg in reversed(conversation):
            if "ACTION_PLAN_READY" in msg.get("message", ""):
                final_decision = msg.get("message", "")
                break
        
        if final_decision:
            # Extract reasoning from final decision
            reasoning_start = final_decision.find("REASONING:")
            if reasoning_start > -1:
                reasoning = final_decision[reasoning_start + 10:].strip()
                return reasoning[:200] + "..." if len(reasoning) > 200 else reasoning
        
        # Fallback: use last meaningful message
        return conversation[-1].get("message", "")[:200] + "..."


# Test function
async def test_agents():
    """Test the cognitive agents"""
    simulator = CognitiveAgentSimulator()
    
    from models import SystemConfiguration
    
    result = await simulator.get_agent_decision(
        customers_at_risk=100,
        weekly_budget=100000,
        success_rates={"discount": 0.4, "priority_fix": 0.7, "executive_escalation": 0.85},
        history=[],
        intervention_costs=None,
        system_config=SystemConfiguration()  # Use default system configuration
    )
    
    print("Agent Decision:")
    print(f"  Allocations: {result['allocations']}")
    print(f"  Reasoning: {result['reasoning']}")
    print(f"  Conversation entries: {len(result['conversation'])}")
    
class CorporateAgentSimulator:
    """Corporate agent simulator following business team structure"""
    
    def __init__(self):
        """Initialize the corporate agent simulator"""
        # Setup Azure OpenAI client
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        model_name = os.getenv("AZURE_OPENAI_MODEL_NAME")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-01-preview")
        
        self.model_client = AzureOpenAIChatCompletionClient(
            azure_endpoint=endpoint,
            api_key=api_key,
            model=model_name,
            api_version=api_version,
            model_capabilities={
                "vision": True,
                "function_calling": True,
                "json_output": True,
                "structured_output": True
            }
        )
        
        # Create corporate agents
        self.agents = []
        for agent_name, agent_prompt in CORPORATE_PROMPTS.items():
            agent = AssistantAgent(
                name=agent_name,
                model_client=self.model_client,
                system_message=agent_prompt
            )
            self.agents.append(agent)
            print(f"Created corporate agent: {agent_name}")
        print(f"Total corporate agents created: {len(self.agents)}")
    
    async def get_agent_decision(self, customers_at_risk: int, weekly_budget: float, 
                                 success_rates: Dict[str, float], history: List[Dict], 
                                 intervention_costs=None, system_config=None) -> Dict[str, Any]:
        """
        Get corporate agent decision for retention strategy
        
        Returns dict with:
        - allocations: How to allocate customers/budget
        - reasoning: Summary of agent thinking
        - conversation: Agent dialogue
        """
        # Create simple scenario prompt with basic history
        history_context = ""
        if history and len(history) > 0:
            recent_weeks = history[-3:] if len(history) > 3 else history
            history_context = "\n\nRecent Performance History:\n"
            for week_data in recent_weeks:
                week_num = week_data.get('week', 0)
                saved = week_data.get('customers_saved', {})
                total_saved = sum([saved.get('basic', 0), saved.get('standard', 0), 
                                 saved.get('premium', 0), saved.get('enterprise', 0)])
                clv = week_data.get('clv_protected', 0)
                history_context += f"- Week {week_num}: Saved {total_saved} customers, £{clv/1000:.0f}k CLV protected\n"
        
        # Import SystemConfiguration if needed
        from models import SystemConfiguration
        
        # Get system configuration - use provided or default
        config = system_config or SystemConfiguration()
        
        # Get actual costs from system configuration
        priority_cost = config.intervention_costs.priority_fix
        executive_cost = config.intervention_costs.executive_escalation
        discount_months = config.intervention_costs.discount_duration_months
        
        # Get customer distribution and revenue data
        customer_dist = config.customer_distribution
        monthly_rev = config.monthly_revenue
        annual_clv = config.get_annual_clv()
        
        scenario = f"""
CORPORATE RETENTION STRATEGY MEETING - Week {len(history) + 1}

BUSINESS SITUATION:
- Customers at risk: {customers_at_risk}
  * Basic ({customer_dist.basic:.0%}): {int(customers_at_risk * customer_dist.basic)} customers × £{annual_clv['basic']:.0f} CLV = £{int(customers_at_risk * customer_dist.basic * annual_clv['basic']):,}
  * Standard ({customer_dist.standard:.0%}): {int(customers_at_risk * customer_dist.standard)} customers × £{annual_clv['standard']:.0f} CLV = £{int(customers_at_risk * customer_dist.standard * annual_clv['standard']):,}
  * Premium ({customer_dist.premium:.0%}): {int(customers_at_risk * customer_dist.premium)} customers × £{annual_clv['premium']:.0f} CLV = £{int(customers_at_risk * customer_dist.premium * annual_clv['premium']):,}
  * Enterprise ({customer_dist.enterprise:.0%}): {int(customers_at_risk * customer_dist.enterprise)} customers × £{annual_clv['enterprise']:.0f} CLV = £{int(customers_at_risk * customer_dist.enterprise * annual_clv['enterprise']):,}
- Total CLV at risk: £{int(customers_at_risk * customer_dist.basic * annual_clv['basic'] + customers_at_risk * customer_dist.standard * annual_clv['standard'] + customers_at_risk * customer_dist.premium * annual_clv['premium'] + customers_at_risk * customer_dist.enterprise * annual_clv['enterprise']):,}
- Available budget: £{weekly_budget:,.0f}

CUSTOMER LIFETIME VALUES (Annual):
- Basic: £{annual_clv['basic']:.0f}/year (£{monthly_rev.basic:.0f}/month × 12)
- Standard: £{annual_clv['standard']:.0f}/year (£{monthly_rev.standard:.0f}/month × 12)  
- Premium: £{annual_clv['premium']:.0f}/year (£{monthly_rev.premium:.0f}/month × 12)
- Enterprise: £{annual_clv['enterprise']:.0f}/year (£{monthly_rev.enterprise:.0f}/month × 12)

INTERVENTION SUCCESS RATES:
- discount_20/30: {success_rates.get('discount', 0.4):.0%} chance of retention
- priority_fix: {success_rates.get('priority_fix', 0.7):.0%} chance of retention
- executive_escalation: {success_rates.get('executive_escalation', 0.85):.0%} chance of retention

{history_context}

INTERVENTION OPTIONS & ACTUAL COSTS FROM SYSTEM CONFIG:
- discount_20: 20% discount for {discount_months} months
  * Basic: £{monthly_rev.basic:.0f} × 20% × {discount_months} = £{monthly_rev.basic * 0.2 * discount_months:.0f}/customer
  * Standard: £{monthly_rev.standard:.0f} × 20% × {discount_months} = £{monthly_rev.standard * 0.2 * discount_months:.0f}/customer  
  * Premium: £{monthly_rev.premium:.0f} × 20% × {discount_months} = £{monthly_rev.premium * 0.2 * discount_months:.0f}/customer
  * Enterprise: £{monthly_rev.enterprise:.0f} × 20% × {discount_months} = £{monthly_rev.enterprise * 0.2 * discount_months:.0f}/customer
- discount_30: 30% discount for {discount_months} months
  * Basic: £{monthly_rev.basic:.0f} × 30% × {discount_months} = £{monthly_rev.basic * 0.3 * discount_months:.0f}/customer
  * Standard: £{monthly_rev.standard:.0f} × 30% × {discount_months} = £{monthly_rev.standard * 0.3 * discount_months:.0f}/customer
  * Premium: £{monthly_rev.premium:.0f} × 30% × {discount_months} = £{monthly_rev.premium * 0.3 * discount_months:.0f}/customer
  * Enterprise: £{monthly_rev.enterprise:.0f} × 30% × {discount_months} = £{monthly_rev.enterprise * 0.3 * discount_months:.0f}/customer
- priority_fix: £{priority_cost} per customer (fixed cost)
- executive_escalation: £{executive_cost} per customer (fixed cost)

CORPORATE TEAM MEETING: Develop a retention strategy for the at-risk customers within the available budget.

Each team member should provide their expertise in sequence:
1. CustomerExperienceAnalyst - analyze customer satisfaction and service quality
2. CustomerIntelligence - provide segmentation insights and churn risk analysis
3. RetentionStrategist - develop intervention strategy and resource allocation
4. OperationsSpecialist - validate feasibility and finalize resource allocation

FINAL DELIVERABLE: Specific customer allocation numbers for each intervention type.

FORMAT FOR FINAL ALLOCATION:
CORPORATE_STRATEGY_APPROVED
ALLOCATIONS:
discount_20: [number]
discount_30: [number]
priority_fix: [number]
executive_escalation: [number]
STRATEGY_RATIONALE: [brief explanation]
"""
        
        # Setup corporate team collaboration with proper termination
        termination = MaxMessageTermination(max_messages=8)  # Shorter for faster processing
        
        selector_prompt = """Select who speaks next from {participants}.

Follow corporate meeting protocol:
1. CustomerExperienceAnalyst provides customer analysis
2. CustomerIntelligence provides segmentation insights
3. RetentionStrategist develops strategy
4. OperationsSpecialist validates and finalizes

{history}"""
        
        team = SelectorGroupChat(
            participants=self.agents,
            model_client=self.model_client,
            selector_prompt=selector_prompt,
            termination_condition=termination,
            allow_repeated_speaker=False
        )
        
        # Run corporate team discussion
        print(f"Corporate team analyzing week {len(history) + 1}...")
        print(f"Number of corporate agents in team: {len(self.agents)}")
        
        # Add retry logic for rate limits
        import asyncio
        from openai import RateLimitError
        
        max_retries = 3
        base_delay = 2
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))
                    print(f"Retrying corporate team after {delay}s delay (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                
                result = await team.run(task=scenario)
                print(f"Corporate team discussion completed. Messages: {len(result.messages)}")
                break
                
            except Exception as e:
                error_str = str(e)
                error_type = str(type(e))
                # Check for various 429/rate limit error patterns
                is_rate_limit = (
                    "RateLimitError" in error_type or
                    "429" in error_str or
                    "rate limit" in error_str.lower() or
                    "GroupChatError" in error_type or
                    "Error code: 429" in error_str
                )

                if is_rate_limit:
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"Corporate team rate limit hit, retrying in {delay}s... (attempt {attempt + 1})")
                        print(f"Corporate team error details: {error_type}: {error_str[:200]}")
                        continue
                    else:
                        print("Corporate team rate limit retries exhausted, falling back to rule-based")
                        print(f"Corporate team final error: {error_type}: {error_str}")
                        raise
                else:
                    print(f"CORPORATE TEAM ERROR: {e}")
                    import traceback
                    traceback.print_exc()
                    raise
        
        # Debug: Print corporate team messages
        print(f"DEBUG: Corporate team total messages: {len(result.messages)}")
        print("DEBUG: Corporate team messages:")
        for msg in result.messages:
            content = msg.content[:200] if len(msg.content) > 200 else msg.content
            # Fix encoding for Windows console
            content = content.encode('ascii', 'ignore').decode('ascii')
            print(f"  {msg.source}: {content}")
        
        # Extract conversation
        conversation = []
        for msg in result.messages:
            if msg.source != "user":
                conversation.append({
                    "agent": msg.source,
                    "message": msg.content  # Keep full messages
                })
        
        # Parse corporate team decision from their output
        allocations = {
            "discount_20": 0,
            "discount_30": 0,
            "priority_fix": 0,
            "executive_escalation": 0
        }
        reasoning = "Corporate team analyzing situation..."
        
        # Find the message with CORPORATE_STRATEGY_APPROVED and parse allocations
        strategy_approved_count = 0
        for msg in result.messages:
            # Ensure content is string for search
            content = str(msg.content) if not isinstance(msg.content, str) else msg.content
            if "CORPORATE_STRATEGY_APPROVED" in content:
                strategy_approved_count += 1
                print(f"DEBUG: Found CORPORATE_STRATEGY_APPROVED #{strategy_approved_count} in {msg.source}")
                print(f"DEBUG: Content preview: {content[:200]}...")
                # Use the properly converted content
                
                # Parse allocations from the structured output (case-insensitive, multiline)
                import re
                discount_20_match = re.search(r'discount_20:\s*(\d+)', content, re.IGNORECASE)
                discount_30_match = re.search(r'discount_30:\s*(\d+)', content, re.IGNORECASE)
                priority_fix_match = re.search(r'priority_fix:\s*(\d+)', content, re.IGNORECASE)
                executive_match = re.search(r'executive_escalation:\s*(\d+)', content, re.IGNORECASE)
                strategy_match = re.search(r'STRATEGY_RATIONALE:(.+?)(?:$|\n\n)', content, re.DOTALL | re.IGNORECASE)
                
                if discount_20_match:
                    allocations["discount_20"] = int(discount_20_match.group(1))
                if discount_30_match:
                    allocations["discount_30"] = int(discount_30_match.group(1))
                if priority_fix_match:
                    allocations["priority_fix"] = int(priority_fix_match.group(1))
                if executive_match:
                    allocations["executive_escalation"] = int(executive_match.group(1))
                if strategy_match:
                    reasoning = strategy_match.group(1).strip()  # Keep full reasoning
                
                print(f"DEBUG: Parsed from {msg.source}: d20={allocations['discount_20']}, d30={allocations['discount_30']}, pf={allocations['priority_fix']}, ee={allocations['executive_escalation']}")
                # Don't break - process all CORPORATE_STRATEGY_APPROVED messages to find the best one
        
        # Calculate average discount costs based on actual system configuration
        avg_discount_20_cost = (customer_dist.basic * monthly_rev.basic * 0.2 * discount_months + 
                              customer_dist.standard * monthly_rev.standard * 0.2 * discount_months + 
                              customer_dist.premium * monthly_rev.premium * 0.2 * discount_months + 
                              customer_dist.enterprise * monthly_rev.enterprise * 0.2 * discount_months)
        avg_discount_30_cost = (customer_dist.basic * monthly_rev.basic * 0.3 * discount_months + 
                              customer_dist.standard * monthly_rev.standard * 0.3 * discount_months + 
                              customer_dist.premium * monthly_rev.premium * 0.3 * discount_months + 
                              customer_dist.enterprise * monthly_rev.enterprise * 0.3 * discount_months)
        
        total_cost = (allocations["discount_20"] * avg_discount_20_cost + 
                     allocations["discount_30"] * avg_discount_30_cost +
                     allocations["priority_fix"] * priority_cost +
                     allocations["executive_escalation"] * executive_cost)
        
        print(f"DEBUG: Corporate team budget validation - Total cost: £{total_cost}, Budget: £{weekly_budget}")
        
        if total_cost > weekly_budget:
            # Scale down proportionally if over budget
            scale = weekly_budget / total_cost
            print(f"DEBUG: Corporate team scaling down by {scale:.3f}")
            for key in allocations:
                old_value = allocations[key]
                allocations[key] = int(allocations[key] * scale)
                print(f"DEBUG: Scaled {key}: {old_value} -> {allocations[key]}")
        
        print(f"DEBUG: FINAL corporate allocations: d20={allocations['discount_20']}, d30={allocations['discount_30']}, pf={allocations['priority_fix']}, ee={allocations['executive_escalation']}")
        
        return {
            "allocations": allocations,
            "conversation": conversation,
            "adapted_rates": {
                "discount": success_rates.get('discount', 0.4),  # Corporate team uses baseline rates
                "priority_fix": success_rates.get('priority_fix', 0.7),
                "executive_escalation": success_rates.get('executive_escalation', 0.85)
            }
        }

    def get_conversation_summary(self, conversation: List[Dict]) -> str:
        """Extract key insights from team conversation"""
        if not conversation or len(conversation) == 0:
            return "No team discussion available"
        
        # Find the final decision message with CORPORATE_STRATEGY_APPROVED
        final_decision = None
        for msg in reversed(conversation):
            message_content = str(msg.get("message", ""))
            if "CORPORATE_STRATEGY_APPROVED" in message_content:
                final_decision = message_content
                break
        
        if final_decision:
            # Extract reasoning from final decision
            reasoning_start = final_decision.find("STRATEGY_RATIONALE:")
            if reasoning_start > -1:
                reasoning = final_decision[reasoning_start + 19:].strip()
                return reasoning[:200] + "..." if len(reasoning) > 200 else reasoning
        
        # Fallback: use last meaningful message
        return conversation[-1].get("message", "")[:200] + "..."


# Test functions
async def test_cognitive_agents():
    """Test the cognitive agents"""
    simulator = CognitiveAgentSimulator()
    
    from models import SystemConfiguration
    
    result = await simulator.get_agent_decision(
        customers_at_risk=100,
        weekly_budget=100000,
        success_rates={"discount": 0.4, "priority_fix": 0.7, "executive_escalation": 0.85},
        history=[],
        intervention_costs=None,
        system_config=SystemConfiguration()
    )
    
    print("Cognitive Agent Decision:")
    print(f"  Allocations: {result['allocations']}")
    print(f"  Reasoning: {result['reasoning']}")
    print(f"  Conversation entries: {len(result['conversation'])}")

async def test_corporate_agents():
    """Test the corporate agents"""
    simulator = CorporateAgentSimulator()
    
    from models import SystemConfiguration
    
    result = await simulator.get_agent_decision(
        customers_at_risk=100,
        weekly_budget=100000,
        success_rates={"discount": 0.4, "priority_fix": 0.7, "executive_escalation": 0.85},
        history=[],
        intervention_costs=None,
        system_config=SystemConfiguration()
    )
    
    print("Corporate Team Decision:")
    print(f"  Allocations: {result['allocations']}")
    print(f"  Reasoning: {result['reasoning']}")
    print(f"  Conversation entries: {len(result['conversation'])}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "corporate":
        asyncio.run(test_corporate_agents())
    else:
        asyncio.run(test_cognitive_agents())