"""
Game Master Integration for 10-Week AutoRun Simulations
Handles AI-driven parameter setting and team performance evaluation
"""

import os
import sys
import json
import asyncio
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import AutoGen components
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

# Import Game Master agent prompts
from agents.game_master_agent import AGENT_PROMPTS as GAME_MASTER_PROMPTS

# Load environment
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Import other components
from models import WeeklySimulationRequest, WeeklySimulationResponse, SystemConfiguration
from simulator import WeeklySimulator
from agent_integration import CognitiveAgentSimulator, CorporateAgentSimulator

class GameMasterSimulator:
    """Game Master that orchestrates 5-week simulations with dynamic parameters"""
    
    def __init__(self):
        """Initialize the Game Master simulator"""
        # Setup Azure OpenAI client
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        model_name = os.getenv("AZURE_OPENAI_MODEL_NAME")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-01-preview")
        
        if not all([api_key, endpoint, model_name]):
            raise ValueError("Missing required Azure OpenAI environment variables")
        
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
        
        # Create Game Master agent
        self.game_master = AssistantAgent(
            name="GameMaster",
            model_client=self.model_client,
            system_message=GAME_MASTER_PROMPTS["GameMaster"]
        )
        
        # Initialize team simulators
        self.cognitive_sim = CognitiveAgentSimulator()
        self.corporate_sim = CorporateAgentSimulator() 
        self.rule_based_sim = WeeklySimulator(SystemConfiguration())
        
        print("✅ Game Master simulator initialized")

    async def set_weekly_parameters(self, week: int, historical_data: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Use Game Master to set parameters for the specified week
        
        Args:
            week: Week number (1-10)
            historical_data: Previous weeks' results for context
            
        Returns:
            Dictionary containing parameters and reasoning
        """
        print(f"🎮 Game Master setting parameters for Week {week}")
        
        # Create context prompt
        context_prompt = f"""
        WEEK {week} PARAMETER SETTING TASK
        
        You are setting parameters for week {week} of a 5-week telco retention simulation.
        
        """
        
        if historical_data:
            context_prompt += f"""
        HISTORICAL CONTEXT:
        Previous weeks' performance data:
        {json.dumps(historical_data, indent=2)}
        
        """
        
        context_prompt += f"""
        Please analyze the business situation and set realistic parameters for Week {week}.
        Consider:
        - This is week {week} of 10, so plan the progression appropriately
        - Create realistic business scenarios that drive parameter changes  
        - Ensure parameters create meaningful challenges for the teams
        - Provide clear reasoning for all parameter choices
        
        Respond with the exact JSON format specified in your system prompt for parameter setting.
        """
        
        # Use single agent directly (no SelectorGroupChat needed for single agent)
        from autogen_agentchat.messages import TextMessage
        from autogen_agentchat.base import Response
        
        # Send message directly to Game Master agent with retry logic
        message = TextMessage(content=context_prompt, source="user")
        
        # Add retry logic for rate limits
        max_retries = 3
        base_delay = 5  # Longer delay for Game Master
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))
                    print(f"🎮 Game Master parameter setting retry after {delay}s delay (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                
                result = await self.game_master.on_messages([message], cancellation_token=None)
                break
                
            except Exception as e:
                if "RateLimitError" in str(type(e)) or "429" in str(e):
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"🎮 Game Master parameter setting rate limit hit, retrying in {delay}s... (attempt {attempt + 1})")
                        continue
                    else:
                        print("🎮 Game Master parameter setting rate limit retries exhausted, using fallback")
                        return self._get_fallback_parameters(week)
                else:
                    print(f"🎮 Game Master parameter setting error: {e}")
                    raise
        
        # Extract JSON from the response
        try:
            # Find JSON in the response
            response_content = result.chat_message.content if hasattr(result, 'chat_message') else str(result)
            
            # Look for JSON block
            if "```json" in response_content:
                json_start = response_content.find("```json") + 7
                json_end = response_content.find("```", json_start)
                json_str = response_content[json_start:json_end].strip()
            elif "{" in response_content and "}" in response_content:
                # Extract JSON from response
                json_start = response_content.find("{")
                json_end = response_content.rfind("}") + 1
                json_str = response_content[json_start:json_end]
            else:
                raise ValueError("No JSON found in Game Master response")
            
            parameters = json.loads(json_str)
            
            # Add conversation log
            parameters["game_master_conversation"] = [
                {"role": "user", "content": context_prompt},
                {"role": "game_master", "content": response_content}
            ]
            
            print(f"✅ Game Master set parameters for Week {week}")
            return parameters
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"❌ Error parsing Game Master response: {e}")
            # Fallback to default parameters
            return self._get_fallback_parameters(week)
    
    async def evaluate_weekly_performance(
        self, 
        week: int, 
        team_results: Dict[str, WeeklySimulationResponse],
        week_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use Game Master to evaluate team performance for the week
        
        Args:
            week: Week number (1-10)
            team_results: Results from all teams (rule_based, cognitive, corporate)
            week_parameters: Parameters that were set for this week
            
        Returns:
            Dictionary containing evaluations and analysis
        """
        print(f"🎮 Game Master evaluating Week {week} performance")
        
        # Prepare team performance data from /simulate/compare (always returns dicts)
        performance_data = {}
        for team_name, result in team_results.items():
            clv_protected = result.get('clv_protected', 0)
            budget_spent = result.get('budget_spent', 0)
            customers_saved = result.get('customers_saved', {})
            allocations = result.get('allocation_decisions', {})
            processing_time = result.get('processing_time_ms', 0)
            
            # Calculate ROI
            roi = (clv_protected / budget_spent) if budget_spent > 0 else 0
            
            performance_data[team_name] = {
                "customers_saved": customers_saved,
                "clv_protected": clv_protected,
                "budget_spent": budget_spent,
                "roi": roi,
                "allocations": allocations,
                "processing_time": processing_time
            }
        
        # Create evaluation prompt
        evaluation_prompt = f"""
        WEEK {week} TEAM PERFORMANCE EVALUATION TASK
        
        You just set these parameters for Week {week}:
        {json.dumps(week_parameters, indent=2)}
        
        Here's how each team performed:
        {json.dumps(performance_data, indent=2)}
        
        Please evaluate each team's performance based on:
        1. How well they adapted to this week's challenges
        2. Efficiency of their resource allocation
        3. Overall decision quality
        4. Evidence of strategic thinking
        
        Provide detailed analysis and scores as specified in your system prompt for team evaluation.
        """
        
        # Use single agent directly for evaluation  
        from autogen_agentchat.messages import TextMessage
        
        # Send message directly to Game Master agent with retry logic
        message = TextMessage(content=evaluation_prompt, source="user")
        
        # Add retry logic for rate limits
        max_retries = 3
        base_delay = 5  # Longer delay for Game Master
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = base_delay * (2 ** (attempt - 1))
                    print(f"🎮 Game Master retry after {delay}s delay (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                
                result = await self.game_master.on_messages([message], cancellation_token=None)
                break
                
            except Exception as e:
                if "RateLimitError" in str(type(e)) or "429" in str(e):
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"🎮 Game Master rate limit hit, retrying in {delay}s... (attempt {attempt + 1})")
                        continue
                    else:
                        print("🎮 Game Master rate limit retries exhausted, using fallback")
                        return self._get_fallback_evaluation(week, team_results)
                else:
                    print(f"🎮 Game Master evaluation error: {e}")
                    raise
        
        # Extract JSON from the response
        try:
            response_content = result.chat_message.content if hasattr(result, 'chat_message') else str(result)
            
            # Look for JSON block
            if "```json" in response_content:
                json_start = response_content.find("```json") + 7
                json_end = response_content.find("```", json_start)
                json_str = response_content[json_start:json_end].strip()
            elif "{" in response_content and "}" in response_content:
                json_start = response_content.find("{")
                json_end = response_content.rfind("}") + 1
                json_str = response_content[json_start:json_end]
            else:
                raise ValueError("No JSON found in Game Master evaluation")
            
            evaluation = json.loads(json_str)
            
            # Add conversation log
            evaluation["game_master_conversation"] = [
                {"role": "user", "content": evaluation_prompt},
                {"role": "game_master", "content": response_content}
            ]
            
            print(f"✅ Game Master evaluated Week {week} performance")
            return evaluation
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"❌ Error parsing Game Master evaluation: {e}")
            return self._get_fallback_evaluation(week, team_results)
    
    def _get_fallback_parameters(self, week: int) -> Dict[str, Any]:
        """Fallback parameters if Game Master fails"""
        return {
            "week": week,
            "business_context": f"Fallback parameters for week {week}",
            "parameters": {
                "customers_at_risk": 100 + (week * 10),
                "weekly_budget": 100000,
                "customer_distribution": {
                    "basic_pct": 80,
                    "standard_pct": 15,
                    "premium_pct": 4,
                    "enterprise_pct": 1
                },
                "risk_distribution": {
                    "low_pct": 40,
                    "medium_pct": 35,
                    "high_pct": 20,
                    "critical_pct": 5
                },
                "success_rates": {
                    "discount_20_pct": 40,
                    "discount_30_pct": 50,
                    "technical_fix": 70,
                    "executive_escalation": 85
                }
            },
            "reasoning": "Fallback parameters due to Game Master parsing error",
            "expected_challenges": f"Standard week {week} challenges",
            "success_metrics": "Standard performance metrics"
        }
    
    def _get_fallback_evaluation(self, week: int, team_results: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback evaluation if Game Master fails"""
        return {
            "week": week,
            "evaluations": {
                "rule_based": {
                    "overall_score": 7,
                    "decision_quality": 7,
                    "resource_efficiency": 7,
                    "adaptability": 5,
                    "strengths": ["Consistent", "Fast"],
                    "improvements": ["Adaptability"],
                    "reasoning": "Fallback evaluation due to parsing error"
                },
                "cognitive": {
                    "overall_score": 8,
                    "decision_quality": 8,
                    "resource_efficiency": 7,
                    "adaptability": 8,
                    "learning_evidence": 7,
                    "strengths": ["Adaptive", "Strategic"],
                    "improvements": ["Efficiency"],
                    "reasoning": "Fallback evaluation due to parsing error"
                },
                "corporate": {
                    "overall_score": 7,
                    "decision_quality": 7,
                    "resource_efficiency": 8,
                    "adaptability": 7,
                    "learning_evidence": 7,
                    "strengths": ["Structured", "Efficient"],
                    "improvements": ["Innovation"],
                    "reasoning": "Fallback evaluation due to parsing error"
                }
            },
            "comparative_insights": "Fallback evaluation - teams performed as expected",
            "week_summary": f"Week {week} completed with fallback evaluation"
        }