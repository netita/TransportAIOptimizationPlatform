# Discordia AI Operations Platform

AI-powered optimization platform for Discordia — Bulgaria's largest transport and logistics company. Augments Oracle Transportation Management (OTM) with real-time AI intelligence across 1500+ trucks and 70 countries.

---

## What it does

| Feature | Description |
|---|---|
| Live Fleet Map | Real-time truck positions across Europe with status indicators |
| WebSocket Live Updates | Dashboard, Shipments, and Analytics pages update instantly via WebSocket — no page refresh needed |
| Connection Status | Header shows Live (green) / Connecting (yellow) / Reconnecting (red) based on real WS state |
| KPI Dashboard | Active shipments, delays, at-risk count, trucks online, border alerts |
| ETA & Risk Scoring | Per-shipment risk scores and delay predictions |
| Border Intelligence | Live wait times for 8 key European border crossings |
| Warehouse Monitoring | Congestion levels, dock availability, queue times for 8 hubs |
| Alerts Feed | Real-time operational alerts sorted by severity |
| AI Copilot | Claude-powered assistant with live operational context + ML predictions |
| Analytics | Delay trends, shipment status breakdown, congestion charts, model metrics |
| XGBoost ETA Model | Predicts delay minutes per shipment (MAE ~4 min, trained on 1,530 samples) |
| Delay Classifier | Predicts delay probability per shipment (Accuracy ~99.9%, AUC 1.0) |
| ML Columns in Table | AI Delay Prob + Predicted Delay columns in shipments table |
| Auto-Retraining | ML models retrain every 30 minutes on fresh live data |
| Anomaly Detection | IsolationForest flags suspicious trucks and shipments (orange dots on map) |
| Route Corridors | 4 main European corridors drawn on map (Turkey→Munich, Bucharest→Berlin, Sofia→Vienna, Varna→Hamburg) |
| Route Optimization | Per-shipment corridor scoring using live border wait times; reroute recommendations with savings estimate |
| Dispatcher Actions | Ranked action list combining ML predictions, route optimizer, anomaly detection, and warehouse congestion |
| Fleet Load Balancing | Corridor load distribution, fleet balance score, greedy truck-to-shipment assignment, idle truck and unassigned shipment alerts |
| Shipment Detail Page | Click any shipment row → full detail view with route map, ML prediction breakdown, border breakdown, dispatcher actions for that shipment |

---

## Business Context

- **80% international road transport** — primary focus
- **20% warehouse logistics** — secondary focus
- Platform **augments OTM**, does not replace it
- Demo corridor: **Turkey → Sofia Warehouse → Hungary Border → Germany**

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy |
| Database | PostgreSQL 16 |
| Cache / Pub-Sub | Redis 7 |
| Event Streaming | Apache Kafka |
| AI Copilot | Claude claude-sonnet-4-6 (Anthropic) |
| ML Models | XGBoost 2.1, scikit-learn 1.5 |
| ML Service | FastAPI on port 8001, auto-retrains every 30 min |
| Frontend | Next.js 14, React, Tailwind CSS |
| Maps | Leaflet + OpenStreetMap |
| Charts | Recharts |
| Infra | Docker Compose (8 services) |

---

## Quick Start

### 1. Prerequisites

- Docker + Docker Compose plugin (`docker compose version`)
- Anthropic API key from https://console.anthropic.com

### 2. Setup

