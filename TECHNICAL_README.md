# Technical Documentation: Disaster Management System (DMS)

This document provides a detailed technical overview of the DMS architecture, data flow, and API specifications.

## 1. System Architecture

The system follows a decoupled client-server architecture:
- **Backend**: FastAPI (Python) with a SQLite database. Logic is modularized into specialized routers (SOS, Missions, Responders, etc.).
- **Frontend**: Clean HTML5/CSS3/Vanilla JS applications.
    - **Commander HQ**: Operational dashboard for mission triage and resource management.
    - **Volunteer App**: Mobile-first application for ground responders.
    - **Authority Dashboard**: High-level strategic monitoring and inventory management.
    - **SOS Page**: Public-facing emergency reporting tool.
- **Real-time Map Integration**: Leaflet.js with plugins for Heatmaps and external layers (OpenTopoMap, RainViewer).

---

## 2. Core Data Flow

### A. SOS & Triage
1. **Reporting**: Public user submits an SOS request via `sos.html`.
2. **Persistence**: Data is stored in `sos_requests` with a calculated `priority_score`.
3. **Commander Approval**: Operators in `commander.html` view pending SOS in the **Triage Kanban**.

### B. Mission Lifecycle
1. **Dispatch**: Operator clicks "Deploy Team" for an SOS. System fetches nearby available responders using geographical radius searches.
2. **Creation**: A `mission` entry is created (status: `created`).
3. **Assignment**: A specific responder is assigned (status: `assigned`).
4. **Volunteer Notification**: The responder sees the new mission in their app.

### C. Field Operations
1. **Status Flow**: Volunteer advances the mission: `assigned` → `en_route` → `on_site` → `rescue_in_progress` → `completed`.
2. **Resolution**: Once completed, the corresponding SOS request is marked `rescued` and the responder is set back to `available`.

---

## 3. Database Schema (SQLite)

### Core Tables
| Table | Description | Key Fields |
| :--- | :--- | :--- |
| `sos_requests` | All emergency calls | `sos_id`, `type`, `lat/lon`, `status`, `priority_score` |
| `responders` | Registered volunteers/teams | `id`, `name`, `type` (boat/medical/etc), `status`, `lat/lon` |
| `missions` | Active rescue tasks | `mission_id`, `sos_id`, `responder_id`, `status` |
| `agencies` | Organizational entities | `id`, `name`, `type` (NDRF, NGO, etc), `personnel_count` |
| `sitreps` | Field intelligence reports | `id`, `responder_id`, `message`, `timestamp` |
| `inventory` | Resource tracking | `id`, `item_name`, `quantity`, `category` |

---

## 4. Primary API Endpoints

### 🆘 SOS Requests (`/api/sos`)
- `POST /submit`: Create new SOS.
- `GET /all`: Retrieve all active/pending SOS.
- `PUT /{id}/verify`: Verify/Reject an SOS.

### 🚁 Missions (`/api/missions`)
- `POST /create`: Initialize a mission for an SOS.
- `POST /{id}/assign`: Assign a responder to a mission.
- `PUT /{id}/status`: Advance mission status.
- `GET /my-assignments/{resp_id}`: Fetch missions for a specific responder.

### 🧑‍🚒 Responders (`/api/responders`)
- `POST /login`: Verify responder by phone number.
- `GET /nearby`: Find responders within X km of a coordinate.
- `PUT /{id}/location`: Update GPS coordinates in real-time.
- `PUT /{id}/status`: Toggle availability (Online/Offline/Busy).

### 📡 Sitreps & Intelligence (`/api/sitreps`)
- `POST /create`: Submit a field situation report.
- `GET /recent`: Global feed of latest 50 sitreps.
- `GET /my/{id}`: History of reports for a specific responder.

---

## 5. Map Layer Integration

The Commander dashboard utilizes dynamic layers for situational awareness:
- **RainViewer (Radar)**: Fetches real-time precipitation data from `api.rainviewer.com`.
- **Thermal Intensity (Heatmap)**: Renders SOS priority density using `leaflet-heat`.
- **Inundation Zones**: Simulated polygons representing high-risk flood areas.
- **Topographical Map**: High-detail terrain via `OpenTopoMap`.
