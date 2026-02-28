import json
import asyncio
import uuid
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage, AIMessage

from models.schemas import ChatRequest, ChatResponse, HealthResponse, BoardStatus, ToolTrace
from agent.graph import graph
from monday_client import monday_client
from config import DEALS_BOARD_ID, WORKORDERS_BOARD_ID

# Path to the built Vue frontend
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"


# Store conversation histories for follow-up support
conversations: dict[str, list] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    print("Monday.com BI Agent starting up...")
    print(f"Deals Board ID: {DEALS_BOARD_ID}")
    print(f"Work Orders Board ID: {WORKORDERS_BOARD_ID}")
    if FRONTEND_DIR.is_dir():
        print(f"Serving frontend from: {FRONTEND_DIR}")
    else:
        print(f"Frontend not built yet ({FRONTEND_DIR}). Run: cd frontend && npm run build")
    yield
    print("Monday.com BI Agent shutting down...")


app = FastAPI(
    title="Monday.com BI Agent",
    description="AI-powered Business Intelligence Agent that queries live Monday.com boards",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint — runs LangGraph agent and returns response + traces."""
    try:
        # Get or create conversation
        conv_id = request.conversation_id or str(uuid.uuid4())
        history = conversations.get(conv_id, [])

        # Build messages with conversation history
        messages = history + [HumanMessage(content=request.message)]

        # Run the agent
        result = await graph.ainvoke({
            "messages": messages,
            "tool_traces": [],
            "data_caveats": [],
            "current_query": request.message,
        })

        # Extract the final response
        final_message = result["messages"][-1]
        response_text = final_message.content if hasattr(final_message, "content") else str(final_message)

        # Update conversation history (keep last 20 messages to avoid unbounded growth)
        conversations[conv_id] = (
            messages + [AIMessage(content=response_text)]
        )[-20:]

        # Build trace objects
        traces = [
            ToolTrace(
                tool_name=t.get("tool_name", "unknown"),
                parameters=t.get("parameters", {}),
                result_summary=t.get("result_summary", ""),
                items_returned=t.get("items_returned", 0),
                cleaning_steps=t.get("cleaning_steps", []),
                duration_ms=t.get("duration_ms", 0),
                status=t.get("status", "completed"),
            )
            for t in result.get("tool_traces", [])
        ]

        # Deduplicate caveats
        caveats = list(set(result.get("data_caveats", [])))

        return ChatResponse(
            response=response_text,
            traces=traces,
            caveats=caveats,
            conversation_id=conv_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """SSE streaming endpoint for real-time tool traces and token streaming."""
    async def event_generator():
        try:
            conv_id = request.conversation_id or str(uuid.uuid4())
            history = conversations.get(conv_id, [])
            messages = history + [HumanMessage(content=request.message)]

            # Send conversation ID
            yield f"data: {json.dumps({'type': 'session', 'conversation_id': conv_id})}\n\n"

            accumulated_response = ""

            async for event in graph.astream_events(
                {
                    "messages": messages,
                    "tool_traces": [],
                    "data_caveats": [],
                    "current_query": request.message,
                },
                version="v2",
            ):
                event_type = event.get("event")

                if event_type == "on_tool_start":
                    tool_data = {
                        "type": "tool_start",
                        "tool": event.get("name", "unknown"),
                        "input": event.get("data", {}).get("input", {}),
                        "run_id": event.get("run_id", ""),
                    }
                    yield f"data: {json.dumps(tool_data, default=str)}\n\n"

                elif event_type == "on_tool_end":
                    output = event.get("data", {}).get("output", "")
                    # Parse output to extract summary info
                    summary = ""
                    items = 0
                    if isinstance(output, str):
                        try:
                            parsed = json.loads(output)
                            items = (
                                parsed.get("total_deals")
                                or parsed.get("total_work_orders")
                                or parsed.get("common_deal_count")
                                or 0
                            )
                            summary = f"{items} items returned"
                        except (json.JSONDecodeError, AttributeError):
                            summary = str(output)[:200]
                    elif isinstance(output, dict):
                        items = (
                            output.get("total_deals")
                            or output.get("total_work_orders")
                            or output.get("common_deal_count")
                            or 0
                        )
                        summary = f"{items} items returned"

                    tool_data = {
                        "type": "tool_end",
                        "tool": event.get("name", "unknown"),
                        "summary": summary,
                        "items": items,
                        "run_id": event.get("run_id", ""),
                    }
                    yield f"data: {json.dumps(tool_data, default=str)}\n\n"

                elif event_type == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        # Only stream text content, not tool calls
                        if not (hasattr(chunk, "tool_calls") and chunk.tool_calls):
                            accumulated_response += chunk.content
                            yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"

            # Store conversation
            if accumulated_response:
                conversations[conv_id] = (
                    messages + [AIMessage(content=accumulated_response)]
                )[-20:]

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/health", response_model=HealthResponse)
async def health():
    """Health check — verifies Monday.com board connectivity."""
    deals_status = None
    wo_status = None

    if DEALS_BOARD_ID:
        result = await monday_client.check_connection(DEALS_BOARD_ID)
        deals_status = BoardStatus(
            board_name=result.get("board_name", "Deals"),
            connected=result.get("connected", False),
            item_count=result.get("item_count"),
            error=result.get("error"),
        )

    if WORKORDERS_BOARD_ID:
        result = await monday_client.check_connection(WORKORDERS_BOARD_ID)
        wo_status = BoardStatus(
            board_name=result.get("board_name", "Work Orders"),
            connected=result.get("connected", False),
            item_count=result.get("item_count"),
            error=result.get("error"),
        )

    overall = "ok"
    if deals_status and not deals_status.connected:
        overall = "degraded"
    if wo_status and not wo_status.connected:
        overall = "degraded"
    if (deals_status and not deals_status.connected and
            wo_status and not wo_status.connected):
        overall = "unhealthy"

    return HealthResponse(
        status=overall,
        deals_board=deals_status,
        workorders_board=wo_status,
    )


@app.get("/api/boards/status")
async def boards_status():
    """Check Monday.com connection and board accessibility."""
    results = {}
    if DEALS_BOARD_ID:
        results["deals"] = await monday_client.check_connection(DEALS_BOARD_ID)
    if WORKORDERS_BOARD_ID:
        results["workorders"] = await monday_client.check_connection(WORKORDERS_BOARD_ID)
    return results


# ---------- Serve Vue frontend (production) ----------
if FRONTEND_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="static")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Catch-all: serve index.html for any non-API route (SPA client routing)."""
        file_path = FRONTEND_DIR / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)