```bash
git clone <repo>
cd TransportAIOptimizationPlatform

cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 3. Run

```bash
docker compose up --build
```

First start takes ~2 minutes to build. On subsequent starts:

```bash
docker compose up
```

### Auto-start on boot (Linux)

All services have `restart: unless-stopped` — if any container crashes, Docker restarts it automatically.

To start the full stack automatically on system boot:

```bash
sudo cp discordia.service /etc/systemd/system/discordia.service
sudo systemctl daemon-reload
sudo systemctl enable discordia.service
```

Control the stack manually:

```bash
sudo systemctl start discordia    # start everything
sudo systemctl stop discordia     # stop everything
sudo systemctl status discordia   # check state
```

### 4. Open

| URL | Description |
|---|---|
| http://localhost:3000 | Main dashboard |
| http://localhost:3000/shipments | Shipments table with filters |
| http://localhost:3000/analytics | Charts, trends + AI Model Performance |
| http://localhost:8000/docs | Backend API (Swagger) |
| http://localhost:8001/docs | ML Service API (Swagger) |
| http://localhost:8001/metrics | XGBoost model metrics (JSON) |

---

## Seed Data

Automatically loaded on first boot:

- **50 trucks** with realistic GPS positions across Europe
- **30 active shipments** on real European corridors
- **8 warehouses**: Sofia Hub, Istanbul Hub, Munich Hub, Vienna Hub, Budapest Hub, Belgrade Hub, Bucharest Hub, Varna Port
- **8 border crossings**: Kapitan Andreevo (BG-TR), Ruse/Giurgiu (BG-RO), Kalotina (BG-RS), Nadlac (RO-HU), Batrovci (RS-HR), Nickelsdorf (HU-AT), Albita (RO-MD), Kulata (BG-GR)
- **8 pre-seeded alerts** with realistic operational messages

---

## Live Simulation

The simulator updates automatically:

| Interval | What updates |
|---|---|
| Every 5 seconds | Truck GPS positions (movement along routes) |
| Every 30 seconds | Warehouse congestion, dock availability, queue times |
| Every 60 seconds | Border wait times and statuses |
| Every 2 minutes | Shipment delays and resolutions |
| Every 3 minutes | New operational alerts |

---

## AI Copilot — Example Conversations

Powered by Claude claude-sonnet-4-6 with live operational context + XGBoost ML predictions + IsolationForest anomaly detection. Access via the blue bot icon (bottom-right corner).

> **Tip:** The Copilot has real-time access to all live data — shipment statuses, truck GPS, border wait times, warehouse congestion, ML predictions, and anomaly scores. The more specific your question, the more actionable the answer.

---

### Morning Shift Briefing

Start here to get a full picture of the current operational state.

```
Give me a full operational briefing for the morning shift
```
> Returns: active shipment count, delayed count, at-risk list, border alerts, warehouse congestion summary, top recommended actions.

```
Summarize overnight operations for the management report
```
> Returns: what changed since last shift — new delays, resolved issues, border incidents, warehouse events.

```
What is our on-time delivery rate and how can we improve it?
```
> Returns: current OTD %, shipments contributing to delays, top improvement levers.

```
How many trucks are currently active vs idle vs at border?
```
> Returns: live fleet breakdown by status with counts.

```
Which shipments were created in the last 6 hours and what is their current status?
```
> Returns: newest shipments with ETA, risk score, and ML delay prediction.

---

### SLA & Risk Management

Use these to prioritize which shipments need immediate action.

```
Which shipments will miss SLA today?
```
> Returns: ranked list of at-risk shipments with delay probability, estimated breach time, and recommended action per shipment.

```
Which shipments are at highest risk right now?
```
> Returns: top 5 shipments sorted by risk score with contributing factors (border congestion, warehouse queue, ML prediction).

```
Are there any SLA breaches expected today?
```
> Returns: shipments where predicted delay pushes delivery past SLA window.

```
Which CRITICAL priority shipments are currently delayed?
```
> Returns: only CRITICAL shipments with delay_minutes > 0, sorted by delay severity.

```
Tell me about shipment SHP-2024-001
```
> Returns: full shipment detail — origin/destination, current truck, ETA, delay minutes, risk score, ML prediction, anomaly flag.

```
Which shipments have been delayed for more than 2 hours?
```
> Returns: shipments with delay_minutes > 120, with probable cause and recommended action.

---

### Border Intelligence

Eight live border crossings with real-time wait times and inspection rates.

```
What's happening at the Bulgaria-Turkey border?
```
> Returns: current wait time at Kapitan Andreevo, inspection rate, weather risk, trucks currently queued, rerouting options.

```
Which border crossing has the worst delays right now?
```
> Returns: ranking of all 8 borders by current wait_time_min with status (NORMAL / SLOW / CONGESTED).

```
Should I reroute trucks away from Kapitan Andreevo?
```
> Returns: decision recommendation based on current wait time, number of trucks affected, and alternative route ETAs.

```
What is the inspection rate at Nadlac border and how does it affect our Romania-Hungary shipments?
```
> Returns: Nadlac inspection rate, estimated processing time per truck, affected shipments on the Bucharest → Berlin corridor.

```
How do current border wait times affect our Turkey to Germany corridor total transit time?
```
> Returns: cumulative border delay across the main corridor — Kapitan Andreevo + Kalotina + Batrovci + Nickelsdorf.

```
Are any borders currently closed or at critical congestion?
```
> Returns: any border with status CLOSED or CONGESTED with estimated reopening or congestion resolution time.

---

### Warehouse & Congestion

Eight warehouse hubs across the Balkans and Central Europe.

```
Sofia Hub is congested — what should I do?
```
> Returns: full action plan — arrival slotting, triage categories, staging points, dwell time targets, cross-docking priority.

```
Which warehouse should I redirect incoming Istanbul trucks to?
```
> Returns: comparison of Sofia Hub vs Belgrade Hub vs Vienna Hub — congestion level, available docks, queue time — with recommendation.

```
What is the current dock availability at Munich Hub?
```
> Returns: total docks, free docks, queue time, incoming truck count, estimated wait for new arrivals.

```
Which warehouses have more than 70% congestion right now?
```
> Returns: list of congested hubs with congestion %, queue time, and suggested action (hold trucks, redirect, prioritize unloading).

```
How long would a truck arriving at Istanbul Hub right now have to wait?
```
> Returns: current queue_time_min at Istanbul Hub plus dock availability and next available slot estimate.

```
Rank all 8 warehouses by current congestion level
```
> Returns: ordered list of all hubs with congestion %, dock availability, and queue time.

---

### Anomaly Detection

IsolationForest flags the most anomalous 10% of trucks and shipments. Check this when something feels off.

```
Are there any suspicious truck movements or anomalies right now?
```
> Returns: list of flagged trucks with anomaly score, reason (impossible speed / no GPS / outside Europe / statistical), and severity (INFO / WARNING / CRITICAL).

```
Which trucks have not sent a GPS update in the last hour?
```
> Returns: trucks where time_since_last_update_min > 60, sorted by staleness.

```
Tell me about the anomalies detected on truck BGN-1006
```
> Returns: full anomaly detail — score, reason, last known position, time since last update, recommended investigation step.

```
Are there any CRITICAL anomalies I should investigate immediately?
```
> Returns: only anomalies with severity = CRITICAL (score > 0.9), with context and suggested action.

```
Which shipments have an anomalous risk pattern?
```
> Returns: shipments flagged by the shipment IsolationForest model with reason (extreme delay / critical risk score / statistical pattern).

```
Is truck BGN-1006 behaving normally?
```
> Returns: real-time anomaly status for that specific truck, including score and reason if flagged.

```
How many trucks are currently showing anomalous behavior and what are the most common reasons?
```
> Returns: count of anomalous trucks, breakdown by reason type, and top recommended actions.

---

### Dispatcher Actions

Use these to get a prioritized action list at the start of any shift or decision point.

```
Give me the top 5 actions I should take in the next hour
```
> Returns: prioritized action list with reasoning based on live KPIs, ML predictions, border/warehouse status, and anomaly flags.

```
Which trucks should I reroute and why?
```
> Returns: trucks where rerouting would reduce delay — specific border to avoid, alternative corridor, estimated time saved.

```
Which trucks have been idle too long?
```
> Returns: trucks with status IDLE or AT_WAREHOUSE longer than expected, with last known position and suggested next action.

```
Which carrier is performing worst today?
```
> Returns: delay rate and average delay minutes per carrier, worst performer highlighted with context.

```
I have 3 free docks opening at Sofia Hub in 2 hours — which trucks should I prioritize?
```
> Returns: ranked list of trucks approaching Sofia Hub by priority, delay risk, and cargo urgency.

```
What would happen if Kapitan Andreevo border closes for 4 hours?
```
> Returns: impact assessment — affected shipments, trucks currently en route, alternative corridors (via Kulata or Romania), estimated delay per shipment.

```
Give me a combined action plan using both ML predictions and route optimization
```
> Returns: unified priority list — shipments where XGBoost predicts high delay AND the route optimizer recommends a corridor switch, ranked by combined urgency.

```
How many hours of total fleet delay can I eliminate with the current reroute recommendations?
```
> Returns: total_savings_minutes from the route optimizer converted to hours, per-shipment breakdown, and % of current delay that is addressable by rerouting.

---

### Corridor Status

Four main European corridors are tracked live on the map.

```
What is the current status of the Turkey to Germany corridor?
```
> Returns: full corridor breakdown — Kapitan Andreevo wait time, Sofia Hub congestion, Kalotina/Batrovci/Nickelsdorf status, active shipments on route, predicted ETAs.

```
How many trucks are currently on the Bucharest to Berlin corridor?
```
> Returns: trucks on Ruse → Nadlac → Budapest → Vienna → Berlin route with status breakdown.

```
What is the fastest corridor from Sofia to Vienna right now?
```
> Returns: comparison of Sofia → Vienna direct vs Sofia → Belgrade → Budapest route based on live border wait times.

```
Which corridor is experiencing the most delays today?
```
> Returns: delay count and average delay per corridor (Turkey→Munich, Bucharest→Berlin, Sofia→Vienna, Varna→Hamburg).

---

### Route Optimization

The route optimizer scores 10 defined corridors using live border wait times and flags shipments where switching saves more than 30 minutes. Access the panel at the bottom of the main dashboard or ask the Copilot directly.

```
Which shipments should I reroute right now?
```
> Returns: full reroute list sorted by urgency — shipment ID, current corridor, recommended corridor, savings in minutes, and top border bottleneck per shipment.

```
How much time would we save if we rerouted all Turkey-to-Germany trucks via Romania today?
```
> Returns: total savings estimate — sum of (via-Serbia total time − via-Romania total time) across all qualifying shipments, with per-shipment breakdown.

```
Is the Serbia route or the Romania route faster for Istanbul to Munich right now?
```
> Returns: scored comparison — Turkey→Germany via Serbia (Kalotina + Batrovci) vs via Romania (Giurgiu + Nadlac), with live border wait times and drive time difference.

```
Which border is causing the most reroutes today?
```
> Returns: the single border checkpoint that appears as a bottleneck across the most active shipments, with wait time and affected shipment count.

```
What is the total border delay on the Turkey to Germany via Serbia corridor right now?
```
> Returns: sum of Kapitan Andreevo + Kalotina + Batrovci + Nickelsdorf wait times, with per-border breakdown and corridor total transit time estimate.

```
If Batrovci border wait drops to 30 minutes, does the Serbia route become optimal again for Sofia to Munich?
```
> Returns: hypothetical scoring — Serbia route total time with Batrovci at 30 min vs Romania route at current values, with crossover threshold.

```
Which CRITICAL priority shipments have a reroute recommendation?
```
> Returns: CRITICAL shipments from the route optimizer where should_reroute=true, sorted by savings_minutes, with recommended corridor and reason.

```
How does the route optimizer score the Varna to Hamburg corridor right now?
```
> Returns: Bulgaria→Germany via Serbia scoring — Kalotina + Batrovci + Nickelsdorf wait times, drive time at 80 km/h, total estimated transit time, and comparison with the via Romania alternative.

```
What is the fastest route from Bucharest to Munich today — via Hungary or via Bulgaria-Serbia?
```
> Returns: Romania→Germany (Nadlac → Nickelsdorf) vs Romania→Germany via Bulgaria-Serbia (Giurgiu → Kalotina → Batrovci → Nickelsdorf) — border totals, distances, and recommended option.

```
Show me all shipments where rerouting saves more than 1 hour
```
> Returns: all recommendations with savings_minutes > 60, sorted by urgency, with corridor switch and bottleneck detail.

```
Which corridor has the lowest total border delay right now?
```
> Returns: ranking of all 10 corridors by sum of border wait times, highlighting the clearest route across Europe.

```
DIS-2024-10015 is going Istanbul to Munich — is it on the best route?
```
> Returns: current corridor score vs best alternative for that specific shipment, with per-border wait times and exact minutes saved by switching.

---

### XGBoost ML Predictions

The model retrains every 30 minutes on live data. Ask about predictions at any time.

```
What does the XGBoost model predict for delays today?
```
> Returns: ML model summary — average predicted delay, % of fleet likely to be delayed, top 3 delay factors, model accuracy stats.

```
Which shipments have the highest predicted delay probability?
```
> Returns: top 10 shipments sorted by delay_probability (0–1), with predicted delay minutes and top contributing features.

```
What are the top factors causing predicted delays right now?
```
> Returns: ranked feature importance from the live XGBoost model — typically border_wait_time, warehouse_congestion_risk, distance_km.

```
Based on the ML predictions, should I reroute any trucks from Kapitan Andreevo?
```
> Returns: ML-backed rerouting recommendation — which trucks are affected, what the model predicts if they stay vs reroute.

```
How accurate is the ETA prediction model?
```
> Returns: current MAE (~3.9 min), RMSE, training sample count, last retrain time, and what MAE means operationally.

```
What is the current model MAE and what does it mean operationally?
```
> Returns: MAE in minutes with plain-language explanation — e.g. "predictions are on average 3.9 minutes off from actual arrival."

```
Which shipments does the model predict will be on time vs delayed?
```
> Returns: split of current shipments into predicted on-time vs predicted delayed, with confidence scores.

```
Has model performance changed since the last retraining?
```
> Returns: current metrics vs baseline — MAE, accuracy, AUC — with interpretation of any drift.

---

### Executive / Management

Use these for reporting, KPI reviews, and stakeholder updates.

```
What should I report to management about today's operations?
```
> Returns: executive summary — on-time rate, delay count, border incidents, warehouse utilization, anomaly count, ML model health.

```
How does today's performance compare to our targets?
```
> Returns: KPI comparison — active shipments vs capacity, delay rate vs target, at-risk count, trucks online ratio.

```
What are the main risks to our KPIs this week?
```
> Returns: top 3–5 operational risks based on current data — border congestion trends, warehouse capacity, anomaly patterns.

```
Give me a cost impact estimate of today's delays
```
> Returns: estimated delay impact — total delay minutes across fleet, high-priority shipments affected, estimated SLA breach exposure.

```
Which of our 8 border crossings is causing the most operational disruption this week?
```
> Returns: border ranked by cumulative delay impact, inspection rates, and recommended mitigation.

---

Requires `ANTHROPIC_API_KEY` in `.env`.

---

## Project Structure

```
TransportAIOptimizationPlatform/
├── docker-compose.yml       — 8 services (all restart: unless-stopped)
├── discordia.service        — systemd unit for auto-start on boot
├── .env.example
├── backend/                 — FastAPI (port 8000)
│   └── app/
│       ├── main.py          — startup, seed, WebSocket (/ws, async Redis + 25s ping)
│       ├── models.py        — Shipment, Truck, Warehouse, Border, Alert
│       ├── schemas.py       — Pydantic schemas
│       └── routers/
│           ├── shipments.py — CRUD + ML prediction merge + SSE stream
│           ├── gps.py
│           ├── warehouse.py
│           ├── borders.py
│           ├── analytics.py — KPIs + model metrics + predictions summary
│           ├── routes.py    — Route Optimization engine (10 corridors, live scoring)
│           ├── dispatcher.py — Dispatcher Recommendation System (REROUTE/ESCALATE/INVESTIGATE/HOLD)
│           ├── fleet.py     — Fleet Load Balancing (corridor load, balance score, greedy assignment)
│           └── copilot.py   — Claude AI + ML context injection
├── ml-service/              — XGBoost ML service (port 8001)
│   └── app/
│       ├── main.py          — training on startup, 30-min retraining loop
│       ├── train.py         — XGBoost regressor + classifier pipeline
│       ├── predict.py       — inference + feature importance
│       ├── features.py      — shared feature engineering (12 features)
│       └── database.py
├── simulators/
│   └── simulator.py         — live data generator
└── frontend/                — Next.js 14 (port 3000)
    └── src/
        ├── app/
        │   ├── layout.tsx       — root layout; mounts WsProvider for all pages
        │   ├── page.tsx         — main dashboard
        │   ├── shipments/       — full table + filters
        │   └── analytics/       — charts + AI model performance
        ├── context/
        │   └── WsContext.tsx    — shared WS connection + SWR cache invalidation
        ├── hooks/
        │   └── useWebSocket.ts  — native WebSocket hook with exponential-backoff reconnect
        └── components/
            ├── Header.tsx                 — shows Live/Connecting/Reconnecting WS status
            ├── ShipmentsTable.tsx         — ML prediction columns
            ├── LiveMap.tsx
            ├── KPICards.tsx
            ├── AlertsFeed.tsx
            ├── WarehousePanel.tsx
            ├── BorderPanel.tsx
            ├── RouteOptimizationPanel.tsx — reroute recommendations, border breakdown
            ├── DispatcherPanel.tsx        — ranked action cards (REROUTE/ESCALATE/INVESTIGATE/HOLD)
            ├── FleetBalancePanel.tsx      — corridor load bars, balance score, assignment cards
            ├── ShipmentMap.tsx            — per-shipment Leaflet map (origin, destination, truck GPS)
            └── AICopilot.tsx
