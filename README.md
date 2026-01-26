# HF Papers Explorer

A beautiful interactive explorer for Hugging Face "Papers of the Month" with AI-powered tagging and clustering.

## Features

- 📄 **Paper Scraping**: Automatically fetches papers from HF monthly listings
- 🏷️ **AI Tagging**: Uses LLM to generate taxonomy and tag papers
- 📊 **Smart Clustering**: Groups papers by contribution type, task, and modality
- 🎠 **Beautiful UI**: HF-inspired paper cards with smooth horizontal carousel
- 🔍 **Search & Filter**: Find papers by title, abstract, or tags

## Architecture

```
hf-papers-explorer/
├── backend/           # Python FastAPI backend
│   ├── main.py        # API endpoints
│   ├── database.py    # SQLite models & queries
│   ├── scraper.py     # HF paper scraper
│   ├── llm_tagger.py  # LLM taxonomy & tagging
│   └── llm/           # Multi-provider LLM abstraction
│       ├── base.py           # Provider protocol & models
│       ├── config.py         # Configuration management
│       └── providers/        # Provider implementations
│           ├── minimax.py
│           ├── openai.py
│           └── anthropic.py
├── frontend/          # React + Vite frontend
│   └── src/
│       ├── App.tsx           # Main app component
│       ├── api.ts            # API client
│       └── components/       # UI components
│           ├── PaperCard.tsx
│           ├── PaperCarousel.tsx
│           ├── ClusterCard.tsx
│           ├── ClusterView.tsx
│           └── PaperModal.tsx
└── start.sh           # Startup script
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- npm

### Run the app

```bash
# Make the startup script executable
chmod +x start.sh

# Start both backend and frontend
./start.sh
```

Or start them separately:

```bash
# Terminal 1: Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm install
npm run dev
```

### Using the app

1. Open http://localhost:5173 in your browser
2. Select a month from the dropdown
3. Click **"Index"** to scrape and index papers for that month
4. Browse clusters, search papers, and explore!

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/months/{month}/summary` | Get month summary with clusters |
| `GET /api/months/{month}/papers` | Get all papers with filters |
| `GET /api/clusters/{id}/papers` | Get papers in a cluster |
| `GET /api/papers/{id}` | Get paper details |
| `POST /api/reindex/month/{month}` | Trigger paper indexing |
| `GET /api/reindex/status/{month}` | Check indexing status |
| `GET /api/llm/providers` | List available LLM providers |

## Tagging Taxonomy

### Contribution Tags (Primary Axis)
- Benchmark / Evaluation
- Dataset / Data Curation
- Architecture / Model Design
- Training Recipe / Scaling / Distillation
- Post-training / Alignment
- Reasoning / Test-time Compute
- Agents / Tool Use / Workflow
- Multimodal Method
- RAG / Retrieval / Memory
- Safety / Robustness / Interpretability
- Systems / Efficiency
- Survey / Tutorial
- Technical Report / Model Release
- Theory / Analysis

### Modality Tags
- text, vision, video, audio, multimodal, code, 3D

## LLM Integration

The app supports two tagging modes:

1. **Heuristic tagging** (default): Fast keyword-based tagging
2. **LLM tagging**: Uses AI for intelligent taxonomy generation and paper tagging

### Supported Providers

| Provider | Environment Variable | Model |
|----------|---------------------|-------|
| MiniMax | `MINIMAX_API_KEY` | abab6.5s-chat |
| OpenAI | `OPENAI_API_KEY` | gpt-4o |
| Anthropic | `ANTHROPIC_API_KEY` | claude-sonnet-4-20250514 |

### Configuration

```bash
# Set the default provider (optional, defaults to minimax)
export LLM_PROVIDER=openai

# Set API key for your chosen provider
export OPENAI_API_KEY=your_key_here
```

### Usage

```bash
# Use default provider
curl -X POST "http://localhost:8000/api/reindex/month/2025-01?use_llm=true"

# Specify provider explicitly
curl -X POST "http://localhost:8000/api/reindex/month/2025-01?use_llm=true&provider=anthropic"

# Check available providers
curl "http://localhost:8000/api/llm/providers"
```

## Tech Stack

- **Backend**: Python, FastAPI, SQLite, httpx, BeautifulSoup
- **Frontend**: React, TypeScript, Vite, TailwindCSS, Embla Carousel
- **LLM**: MiniMax, OpenAI, or Anthropic Claude (configurable)

## License

MIT
