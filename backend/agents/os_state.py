"""
State representation for OS / Laptop Multi-Agent Automation.
"""

from typing import TypedDict, List, Dict, Any, Optional

class ActionRecord(TypedDict):
    agent: str
    action_type: str
    command_or_target: str
    result: Any
    status: str
    timestamp: float

class OSAutomationState(TypedDict, total=False):
    task_id: str
    user_goal: str
    classified_intent: str
    required_agents: List[str]
    plan: List[Dict[str, Any]]
    current_step_index: int
    active_agent: str
    
    # Perception / Environment state
    active_window: Dict[str, Any]
    last_screenshot_path: Optional[str]
    system_resources: Dict[str, Any]
    
    # Execution & History
    actions_history: List[ActionRecord]
    trace_log: List[Dict[str, Any]]
    
    # Safety & Verification
    risk_score: float
    risk_level: str
    hitl_required: bool
    verification_status: str
    verification_details: Dict[str, Any]
    
    # Completion status
    is_completed: bool
    final_summary: str
    error: Optional[str]