```

---

## Dispatcher Recommendation System

**API:** `GET http://localhost:8000/api/v1/dispatcher/recommendations`

Produces a ranked action list for the on-duty dispatcher by combining four data sources in a single call. Displayed as a panel on the main dashboard next to Route Optimization, refreshed on every WebSocket event.

### Action types

| Type | Source | Trigger condition |
|---|---|---|
| **REROUTE** | Route optimization engine | Corridor switch saves > 30 min |
| **ESCALATE** | XGBoost ML predictions | HIGH/CRITICAL shipment with ≥ 70% delay probability |
| **INVESTIGATE** | IsolationForest anomaly detector | Truck flagged WARNING or CRITICAL severity |
| **HOLD** | Live warehouse data | Warehouse congestion risk > 80% |

### Urgency ranking

All actions are scored and sorted: CRITICAL → HIGH → MEDIUM → LOW, then by impact minutes descending. The list is capped at 15 items.

| Urgency | REROUTE | ESCALATE | INVESTIGATE | HOLD |
|---|---|---|---|---|
| CRITICAL | Savings > 90 min | Prob ≥ 90% or CRITICAL priority | Anomaly severity CRITICAL | Congestion > 90% |
| HIGH | Savings > 45 min | Prob ≥ 70% and HIGH priority | Anomaly severity WARNING | Congestion > 80% |
| MEDIUM | Savings > 30 min | — | — | — |

