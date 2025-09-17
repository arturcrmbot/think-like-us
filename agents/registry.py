"""
Simple team registry for telco retention agent teams.
Single source of truth for all available teams.
"""

from backend.agent_integration import CognitiveAgentSimulator, CorporateAgentSimulator

# Registry of all available agent teams
AVAILABLE_TEAMS = {
    "cognitive": CognitiveAgentSimulator,
    "corporate": CorporateAgentSimulator,
    # Add new teams here:
    # "hybrid": HybridAgentSimulator,
    # "specialist": SpecialistAgentSimulator,
}