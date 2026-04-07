from pydantic import BaseModel, Field
from typing import Literal, Optional, List, Dict, Any

class Action(BaseModel):
    tool: Literal["query_crm", "search_kb", "ask_customer", "resolve_ticket"] = Field(...)
    field: Optional[str] = Field(None)
    query: Optional[str] = Field(None)
    question: Optional[str] = Field(None)
    solution_code: Optional[str] = Field(None)

class Observation(BaseModel):
    current_patience: float
    last_action_result: str
    conversation_history: List[str]

class Reward(BaseModel):
    value: float
    is_terminal: bool
    info: Dict[str, Any]

class State(BaseModel):
    ticket_id: str
    target_solution: str
    patience: float
    history: List[str]
    is_done: bool
    customer_turn: int