### Response shape

```json
{
  "actions": [
    {
      "id": "reroute-DIS-2024-10017",
      "type": "REROUTE",
      "urgency": "CRITICAL",
      "title": "Reroute DIS-2024-10017",
      "description": "CRITICAL · Istanbul → Munich. Batrovci: 156 min. Switch to Turkey → Germany (via Romania).",
      "action": "Switch to Turkey → Germany (via Romania) — saves 2.6h",
      "entity_id": "DIS-2024-10017",
      "entity_type": "shipment",
      "impact_minutes": 156,
      "impact_label": "Saves 2.6h"
    }
  ],
  "summary": {
    "total": 12,
    "critical": 4,
    "high": 5,
    "total_saveable_minutes": 480
  }
}
```

### Dashboard panel

The **Dispatcher Actions** panel sits side-by-side with Route Optimization at the bottom of the main dashboard. Shows 6 actions by default with a "Show N more" toggle. Each card displays:
- Urgency badge (red / orange / yellow)
- Action type badge with icon (Navigate / AlertTriangle / Search / PauseCircle)
- Description of what is happening
- Recommended action text
- Impact label (e.g. "Saves 2.6h", "94% delay risk", "45 min queue")

---

## Fleet Load Balancing

**API:** `GET http://localhost:8000/api/v1/fleet/balance`

