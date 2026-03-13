# 🛠️ Deep Technical Specifications – Disaster Management System

This document provides a low-level engineering breakdown of the DMS backend, database architecture, and algorithmic engines.

## 🏗️ Backend Architecture (FastAPI)
The backend is built with **FastAPI**, leveraging asynchronous patterns and Pydantic for strict data validation.

### Core Modules:
- **`main.py`**: Entry point. Configures CORS (allowing local frontend access), initializes the database, and mounts 11 specialized routers.
- **`database.py`**: Handles SQLite connection pooling (WAL mode) and schema migrations. Includes a 4-tier Chennai-based seeding engine for showcase environments.
- **`services/matcher.py`**: The core algorithmic engine for responder-to-emergency pairing.

---

## 💾 Database Schema & Data Models

| Table | High-Level Responsibility |
|---|---|
| `sos_requests` | Incident intake, `priority_score` (0-100), and `triage_level`. |
| `responders` | Unit registry with `type` (boat, medical) and `gps_accuracy`. |
| `missions` | The state-machine linking SOS to Responder. Tracks timestamps for every stage. |
| `agencies` | ICS hierarchical data (NDRF, TN-FIRE, NGOs). |
| `inventory` | Resource tracking (`owner_id` links to Agency or Shelter). |
| `sitreps` | Live field intelligence feed (linked to `mission_id`). |
| `audit_logs` | Immutable log of all system actions for accountability. |

---

## 🧠 Algorithmic Logic

### 1. The Matcher Engine (`matcher.py`)
Used by the Commander HUD to suggest the best team for a rescue.
- **Haversine Formula**: Calculates earth-curvature distance between SOS and Responder.
- **Scoring Weight Matrix**:
    - **Distance (60%)**: `Inverse distance score = 50 * (1 / (dist + 0.5))`
    - **Capability (30%)**: Matches `emergency_type` to `responder_type`.
        - *Example*: Boat on Flood = 1.0 weight; Drone on Medical = 0.2 weight.
    - **Trust Score (10%)**: Historical reliability normalized from 0-100.
- **Heuristic Overrides**: If the engine pairs a non-specialized unit to a medical case, it auto-appends a `special_instruction` for field transport.

### 2. Triage Logic (`sos.py`)
Calculates SOS priority based on:
- **Phone metadata** (Location reliability).
- **Keywords** in message (e.g., "Critical", "Trapped" have higher multipliers).
- **People Count**: Exponential priority scaling for larger groups.

---

## 📡 API Reference – Detailed Endpoints

### 🆘 Layer 1: SOS Intake (`/api/sos`)
- `POST /create`: Accepts `lat`, `lon`, `emergency_type`. Returns `sos_id`.
- `GET /all`: Returns all active SOS signals (polled by maps).
- `PUT /{id}/verify`: Commander manual verification of field reports.

### 🧑‍🚒 Layer 2: Responder Mgmt (`/api/responders`)
- `POST /register`: Onboarding with tier selection (Gov vs NGO).
- `GET /nearby`: Queries best candidates using the Matcher Engine.
- `PUT /{id}/location`: Volunteer app heartbeats for live map tracking.

### 🎯 Layer 3: Mission Lifecycle (`/api/missions`)
- `POST /create`: Step 1 of dispatch.
- `POST /{id}/assign`: Step 2 (Finalizes pairing and marks responder as `BUSY`).
- `PATCH /{id}/status`: Moves mission through ICS stages (En route -> On site -> Completed).

### 🖥️ Layer 4 & 5: Analytics (`/api/dashboard` & `/api/strategic`)
- `GET /alerts`: Fetches priority clusters and resource gaps.
- `GET /stats`: Aggregated KPIs for the Authority portal.
- `GET /agencies/directory`: Comprehensive listing of organization assets.

### ⚡ Field Intelligence (`/api/sitreps`)
- `POST /create`: SITREP submission.
- `GET /recent`: Tailled log of field updates for the Commander feed.

---

## 🔄 Execution Logic: The "Golden Hour" Flow
1. **Intake**: `POST /sos/create` -> DB persistence -> Triage Calculation.
2. **Alerting**: `GET /dashboard/alerts` detects high-density clusters.
3. **Dispatch**: Commander HUD calls `GET /responders/nearby` -> `matcher.py` runs scoring -> `POST /missions/create`.
4. **Field Action**: Volunteer app calls `PATCH /missions/status` -> Updates `sitreps` -> HUD maps update via polling.
5. **Resolution**: Status `completed` -> Responder becomes `available` -> Inventory updated if gear was consumed.
