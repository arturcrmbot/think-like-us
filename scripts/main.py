"""
Telco Retention Cognitive Architecture - Main
Supports both corporate and cognitive agent styles with conversation logging
"""

import os
import json
import asyncio
import argparse
from datetime import datetime
from dotenv import load_dotenv

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

# Import both agent configurations
from agents.corporate_agents import AGENT_PROMPTS as CORPORATE_PROMPTS
from agents.cognitive_agents import AGENT_PROMPTS as COGNITIVE_PROMPTS
from utils.logging_utils import logged_console, generate_log_filename

# Load environment variables
load_dotenv()


def load_scenario(scenario_name):
    """Load scenario from JSON file"""
    scenario_path = f"scenarios/{scenario_name}.json"
    if not os.path.exists(scenario_path):
        raise ValueError(f"Scenario '{scenario_name}' not found at {scenario_path}")
    
    with open(scenario_path, 'r') as f:
        return json.load(f)


def create_corporate_agents(model_client):
    """Create corporate-style agents using original configuration"""
    agents = []
    
    # Iterate through the dictionary items (key-value pairs)
    for agent_name, agent_prompt in CORPORATE_PROMPTS.items():
        agent = AssistantAgent(
            name=agent_name,
            model_client=model_client,
            system_message=agent_prompt
        )
        agents.append(agent)
    
    return agents


def create_cognitive_agents(model_client):
    """Create cognitive agents"""
    agents = []
    
    for agent_name, agent_prompt in COGNITIVE_PROMPTS.items():
        agent = AssistantAgent(
            name=agent_name,
            model_client=model_client,
            system_message=agent_prompt
        )
        agents.append(agent)
    
    return agents


async def run_corporate_scenario(model_client, scenario, enable_logging=True):
    """Run scenario with corporate-style agents"""
    
    print(f"\n{'='*60}")
    print(f"CORPORATE SCENARIO: {scenario['name']}")
    print(f"{'='*60}")
    print(f"{scenario['description']}")
    print()
    
    # Create agents
    agents = create_corporate_agents(model_client)
    
    # Get selector prompt from scenario or use default
    selector_prompt = scenario.get('selector_prompt', """Select who speaks next from {participants}.

{roles}

{history}""")
    
    # Get termination settings
    termination_keyword = scenario.get('termination_keyword', 'ACTION_PLAN_READY')
    max_messages = scenario.get('max_messages', 10)  # Default to 10 as backup
    
    # Simple termination: keyword OR max messages as backup
    termination_condition = TextMentionTermination(termination_keyword) | MaxMessageTermination(max_messages)
    
    # Setup group chat
    retention_team = SelectorGroupChat(
        participants=agents,
        model_client=model_client,
        selector_prompt=selector_prompt,
        termination_condition=termination_condition,
        allow_repeated_speaker=True
    )
    
    # Get initial prompt from scenario
    initial_prompt = scenario['initial_prompt']
    
    # Run planning session
    print("\n" + "="*60)
    print("RETENTION PLANNING SESSION")
    print("="*60)
    print()
    
    # Run with logging if enabled
    if enable_logging:
        log_file = generate_log_filename(scenario['name'], 'corporate')
        print(f"Logging conversation to: {log_file}\n")
        
        print("Team Discussion:")
        print("-" * 60)
        result = await Console(
            logged_console(retention_team.run_stream(task=initial_prompt), log_file)
        )
        print("-" * 60)
    else:
        if scenario.get('show_conversation', True):
            print("Team Discussion:")
            print("-" * 60)
            result = await Console(retention_team.run_stream(task=initial_prompt))
            print("-" * 60)
        else:
            result = await retention_team.run(task=initial_prompt)
    
    # Extract action plan
    action_plan = extract_action_plan(result, termination_keyword)
    
    # Create result summary
    retention_result = {
        "scenario": scenario['name'],
        "agent_type": "corporate",
        "timestamp": datetime.now().isoformat(),
        "action_plan": action_plan,
        "messages_exchanged": len(result.messages) if hasattr(result, 'messages') else "N/A"
    }
    
    return retention_result