Analyses how work is distributed across the active fleet and produces truck-to-shipment assignment recommendations. Displayed as a full-width panel at the bottom of the main dashboard, refreshed on every WebSocket event.

### What it calculates

**Corridor load distribution** — counts active trucks per recognised European corridor and classifies each corridor's load level:

| Level | Trucks on corridor | Color |
|---|---|---|
| CRITICAL | ≥ 8 | Red — overloaded, avoid new assignments |
| HIGH | ≥ 5 | Orange — near capacity, prefer alternatives |
| BALANCED | ≥ 2 | Green — normal range |
| LOW | < 2 | Gray — underutilised, prioritise for new assignments |

**Fleet balance score** — single 0–100% value based on the coefficient of variation across corridor loads. 100% = perfectly even distribution; 0% = all trucks on one corridor.

**Greedy assignment** — when IDLE/AT_WAREHOUSE trucks and PENDING shipments coexist, the engine matches them:
1. Shipments sorted by priority (CRITICAL → HIGH → MEDIUM → LOW) then risk score
2. For each shipment, the nearest available truck is selected by Haversine distance
3. Assignment score = `(priority_weight / 4) × max(0.1, 1 − distance_km / 500)`

### Response shape

```json
{
  "assignments": [
    {
      "truck_id": "BGN-1007",
      "shipment_id": "DIS-2024-10042",
      "priority": "HIGH",
      "distance_km": 38.2,
      "score": 0.694,
      "truck_status": "IDLE",
      "origin": "Sofia",
      "destination": "Munich",
      "reason": "Nearest available truck (38.2 km away). HIGH priority shipment."
    }
  ],
  "unassigned_shipments": [],
  "idle_trucks": [],
  "corridor_load": [
    {
      "corridor_id": "BG_DE_RS",
      "corridor_name": "Bulgaria → Germany (via Serbia)",
      "active_trucks": 6,
      "load_level": "HIGH",
      "recommendation": "Near capacity — prefer alternative corridors for new shipments."
    }
  ],
  "summary": {
    "total_trucks": 50,
    "available_trucks": 2,
    "active_trucks": 48,
    "pending_shipments": 0,
    "assignments_made": 1,
    "balance_score": 0.65,
    "overloaded_corridors": 2
  }
}
```

