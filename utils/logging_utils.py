"""
Logging utilities for capturing agent conversations
"""

import os
from datetime import datetime


async def logged_console(stream, log_file):
    """
    Custom console that both displays and logs all agent messages.
    Based on working implementation from MagneticOne.
    """
    # Ensure log directory exists
    os.makedirs("logs", exist_ok=True)
    
    messages = []
    last_result = None
    
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(f"=== Agent Dialogue Log ===\n")
        f.write(f"Started: {datetime.now().isoformat()}\n")
        f.write("="*50 + "\n\n")
        
        async for message in stream:
            # Log everything to file
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {type(message).__name__}\n")
            
            # Extract content based on message type
            if hasattr(message, 'content'):
                f.write(str(message.content))
            elif hasattr(message, 'message'):
                f.write(str(message.message))
            else:
                f.write(str(message))
            
            f.write("\n" + "-"*40 + "\n")
            f.flush()
            
            messages.append(message)
            last_result = message
            
            # Yield the message to maintain streaming behavior for Console
            yield message
        
        f.write("\n" + "="*50 + "\n")
        f.write(f"Completed: {datetime.now().isoformat()}\n")
        f.write(f"Total messages: {len(messages)}\n")
    
    print(f"\n📝 Full dialogue saved to: {log_file}")


def generate_log_filename(scenario_name: str, agent_type: str = "corporate") -> str:
    """
    Generate a unique log filename based on scenario and timestamp.
    
    Args:
        scenario_name: Name of the scenario being run
        agent_type: Type of agents being used (corporate or cognitive)
        
    Returns:
        Path to the log file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{scenario_name}_{agent_type}_{timestamp}.txt"
    return os.path.join("logs", filename)