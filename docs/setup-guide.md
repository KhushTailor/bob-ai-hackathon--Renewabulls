# Setup Guide

> **This file is read by the automated evaluation pipeline. Be precise and complete.**

## Prerequisites

Before you begin, ensure you have the following installed:

- [ ] Python 3.11 or higher (`python --version`)
- [ ] Node.js 18 or higher (`node --version`)
- [ ] pip (`pip --version`)
- [ ] npm (`npm --version`)
- [ ] Git

**IBM Cloud (optional):**
- An IBM Cloud account with access to watsonx.ai is required only if you want to enable the Granite AI features.
- All five GridPulse features work without IBM Cloud credentials using the built-in fallbacks.

---

## Environment Variables

Copy `.env.example` to `.env` inside the `src/` directory:

```bash
cd src
cp .env.example .env
```

Open `.env` and fill in the values:

| Variable | Description | Required |
|---|---|---|
| `WATSONX_API_KEY` | IBM Cloud API key with watsonx.ai access | Only if WATSONX_*_ENABLED=true |
| `WATSONX_PROJECT_ID` | watsonx.ai project ID | Only if WATSONX_*_ENABLED=true |
| `WATSONX_URL` | watsonx.ai endpoint URL (e.g. `https://us-south.ml.cloud.ibm.com`) | Only if WATSONX_*_ENABLED=true |
| `WATSONX_GRANITE_TTM_ENABLED` | `true` to use Granite time-series for demand forecast; `false` for STL fallback | No (default: `false`) |
| `WATSONX_BRIEF_ENABLED` | `true` to use Granite Instruct for operator brief; `false` for template | No (default: `false`) |
| `APP_PORT` | Backend port (default: `8000`) | No |
| `GRID_DATA_PATH` | Path to CSV relative to `src/` (default: `data/grid_data.csv`) | No |

**To run the full demo without IBM Cloud:** leave both `WATSONX_*_ENABLED` as `false`.

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/KhushTailor/bob-ai-hackathon--Renewabulls-.git
cd bob-ai-hackathon--Renewabulls-

# 2. Install Python dependencies
cd src
pip install -r requirements.txt

# 3. Generate the dataset
python data/generate_dataset.py
# This creates src/data/grid_data.csv (~3 MB, 17,520 rows, takes ~10 seconds)

# 4. Configure environment
cp .env.example .env
# Edit .env if you have IBM Cloud credentials; otherwise defaults are fine

# 5. Install frontend dependencies
cd frontend
npm install
cd ..
```

---

## Running the Application

Open two terminal windows:

**Terminal 1 — Backend API:**
```bash
cd src
uvicorn backend.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`
API documentation: `http://localhost:8000/docs`

**Terminal 2 — Frontend Dashboard:**
```bash
cd src/frontend
npm run dev
```

The dashboard will be available at `http://localhost:5173`

---

## Running Tests

```bash
cd src
pytest tests/ -v
```

All tests pass without IBM Cloud credentials. The watsonx.ai integration is mocked in tests.

Expected output: all tests pass, no credentials required.

---

## Verifying the Installation

1. Open `http://localhost:8000/health` — should return `{"status": "ok"}`
2. Open `http://localhost:8000/docs` — FastAPI interactive docs should load
3. Open `http://localhost:5173` — the GridPulse dashboard should load with 4 KPI cards

---

## IBM Bob MCP Server (optional — enables live Bob queries)

If you have IBM Bob installed, you can enable live GridPulse queries from Bob's chat:

```bash
cd src/mcp-server
npm install
npm run build
```

Then register the server in your Bob settings. See [`docs/ibm-bob-integration.md`](ibm-bob-integration.md) for the registration configuration.

Once registered, you can type in Bob's chat:
- *"What is the current grid status?"*
- *"Are there any active alerts?"*
- *"What does the AI operator brief say?"*

---

## Troubleshooting

| Issue | Solution |
|---|---|
| `ModuleNotFoundError` on backend start | Run `pip install -r requirements.txt` from the `src/` directory |
| `grid_data.csv not found` | Run `python data/generate_dataset.py` from `src/` |
| Frontend shows blank screen | Check that the backend is running on port 8000; check browser console for CORS errors |
| `npm install` fails | Ensure Node.js 18+ is installed: `node --version` |
| watsonx.ai 401 error | Check `WATSONX_API_KEY` and `WATSONX_PROJECT_ID` in `.env`; set `WATSONX_GRANITE_TTM_ENABLED=false` to use fallback |
| watsonx.ai 404 / model not found | Verify `WATSONX_URL` matches your IBM Cloud region; set feature flag to `false` to use fallback |