### Dashboard panel

The **Fleet Load Balancing** panel runs full-width below the Dispatcher / Route Optimization row. It shows:
- **Balance score** and active/available truck counts in the header
- **Corridor load bars** — one per active corridor, color-coded, with truck count badge and recommendation text for HIGH/CRITICAL corridors
- **Recommended assignments** — truck → shipment cards with origin/destination and distance, shown when idle trucks and pending shipments exist simultaneously
- **Idle trucks notice** — when trucks are available but no shipments are pending
- **Unassigned shipments notice** — when shipments are pending but no trucks are free (highlights CRITICAL count)
- "Show N more corridors" toggle when there are more than 5 corridors

### Test via curl

```bash
curl -s http://localhost:8000/api/v1/fleet/balance | python3 -m json.tool
```

---

## Shipment Detail Page

**URL:** `http://localhost:3000/shipments/{shipment_id}`

Click any row in the Shipments table to open the full detail view for that shipment. No new backend endpoint was needed — all data already existed; the page assembles it in one place.

### Sections

| Section | Content |
|---|---|
| **Route Map** | Leaflet map with green dot (origin), red dot (destination), dashed blue route line, and a blue square for the assigned truck's last GPS position |
| **Overview** | Carrier, assigned truck, ETA with countdown, created timestamp, current delay in red, risk score gauge |
| **AI Prediction** | Delay probability bar, predicted delay minutes, model confidence, top 3 delay factors with HIGH / MEDIUM / LOW impact badges |
| **Route Optimization** | Current corridor vs recommended corridor, border-by-border wait time breakdown with bottlenecks highlighted in red, savings in minutes |
| **Dispatcher Actions** | Any REROUTE / ESCALATE / INVESTIGATE / HOLD actions that apply specifically to this shipment |

