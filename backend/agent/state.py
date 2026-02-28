from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
import operator


class AgentState(TypedDict):
    """State schema for the LangGraph BI agent.

    Attributes:
        messages: Conversation history (accumulated via operator.add)
        tool_traces: List of ToolTrace dicts for the trace panel
        data_caveats: Data quality warnings to display to the user
        current_query: The user's original question text
    """
    messages: Annotated[Sequence[BaseMessage], operator.add]
    tool_traces: list
    data_caveats: list
    current_query: str
