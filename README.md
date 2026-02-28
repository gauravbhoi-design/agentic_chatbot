# Monday.com Business Intelligence Agent

AI-powered BI agent that answers founder-level business queries by querying live Monday.com boards in real-time.

## Architecture

- **Backend**: FastAPI (Python) with async Monday.com GraphQL client
- **Agent**: LangGraph with GPT-4o function calling (5 specialized tools)
- **Frontend**: Vue.js 3 (Composition API) with split-panel chat + trace UI
- **Data Source**: Monday.com GraphQL API — live queries, no caching

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Monday.com API token
- OpenAI API key
- Board IDs for Deals and Work Orders boards

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env .env.local
# Edit .env with your actual API keys and board IDs:
#   MONDAY_API_KEY=your_monday_api_token
#   OPENAI_API_KEY=your_openai_api_key
#   DEALS_BOARD_ID=your_deals_board_id
#   WORKORDERS_BOARD_ID=your_workorders_board_id

# Run the server
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server (proxies API calls to localhost:8000)
npm run dev
```

Open http://localhost:5173 in your browser.

### Production Build

```bash
cd frontend
npm run build
# Static files output to frontend/dist/
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Main query endpoint (full response) |
| `/api/chat/stream` | POST | SSE streaming with real-time tool traces |
| `/api/health` | GET | Health check + board connectivity |
| `/api/boards/status` | GET | Monday.com board status details |

## Agent Tools

1. **query_deals_board** — Query deals pipeline with filters (status, sector, stage, owner, dates)
2. **query_workorders_board** — Query work orders with filters (execution status, billing, sector)
3. **cross_board_analysis** — Join deals + work orders by deal name for lifecycle analysis
4. **aggregate_metrics** — Calculate SUM, COUNT, AVG, WIN_RATE, COLLECTION_RATE grouped by dimension
5. **get_data_summary** — High-level board overview with key metrics and data quality info

## Sample Queries

- "How's our pipeline looking?"
- "What's our win rate by sector?"
- "How's the mining sector performing end-to-end?"
- "Which owner is bringing in the most revenue?"
- "How much revenue is stuck in collections?"
- "Show me deals closing this quarter"
- "Compare renewables vs mining performance"
- "Any deals at risk?"

## Data Handling

The agent includes a data resilience layer that automatically:
- Removes duplicate header rows from Deals board
- Fixes "BIlled" → "Billed" typo in Work Orders
- Parses mixed date formats safely
- Cleans quantity strings ("5360 HA" → 5360)
- Generates data quality caveats for every response
- Tracks and reports null rates per field

## Project Structure

```
monday-bi-agent/
├── backend/
│   ├── main.py              # FastAPI app + endpoints
│   ├── config.py            # Environment variables + board mappings
│   ├── monday_client.py     # Monday.com GraphQL client with pagination
│   ├── data_cleaner.py      # Data resilience/normalization layer
│   ├── agent/
│   │   ├── graph.py         # LangGraph agent definition
│   │   ├── state.py         # Agent state schema
│   │   ├── tools.py         # 5 tool definitions with Monday.com integration
│   │   └── prompts.py       # System prompt with domain knowledge
│   ├── models/
│   │   └── schemas.py       # Pydantic request/response models
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.vue
│   │   ├── components/      # ChatPanel, TracePanel, MessageBubble, etc.
│   │   ├── stores/chat.js   # Pinia store for reactive state
│   │   └── services/api.js  # API client with SSE support
│   └── package.json
├── Decision_Log.md
└── README.md
```