### Navigation

- From **Shipments table** (`/shipments`): click any row
- Direct URL: `http://localhost:3000/shipments/DIS-2024-10001`
- Back button returns to the Shipments table

### Live updates

The detail page polls every 30 seconds and also reacts to WebSocket events — if the shipment status changes while the page is open, the status badge and delay row update automatically.

---

## Real-Time WebSocket Updates

The backend exposes a WebSocket endpoint at `ws://localhost:8000/ws` backed by Redis Pub/Sub on the `live_events` channel.

### Event types published

| Event | Trigger | Frontend action |
|---|---|---|
| `gps_update` | Simulator pushes truck positions every 5 s | Refetches live truck data → map updates |
| `shipment_update` | Status change via `PUT /api/v1/shipments/{id}/status` | Optimistically patches shipment row + refetches KPIs and alerts |

### Frontend architecture

One WebSocket connection is opened in the root layout (`WsProvider`) and shared across all pages. The `Header` component reads the connection state from context and displays:

- **Green pulsing dot — Live**: connected, events flowing
- **Yellow pulsing dot — Connecting**: initial handshake or reconnecting within backoff window
- **Red dot — Reconnecting**: connection lost, waiting to retry (exponential backoff: 1 s → 2 s → 4 s → … → 30 s cap)

SWR polling (30 s fallback) runs in the background in case the WebSocket drops and misses an event.

### Test the WebSocket directly

```bash
python3 -c "
import asyncio, websockets
async def w():
    async with websockets.connect('ws://localhost:8000/ws') as ws:
        while True: print(await ws.recv())
asyncio.run(w())
"
```

Then trigger a shipment update in a second terminal:

```bash
curl -X PUT http://localhost:8000/api/v1/shipments/DIS-2024-10017/status \
  -H 'Content-Type: application/json' \
  -d '{"status": "DELAYED"}'
```

---

## Stopping

```bash
docker compose down          # stop containers
docker compose down -v       # stop + delete database
```

---

## ML Service Details

The ML service trains three models on startup.

### XGBoost ETA Prediction

Trains on 30 real shipments × 50 synthetic augmentations = **1,530 training samples**.

**12 input features:**
- distance_km, priority, carrier, border_wait_time, border_inspection_rate, border_weather_risk, warehouse_congestion_risk, warehouse_queue_time, hour_of_day, day_of_week, is_already_delayed, trucks_online_ratio

**Outputs per shipment:**
- `predicted_delay_minutes` — how many minutes late (XGBoost regressor)
- `delay_probability` — 0–1 chance of being delayed (XGBoost classifier)
- `confidence` — model confidence score
- `top_factors` — top 3 features driving the prediction

**Current model performance:**
- ETA MAE: ~3.9 minutes
- Delay classifier accuracy: ~99.9%, AUC: 1.0
- Auto-retrains every 30 minutes

---

### Anomaly Detection (IsolationForest)

Two IsolationForest models — one for trucks, one for shipments. `contamination=0.1` means the most anomalous 10% are flagged.

**Truck features (5):** speed_kmh, lat, lon, time_since_last_update_min, is_moving

**Shipment features (5):** delay_minutes, risk_score, distance_km, priority_encoded, hours_since_created

**Anomaly reasons detected:**
- Impossible speed (>120 km/h)
- No GPS signal for 8h+
- Truck moving but no GPS update for 3h+
- GPS position outside Europe bounds
- Statistical anomaly in movement/shipment pattern

