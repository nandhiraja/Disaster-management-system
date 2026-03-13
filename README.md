# 🚨 Disaster Management System

A **5-layer flood disaster response prototype** built with Python (FastAPI) backend and pure HTML/CSS/JS frontend.

## Quick Start

### 1. Start Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs available at: **http://localhost:8000/docs**

### 2. Open Frontend Pages

Open these files directly in your browser (no build step needed):

| Layer | File | Description |
|---|---|---|
| 🆘 Layer 1 | `frontend/sos.html` | Emergency SOS Portal |
| 🧑‍🤝‍🧑 Layer 2 | `frontend/responders.html` | Responder Management |
| 🎯 Layer 3 | `frontend/missions.html` | Mission Allocation |
| 🖥️ Layer 4 | `frontend/dashboard.html` | Command Dashboard ← **Start here** |
| 📊 Layer 5 | `frontend/strategic.html` | Strategic Monitor |

## Demo Flow

1. Open `sos.html` → tap SOS → fill form → submit
2. Open `dashboard.html` → see SOS on live map 🔴
3. Click **Assign Now** → go to Mission Control
4. Auto-assign or manually pick responder → mission starts 🟡
5. Update mission to **Completed** → marker turns green 🟢
6. Open `strategic.html` → KPI cards, charts, heatmap all update

## Architecture

```
Layer 1 (SOS)    → POST /api/sos/create
Layer 2 (Resp)   → GET/PUT /api/responders
Layer 3 (Mission)→ POST /api/missions/auto-assign
Layer 4 (Ops)    → GET /api/dashboard/map-data (5s poll)
Layer 5 (Strat)  → GET /api/strategic/stats + heatmap
```

**Matcher Engine:** `backend/services/matcher.py`
- Haversine distance calculation
- Area condition checks (boat-only flood zones)
- Capability + trust-level weighted scoring

## Tech Stack
- **Backend:** Python 3 + FastAPI + SQLite
- **Frontend:** Vanilla HTML + CSS + JS
- **Maps:** Leaflet.js + OpenStreetMap (no API key)
- **Charts:** Chart.js (Layer 5)
- **Seed Data:** Chennai flood scenario (15 responders, 8 SOS, 5 shelters)
