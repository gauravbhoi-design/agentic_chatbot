import json
import time
from typing import Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.prompts import SYSTEM_PROMPT
from agent.tools import ALL_TOOLS
from config import OPENAI_API_KEY


# Initialize the LLM with tool binding
llm = ChatOpenAI(
    model="gpt-4o",
    api_key=OPENAI_API_KEY,
    temperature=0,
    streaming=True,
)

# Bind tools to the LLM so it knows what's available
llm_with_tools = llm.bind_tools(ALL_TOOLS)

# Build a tool name → function lookup
tool_map = {t.name: t for t in ALL_TOOLS}


async def reasoning_node(state: AgentState) -> dict:
    """LLM reasoning node — decides whether to call a tool or respond."""
    messages = list(state["messages"])

    # Inject system prompt if not already present
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}


async def tool_execution_node(state: AgentState) -> dict:
    """Execute tool calls from the LLM and return results."""
    last_message = state["messages"][-1]
    tool_calls = last_message.tool_calls

    new_messages = []
    new_traces = []
    new_caveats = []

    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        call_id = tool_call["id"]

        start_time = time.time()
        trace = {
            "tool_name": tool_name,
            "parameters": tool_args,
            "status": "running",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

        try:
            # Look up and execute the tool
            tool_fn = tool_map.get(tool_name)
            if not tool_fn:
                raise ValueError(f"Unknown tool: {tool_name}")

            result = await tool_fn.ainvoke(tool_args)

            elapsed = round((time.time() - start_time) * 1000)

            # Extract trace information from the result
            if isinstance(result, dict):
                items_count = (
                    result.get("total_deals")
                    or result.get("total_work_orders")
                    or result.get("common_deal_count")
                    or 0
                )
                cleaning_steps = result.get("cleaning_steps", [])
                caveats = result.get("caveats", [])
                api_ms = result.get("api_time_ms", 0)

                trace.update({
                    "status": "completed",
                    "items_returned": items_count,
                    "cleaning_steps": cleaning_steps,
                    "duration_ms": elapsed,
                    "api_time_ms": api_ms,
                    "result_summary": f"{items_count} items returned in {elapsed}ms",
                })

                new_caveats.extend(caveats)
            else:
                trace.update({
                    "status": "completed",
                    "duration_ms": elapsed,
                    "result_summary": str(result)[:200],
                })

            # Truncate large result sets before sending back to LLM
            result_for_llm = _truncate_result(result)

            new_messages.append(
                ToolMessage(
                    content=json.dumps(result_for_llm, default=str),
                    tool_call_id=call_id,
                )
            )

        except Exception as e:
            elapsed = round((time.time() - start_time) * 1000)
            trace.update({
                "status": "error",
                "duration_ms": elapsed,
                "result_summary": f"Error: {str(e)}",
            })
            new_messages.append(
                ToolMessage(
                    content=json.dumps({"error": str(e)}),
                    tool_call_id=call_id,
                )
            )

        new_traces.append(trace)

    return {
        "messages": new_messages,
        "tool_traces": state.get("tool_traces", []) + new_traces,
        "data_caveats": list(set(state.get("data_caveats", []) + new_caveats)),
    }


def should_continue(state: AgentState) -> Literal["tools", "end"]:
    """Conditional edge: route to tool execution or end."""
    last_message = state["messages"][-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return "end"


def _truncate_result(result: dict, max_items: int = 50) -> dict:
    """Truncate large result sets to avoid overwhelming the LLM context.

    Keeps aggregated data intact but limits individual item lists.
    """
    if not isinstance(result, dict):
        return result

    truncated = {}
    for key, value in result.items():
        if key in ("deals", "work_orders", "lifecycle"):
            if isinstance(value, list) and len(value) > max_items:
                truncated[key] = value[:max_items]
                truncated[f"{key}_truncated"] = True
                truncated[f"{key}_total"] = len(value)
            else:
                truncated[key] = value
        else:
            truncated[key] = value
    return truncated


def build_graph() -> StateGraph:
    """Build and compile the LangGraph agent."""
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("reasoning", reasoning_node)
    workflow.add_node("tools", tool_execution_node)

    # Set entry point
    workflow.set_entry_point("reasoning")

    # Add conditional edges
    workflow.add_conditional_edges(
        "reasoning",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        },
    )

    # After tool execution, loop back to reasoning
    workflow.add_edge("tools", "reasoning")

    return workflow.compile()


# Compiled graph instance
graph = build_graph()