**Output per anomaly:**
- `entity_id` — truck_id or shipment_id
- `anomaly_score` — 0–1 (higher = more anomalous)
- `is_anomaly` — true/false (IsolationForest predict = -1)
- `severity` — INFO / WARNING / CRITICAL
- `reason` — human-readable explanation

**On the map:** anomalous trucks show as **orange pulsing dots**. Click to see the anomaly reason in the popup.

**API:** `GET http://localhost:8001/anomalies` — live JSON list of all detected anomalies.

---

---

## Route Optimization Engine

**API:** `GET http://localhost:8000/api/v1/routes/recommendations`

Scores every active shipment across all applicable route corridors using live border wait times. Flags shipments where switching corridors saves more than 30 minutes.

### Scoring model

For each corridor:
```
total_time = (distance_km / 80 km/h × 60) + sum(border_wait_times_on_route)
```

Reroute is recommended when: `current_total_time − best_total_time > 30 min`

### Defined corridors (10 total)

| Corridor | Borders | Distance |
|---|---|---|
| Turkey → Germany (via Serbia) | KA → Kalotina → Batrovci → Nickelsdorf | 2 200 km |
| Turkey → Germany (via Romania) | KA → Giurgiu → Nadlac → Nickelsdorf | 2 380 km |
| Turkey → Austria (via Serbia) | KA → Kalotina → Batrovci → Nickelsdorf | 1 800 km |
| Turkey → Austria (via Romania) | KA → Giurgiu → Nadlac → Nickelsdorf | 1 980 km |
| Bulgaria → Germany (via Serbia) | Kalotina → Batrovci → Nickelsdorf | 1 550 km |
| Bulgaria → Germany (via Romania) | Giurgiu → Nadlac → Nickelsdorf | 1 750 km |
| Romania → Germany | Nadlac → Nickelsdorf | 1 900 km |
| Romania → Germany (via Bulgaria-Serbia) | Giurgiu → Kalotina → Batrovci → Nickelsdorf | 2 100 km |
| Bulgaria → Austria | Kalotina → Batrovci → Nickelsdorf | 1 200 km |
| Turkey → Bulgaria | Kapitan Andreevo | 570 km |

### Response per shipment

```json
{
  "shipment_id": "DIS-2024-10015",
  "current_route": "Turkey → Germany (via Serbia)",
  "recommended_route": "Turkey → Germany (via Romania)",
  "should_reroute": true,
  "savings_minutes": 571,
  "urgency": "CRITICAL",
  "bottlenecks": ["Bulgaria-Turkey (Kapitan Andreevo): 1226 min", "Bulgaria-Serbia (Kalotina): 1244 min"],
  "border_breakdown": [
    {"name": "Bulgaria-Turkey (Kapitan Andreevo)", "wait_min": 1226},
    {"name": "Bulgaria-Serbia (Kalotina)", "wait_min": 1244},
    {"name": "Serbia-Croatia (Batrovci)", "wait_min": 1739},
    {"name": "Hungary-Austria (Nickelsdorf)", "wait_min": 1139}
  ],
  "all_options": [
    {"name": "Turkey → Germany (via Romania)", "total_time_min": 7076, "is_recommended": true},
    {"name": "Turkey → Germany (via Serbia)", "total_time_min": 7647, "is_recommended": false}
  ]
}
```

**On the dashboard:** Route Optimization panel shows at the bottom of the main page — reroutes first, sorted by savings. Click any row to expand the full border breakdown and route comparison.

---

## Roadmap

- [x] Phase 1 — Infrastructure (Kafka, PostgreSQL, Redis, Docker)
- [x] Phase 2 — Data Simulation (GPS, shipments, warehouses, borders)
- [x] Phase 3 — XGBoost ETA Prediction + Delay Classification
- [x] Phase 3 — Anomaly Detection (IsolationForest)
- [x] Phase 4 — Route Optimization engine
- [x] Phase 4 — Dashboard real-time WebSocket updates (all pages)
- [x] Phase 4 — Auto-start on boot (systemd service + restart policies)
- [x] Phase 5 — Dispatcher recommendation system (REROUTE / ESCALATE / INVESTIGATE / HOLD)
- [x] Phase 5 — Fleet load balancing (corridor load distribution, balance score, greedy truck assignment)
- [x] Phase 5 — Shipment detail page (route map, ML breakdown, border breakdown, dispatcher actions)
- [ ] Phase 6 — SLA Breach Monitoring
- [ ] Phase 6 — OTM integration layer
- [ ] Phase 6 — Carrier & Corridor Analytics