async def run_cognitive_scenario(model_client, scenario, enable_logging=True):
    """Run scenario with cognitive-style agents"""
    
    print(f"\n{'='*60}")
    print(f"COGNITIVE SCENARIO: {scenario['name']}")
    print(f"{'='*60}")
    print(f"{scenario['description']}")
    print()
    
    # Create cognitive agents
    agents = create_cognitive_agents(model_client)
    
    # Get termination settings
    termination_keyword = scenario.get('termination_keyword', 'ACTION_PLAN_READY')
    max_messages = scenario.get('max_messages', 10)
    
    # Simple termination: keyword OR max messages as backup
    termination_condition = TextMentionTermination(termination_keyword) | MaxMessageTermination(max_messages)
    
    # Get selector prompt from scenario or use default
    selector_prompt = scenario.get('selector_prompt', """Select who speaks next from {participants}.

{roles}

{history}""")
    
    # Setup group chat
    cognitive_team = SelectorGroupChat(
        participants=agents,
        model_client=model_client,
        selector_prompt=selector_prompt,
        termination_condition=termination_condition,
        allow_repeated_speaker=True
    )
    
    # Get initial prompt from scenario
    initial_prompt = scenario['initial_prompt']
    
    # Run planning session
    print("\n" + "="*60)
    print("COGNITIVE PLANNING SESSION")
    print("="*60)
    print()
    
    # Run with logging if enabled
    if enable_logging:
        log_file = generate_log_filename(scenario['name'], 'cognitive')
        print(f"Logging conversation to: {log_file}\n")
        
        print("Team Discussion:")
        print("-" * 60)
        result = await Console(
            logged_console(cognitive_team.run_stream(task=initial_prompt), log_file)
        )
        print("-" * 60)
    else:
        if scenario.get('show_conversation', True):
            print("Team Discussion:")
            print("-" * 60)
            result = await Console(cognitive_team.run_stream(task=initial_prompt))
            print("-" * 60)
        else:
            result = await cognitive_team.run(task=initial_prompt)
    
    # Extract action plan
    action_plan = extract_action_plan(result, termination_keyword)
    
    # Create result summary
    retention_result = {
        "scenario": scenario['name'],
        "agent_type": "cognitive",
        "timestamp": datetime.now().isoformat(),
        "action_plan": action_plan,
        "messages_exchanged": len(result.messages) if hasattr(result, 'messages') else "N/A"
    }
    
    return retention_result


def extract_action_plan(result, termination_keyword):
    """Extract action plan from result messages"""
    action_plan = "No plan finalized"
    messages_to_check = result.messages if hasattr(result, 'messages') else []
    
    for message in messages_to_check:
        if termination_keyword in message.content:
            if "SAVE THESE" in message.content or "Total" in message.content:
                keyword_pos = message.content.find(termination_keyword)
                action_plan = message.content[:keyword_pos].strip()
            else:
                keyword_pos = message.content.find(termination_keyword)
                plan_start = keyword_pos + len(termination_keyword)
                if plan_start < len(message.content) and message.content[plan_start] == ':':
                    plan_start += 1
                action_plan = message.content[plan_start:].strip()
            
            if not action_plan:
                action_plan = message.content.replace(termination_keyword, "").strip()
            break
    
    return action_plan



async def main():
    """Main entry point with CLI argument parsing"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run telco retention scenarios')
    parser.add_argument('--scenario', type=str, default='single_customer',
                       help='Scenario name (JSON file in scenarios/ folder)')
    parser.add_argument('--agents', type=str, default='corporate',
                       choices=['corporate', 'cognitive', 'both'],
                       help='Agent style to use')
    parser.add_argument('--no-log', action='store_true',
                       help='Disable conversation logging')
    parser.add_argument('--list', action='store_true',
                       help='List available scenarios')
    parser.add_argument('--max-messages', type=int, default=None,
                       help='Override scenario max messages setting')
    
    args = parser.parse_args()
    
    # List scenarios if requested
    if args.list:
        print("\nAvailable scenarios:")
        for file in os.listdir('scenarios'):
            if file.endswith('.json'):
                print(f"  - {file[:-5]}")
        return
    
    print("="*60)
    print("TELCO CHURN PREVENTION - COGNITIVE ARCHITECTURE")
    print("="*60)
    print()
    
    # Load scenario
    try:
        scenario = load_scenario(args.scenario)
    except ValueError as e:
        print(f"Error: {e}")
        print("\nAvailable scenarios:")
        for file in os.listdir('scenarios'):
            if file.endswith('.json'):
                print(f"  - {file[:-5]}")
        return
    
    # Apply CLI overrides
    if args.max_messages is not None:
        scenario['max_messages'] = args.max_messages
    
    # Create model client
    print("Initializing Azure OpenAI client...")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    model_name = os.getenv("AZURE_OPENAI_MODEL_NAME")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-01-preview")
    
    model_capabilities = {
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "structured_output": True
    }
    
    model_client = AzureOpenAIChatCompletionClient(
        azure_endpoint=endpoint,
        api_key=api_key,
        model=model_name,
        api_version=api_version,
        model_capabilities=model_capabilities
    )
    
    enable_logging = not args.no_log
    
    # Run scenarios based on agent type
    if args.agents == 'both':
        print("\n" + "="*60)
        print("Running BOTH agent styles for comparison")
        print("="*60)
        
        # Run corporate version
        corporate_result = await run_corporate_scenario(model_client, scenario, enable_logging)
        
        print("\n" + "="*60)
        print("Switching to COGNITIVE agents")
        print("="*60)
        
        # Run cognitive version
        cognitive_result = await run_cognitive_scenario(model_client, scenario, enable_logging)
        
        # Print comparison
        print("\n" + "="*60)
        print("COMPARISON RESULTS")
        print("="*60)
        print("\nCORPORATE APPROACH:")
        print(json.dumps(corporate_result, indent=2))
        print("\nCOGNITIVE APPROACH:")
        print(json.dumps(cognitive_result, indent=2))
        
    elif args.agents == 'cognitive':
        result = await run_cognitive_scenario(model_client, scenario, enable_logging)
        print("\n" + "="*60)
        print("COGNITIVE RETENTION PLAN")
        print("="*60)
        print(json.dumps(result, indent=2))
        
    else:  # corporate (default)
        result = await run_corporate_scenario(model_client, scenario, enable_logging)
        print("\n" + "="*60)
        print("CORPORATE RETENTION PLAN")
        print("="*60)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())