from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The user's query")
    conversation_id: Optional[str] = Field(
        None, description="Optional conversation ID for follow-ups"
    )


class ToolTrace(BaseModel):
    tool_name: str
    parameters: dict
    result_summary: str
    items_returned: int = 0
    cleaning_steps: list[str] = []
    duration_ms: int = 0
    status: str = "completed"  # "running", "completed", "error"
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    raw_result: Optional[dict] = None


class ChatResponse(BaseModel):
    response: str
    traces: list[ToolTrace] = []
    caveats: list[str] = []
    conversation_id: Optional[str] = None


class BoardStatus(BaseModel):
    board_name: str
    connected: bool
    item_count: Optional[int] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    deals_board: Optional[BoardStatus] = None
    workorders_board: Optional[BoardStatus] = None
