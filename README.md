# 🌊 Disaster Management System (DMS) – Next-Gen Mission Control

A professional, high-fidelity Disaster Response & Mission Management platform designed for real-time flood emergency coordination. Built on an **Incident Command System (ICS)** model.

## 🚀 The Three Pillars
The system is divided into three specialized portals for distinct operational roles:

### 🖥️ [Commander HUD](frontend/commander.html)
**The Tactical Mission Control Center.**
- **Real-time Radar**: Live precipitation radar via RainViewer API integration.
- **Thermal Water Intensity**: Custom heatmap derived from SOS density and Chennai topographical heuristics (Adyar/Cooum river risk).
- **Tactical Sidebar**: Streamlined "Incoming" vs "Active" workflow for rapid deployment.
- **Stage-based Tracking**: Multi-step mission progress bars for live field monitoring.

### 📊 [Authority Dashboard](frontend/authority.html)
**Strategic District-Level Oversight.**
- **Agency Benchmarking**: Monitor personnel and asset distribution across NGOs and Government bodies.
- **Gap Analysis**: Identification of resource shortages in high-risk zones.
- **Strategic Charts**: High-density SITREP and inventory monitoring via Chart.js.

### 🧑‍🚒 [Volunteer Tactical App](frontend/volunteer-app.html)
**Field-Ready Mobile Interface.**
- **SITREP Reporting**: Instant "Field Intel" submission with location context.
- **Support Drawer**: Professional UI for requesting technical backup (Boats, Medical, Logistics).
- **Navigation**: Integrated Tactical Map and deep-linking for Google Maps turn-by-turn directions.

---

## 🛠️ Setup & Operations

### 1. Power on the Backend
```bash
cd backend
python main.py
```
*Note: Ensure `fastapi`, `uvicorn`, and `pydantic` are installed.*

### 2. Operational Entry Points
- **Entryway**: [index.html](frontend/index.html) (Main portal for role selection)
- **SOS Portal**: [sos.html](frontend/sos.html) (Public-facing emergency reporting)
- **Register**: [responders_register.html](frontend/responders_register.html) (NGO/Volunteer onboarding)

---

## 🧠 Core Intelligence
- **Matcher Engine**: Advanced greedy matching algorithm considering Haversine distance, responder capability, and agency trust-scores.
- **Inundation Modeling**: Simulated flood zone layers using professional geospatial visualizations.
- **Audit Logs**: Comprehensive event tracking for post-disaster analysis and accountability.

## 🎨 Professional Design Philosophy
The system uses a **Glassmorphic Dark Mode** aesthetics, inspired by modern command-and-control defense systems. 
- **Typography**: Outfit (Modern, high-redability)
- **Palette**: Neon Operational (Accent Blue, Critical Red, Success Green)
- **Responsive**: Fully optimized for Desktop, iPad Pro, and Tablet-sized tactical mounts.

---
**Vision**: Empowering first responders with superior data clarity during the "Golden Hour" of disaster relief.
