# Decision Log — Monday.com BI Agent

## Architecture Decisions

### 1. Agent Framework: LangGraph
**Why**: Provides explicit control over agent workflow with a graph-based architecture of nodes and edges. Unlike simple ReAct loops, LangGraph enables:
- **Conditional routing** — the `should_continue` edge decides whether to execute tools or generate the final response, preventing infinite loops
- **State persistence** — `AgentState` carries conversation history, tool traces, and data caveats across turns, supporting follow-up queries
- **Streaming support** — `astream_events` emits tool_start/tool_end/token events in real-time for the trace panel
- **Multi-tool orchestration** — the agent can chain multiple API calls (e.g., cross-board analysis) in a single turn

**Trade-off**: Slightly more boilerplate than a simple `chat.completions` loop, but the control and observability are essential for a production BI agent.

### 2. LLM: OpenAI GPT-4o
**Why**: Best-in-class function calling reliability. GPT-4o consistently:
- Selects the correct tool based on nuanced business questions
- Generates well-structured parameters (correct enum values, date formats)
- Produces rich markdown responses with tables, bold numbers, and actionable insights
- Handles multi-step reasoning (e.g., "compare sectors" → calls aggregate_metrics twice, then synthesizes)

**Trade-off**: Higher cost per token than GPT-4o-mini, but accuracy on tool selection is critical — a wrong tool call wastes a Monday.com API round-trip.

### 3. Backend: FastAPI
**Why**: Native async support for non-blocking Monday.com API calls. Key benefits:
- `async/await` throughout — concurrent board queries in `cross_board_analysis`
- Built-in Pydantic validation for request/response schemas
- SSE streaming via `StreamingResponse` for real-time tool traces
- Auto-generated OpenAPI docs at `/docs` for debugging

**Trade-off**: Python's GIL limits true parallelism, but I/O-bound API calls benefit fully from async.

### 4. Frontend: Vue.js 3 (Composition API)
**Why**: The Composition API enables clean reactive state management for real-time SSE updates:
- `ref()` and `computed()` provide fine-grained reactivity for streaming tokens
- Pinia store centralizes chat state, traces, and connection status
- Component architecture maps cleanly to the split-panel layout
- Lighter bundle than React for this scope

**Trade-off**: Smaller ecosystem than React, but Vue's reactivity model is ideal for real-time SSE data flows.

### 5. Live API Calls (No Caching)
**Why**: Assignment requirement — every query triggers fresh Monday.com GraphQL calls. This ensures:
- Data freshness for a BI tool (stale data defeats the purpose)
- Real tool traces showing actual API calls (not cache hits)

**Trade-off**: Higher latency (300-500ms per API call + pagination) and potential rate limiting. Mitigated by cursor-based pagination and retry logic with exponential backoff.

### 6. Data Resilience Layer
**Why**: The Monday.com data has documented quality issues that would corrupt analysis if not handled:
- **Header rows as data** — 2 rows where column values equal column names
- **"BIlled" typo** — would cause incorrect billing status aggregations
- **Mixed date formats** — datetime objects and strings in the same column
- **52% null deal values** — totals would be wildly inaccurate without caveats
- **"5360 HA" quantities** — would fail numeric aggregation without parsing

Cleaning happens at query time (not import time) to handle any future data changes.

### 7. SSE Streaming over WebSocket
**Why**: Server-Sent Events provide unidirectional server→client streaming, which is all we need (the client sends queries via POST, not over the stream). SSE is simpler to implement, works through proxies/CDNs, and auto-reconnects natively.

**Trade-off**: No bidirectional communication, but our architecture doesn't require it — queries go through `POST /api/chat/stream` and events flow back via SSE.

### 8. Chart.js for Visualizations
**Why**: Lightweight (~60KB gzipped) with good Vue.js integration via `vue-chartjs`. Supports bar charts, which cover the primary visualization needs (sector comparisons, stage breakdowns).

**Trade-off**: Less powerful than D3.js or ECharts, but we don't need complex visualizations — clean bar charts and tables are sufficient for BI dashboards.

## Data Architecture Decisions

### Cross-Board Join Strategy
- **Join key**: Deal name (`name` in Deals ↔ `Deal name masked` in Work Orders)
- **NOT joined on**: Client codes (different namespaces: COMPANY vs WOCOMPANY)
- **Shared dimensions**: Owner codes (OWNER_001-007), Sectors (6 common)
- **52 matching deals** between boards, enabling full lifecycle analysis

### Caveat Generation Strategy
- Caveats are auto-generated based on null rates in the queried subset
- Every response with >20% null rates on key fields includes warnings
- Users see exactly how complete their data is for every insight

## Trade-offs Summary

| Decision | Chose | Over | Reason |
|----------|-------|------|--------|
| Streaming | SSE | WebSocket | Simpler, unidirectional sufficient |
| GraphQL | Direct client | MCP Server | More control over query structure |
| Charts | Chart.js | D3/ECharts | Lightweight, sufficient for bar charts |
| State | Pinia | Vuex | Modern, Composition API native |
| Dates | String parsing | Library | Fewer dependencies, known formats |
