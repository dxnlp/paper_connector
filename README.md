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
│   └── llm_tagger.py  # LLM taxonomy & tagging
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
2. **LLM tagging**: Uses MiniMax model for intelligent taxonomy generation and tagging

To enable LLM tagging, set `MINIMAX_API_KEY` environment variable and use `?use_llm=true` when triggering reindex.

## Tech Stack

- **Backend**: Python, FastAPI, SQLite, httpx, BeautifulSoup
- **Frontend**: React, TypeScript, Vite, TailwindCSS, Embla Carousel
- **LLM**: MiniMax API (optional)

## License

MIT
