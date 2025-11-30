"""
Simulation Types: Enumeration of available simulation modeling approaches
"""
from enum import Enum


class SimulationType(Enum):
    """
    Available simulation modeling approaches.
    
    - AGENT_BASED: Time-stepped agent-based simulation (default)
    - DISCRETE_EVENT: Event-driven simulation with event queue
    - MONTE_CARLO: Statistical simulation with multiple runs
    - MARKOV_CHAIN: Probabilistic state transition modeling
    """
    AGENT_BASED = "agent_based"
    DISCRETE_EVENT = "discrete_event"
    MONTE_CARLO = "monte_carlo"
    MARKOV_CHAIN = "markov_chain"

