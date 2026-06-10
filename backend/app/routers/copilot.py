import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import (
    Alert,
    AlertTypeEnum,
    Border,
    Shipment,
    ShipmentStatusEnum,
    Truck,
    TruckStatusEnum,
    Warehouse,
)
from app.schemas import CopilotRequest, CopilotResponse

logger = logging.getLogger(__name__)

router = APIRouter()

SYSTEM_PROMPT_TEMPLATE = """You are the Discordia AI Logistics Copilot. Discordia is Bulgaria's largest transport company with 1500+ trucks operating in 70 countries. The platform augments Oracle Transportation Management (OTM).

## Fleet KPIs
- Active shipments: {active_shipments}
- Delayed shipments: {delayed}
- At-risk shipments (risk score >= 0.6): {at_risk}
- Trucks online: {trucks_online}
- Unread border alerts: {border_alerts}
- On-time rate: {on_time_rate}%
- Average delay: {avg_delay} minutes

{ml_section}{borders_section}{warehouses_section}{routes_section}{fleet_section}Help dispatchers with:
- SLA risk analysis and prioritization
- Route recommendations and alternatives
- Border delay insights and predictions
- Warehouse congestion management
- Anomaly detection explanations
- Fleet load balancing

When answering questions about specific shipments, explicitly reference ML predictions: "According to the XGBoost prediction model..." rather than "Based on current data..."
When answering route comparison questions, use the LIVE border wait times above to calculate exact corridor totals.

Be concise, operational, and data-driven. Use bullet points for lists. Highlight critical issues first."""


def _fetch_ml_metrics(timeout: float = 2.0) -> Optional[Dict[str, Any]]:
    """Fetch model metrics from the ML service. Returns None if unavailable."""
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(f"{settings.ml_service_url}/metrics")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.debug(f"ML metrics unavailable for copilot prompt: {e}")
        return None


def _fetch_predictions_summary(timeout: float = 2.0) -> Optional[Dict[str, Any]]:
    """Fetch predictions summary from the analytics endpoint. Returns None if unavailable."""
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(
                f"http://localhost:8000/api/v1/analytics/predictions/summary"
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.debug(f"Predictions summary unavailable for copilot prompt: {e}")
        return None


def _fetch_route_recommendations(timeout: float = 3.0) -> Optional[Dict[str, Any]]:
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get("http://localhost:8000/api/v1/routes/recommendations")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.debug(f"Route recommendations unavailable for copilot prompt: {e}")
        return None


def _fetch_fleet_balance(timeout: float = 3.0) -> Optional[Dict[str, Any]]:
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get("http://localhost:8000/api/v1/fleet/balance")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.debug(f"Fleet balance unavailable for copilot prompt: {e}")
        return None


def _fetch_anomalies(timeout: float = 2.0) -> list:
    """Fetch current anomalies from the analytics endpoint. Returns [] if unavailable."""
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(
                f"http://localhost:8000/api/v1/analytics/anomalies"
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.debug(f"Anomalies unavailable for copilot prompt: {e}")
        return []


def _build_ml_section(
    ml_metrics: Optional[Dict[str, Any]],
    predictions_summary: Optional[Dict[str, Any]],
    anomalies: Optional[list] = None,
) -> str:
    """Build the ML section of the system prompt."""
    lines = []

    if ml_metrics:
        mae = ml_metrics.get("mae", "N/A")
        accuracy = ml_metrics.get("accuracy", 0)
        total_samples = ml_metrics.get("total_samples", "N/A")
        accuracy_pct = round(float(accuracy) * 100, 1) if isinstance(accuracy, (int, float)) else "N/A"
        lines.append("ML Model Performance:")
        lines.append(f"- ETA prediction MAE: {mae} minutes")
        lines.append(f"- Delay classification accuracy: {accuracy_pct}%")
        lines.append(f"- Model trained on: {total_samples} shipments")
        lines.append("")

    if predictions_summary:
        pct = predictions_summary.get("pct_likely_delayed", 0)
        avg_delay = predictions_summary.get("avg_predicted_delay", 0)
        top_factors = predictions_summary.get("top_factors", [])
        factor_names = [f["factor"] for f in top_factors] if top_factors else []
        lines.append("AI Predictions (live):")
        lines.append(f"- {pct}% of active shipments predicted to be delayed")
        lines.append(f"- Average predicted delay: {avg_delay} minutes")
        if factor_names:
            lines.append(f"- Top fleet-wide delay factors: {', '.join(factor_names)}")
        lines.append("")

    if anomalies is not None:
        count = len(anomalies)
        lines.append(f"Active Anomalies ({count}):")
        for anomaly in anomalies[:3]:
            severity = anomaly.get("severity", "INFO")
            entity_id = anomaly.get("entity_id", "unknown")
            reason = anomaly.get("reason", "")
            lines.append(f"- [{severity}] {entity_id}: {reason}")
        lines.append("")

    return "\n".join(lines)


def _build_borders_section(db: Session) -> str:
    try:
        borders = db.query(Border).order_by(Border.wait_time_min.desc()).all()
        if not borders:
            return ""
        lines = ["## Live Border Wait Times"]
        for b in borders:
            status = b.status.value if hasattr(b.status, "value") else str(b.status)
            lines.append(f"- {b.name}: {b.wait_time_min} min wait, status={status}, inspection_rate={b.inspection_rate:.0%}")
        lines.append("")
        return "\n".join(lines) + "\n"
    except Exception as e:
        logger.debug(f"Border section error: {e}")
        return ""


def _build_warehouses_section(db: Session) -> str:
    try:
        warehouses = db.query(Warehouse).order_by(Warehouse.congestion_risk.desc()).all()
        if not warehouses:
            return ""
        lines = ["## Live Warehouse Status"]
        for w in warehouses:
            lines.append(
                f"- {w.name} ({w.city}): congestion={w.congestion_risk:.0%}, "
                f"docks={w.available_docks}/{w.total_docks} free, queue={w.queue_time_min} min"
            )
        lines.append("")
        return "\n".join(lines) + "\n"
    except Exception as e:
        logger.debug(f"Warehouse section error: {e}")
        return ""


def _build_routes_section(routes: Optional[Dict[str, Any]]) -> str:
    if not routes:
        return ""
    recs = routes.get("recommendations", [])
    summary = routes.get("summary", {})
    if not recs:
        return ""
    lines = ["## Route Optimization (live)"]
    lines.append(
        f"- {summary.get('reroute_recommended', 0)}/{summary.get('total_analyzed', 0)} shipments recommended for reroute"
    )
    lines.append(f"- Total saveable: {summary.get('total_savings_minutes', 0)} min")
    if summary.get("worst_bottleneck"):
        lines.append(f"- Worst bottleneck: {summary['worst_bottleneck']}")
    reroutes = [r for r in recs if r.get("should_reroute")][:5]
    for r in reroutes:
        lines.append(
            f"- {r['shipment_id']} ({r.get('origin')}→{r.get('destination')}): "
            f"switch {r['current_route']} → {r['recommended_route']}, saves {r['savings_minutes']} min"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def _build_fleet_section(fleet: Optional[Dict[str, Any]]) -> str:
    if not fleet:
        return ""
    summary = fleet.get("summary", {})
    corridors = fleet.get("corridor_load", [])
    lines = ["## Fleet Load Balance (live)"]
    lines.append(
        f"- Balance score: {round(summary.get('balance_score', 0) * 100)}%, "
        f"active={summary.get('active_trucks', 0)}, available={summary.get('available_trucks', 0)}, "
        f"overloaded corridors={summary.get('overloaded_corridors', 0)}"
    )
    for c in corridors[:6]:
        lines.append(f"- {c['corridor_name']}: {c['active_trucks']} trucks, level={c['load_level']}")
    assignments = fleet.get("assignments", [])
    if assignments:
        lines.append(f"- {len(assignments)} pending assignment(s) ready to dispatch")
    lines.append("")
    return "\n".join(lines) + "\n"


def build_system_prompt(db: Session) -> str:
    try:
        active_statuses = [
            ShipmentStatusEnum.IN_TRANSIT,
            ShipmentStatusEnum.AT_BORDER,
            ShipmentStatusEnum.AT_WAREHOUSE,
            ShipmentStatusEnum.DELAYED,
            ShipmentStatusEnum.PENDING,
        ]
        active = db.query(Shipment).filter(Shipment.status.in_(active_statuses)).count()
        delayed = db.query(Shipment).filter(Shipment.status == ShipmentStatusEnum.DELAYED).count()
        at_risk = (
            db.query(Shipment)
            .filter(Shipment.risk_score >= 0.6)
            .filter(Shipment.status.in_(active_statuses))
            .count()
        )
        trucks_online = db.query(Truck).filter(
            Truck.status.in_(
                [
                    TruckStatusEnum.MOVING,
                    TruckStatusEnum.IDLE,
                    TruckStatusEnum.AT_WAREHOUSE,
                    TruckStatusEnum.AT_BORDER,
                ]
            )
        ).count()
        border_alerts = (
            db.query(Alert)
            .filter(Alert.alert_type == AlertTypeEnum.BORDER)
            .filter(Alert.is_read == False)
            .count()
        )

        total = db.query(Shipment).count()
        on_time_rate = round(((total - delayed) / total * 100) if total > 0 else 100.0, 1)

        avg_delay_result = (
            db.query(func.avg(Shipment.delay_minutes))
            .filter(Shipment.delay_minutes != None)
            .scalar()
        )
        avg_delay = round(float(avg_delay_result), 0) if avg_delay_result else 0

        # Fetch all context in parallel (fail-safe — each call is independent)
        fetch_fns = {
            'ml_metrics': _fetch_ml_metrics,
            'predictions_summary': _fetch_predictions_summary,
            'anomalies': _fetch_anomalies,
            'route_data': _fetch_route_recommendations,
            'fleet_data': _fetch_fleet_balance,
        }
        results: Dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fn): key for key, fn in fetch_fns.items()}
            for future in as_completed(futures, timeout=6):
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception:
                    results[key] = None

        ml_metrics = results.get('ml_metrics')
        predictions_summary = results.get('predictions_summary')
        anomalies = results.get('anomalies') or []
        route_data = results.get('route_data')
        fleet_data = results.get('fleet_data')

        ml_section = _build_ml_section(ml_metrics, predictions_summary, anomalies)
        borders_section = _build_borders_section(db)
        warehouses_section = _build_warehouses_section(db)
        routes_section = _build_routes_section(route_data)
        fleet_section = _build_fleet_section(fleet_data)

        return SYSTEM_PROMPT_TEMPLATE.format(
            active_shipments=active,
            delayed=delayed,
            at_risk=at_risk,
            trucks_online=trucks_online,
            border_alerts=border_alerts,
            on_time_rate=on_time_rate,
            avg_delay=avg_delay,
            ml_section=ml_section,
            borders_section=borders_section,
            warehouses_section=warehouses_section,
            routes_section=routes_section,
            fleet_section=fleet_section,
        )
    except Exception as e:
        logger.error(f"Error building system prompt: {e}")
        return SYSTEM_PROMPT_TEMPLATE.format(
            active_shipments="N/A",
            delayed="N/A",
            at_risk="N/A",
            trucks_online="N/A",
            border_alerts="N/A",
            on_time_rate="N/A",
            avg_delay="N/A",
            ml_section="",
            borders_section="",
            warehouses_section="",
            routes_section="",
            fleet_section="",
        )


@router.post("/chat", response_model=CopilotResponse)
def chat(request: CopilotRequest, db: Session = Depends(get_db)):
    if not settings.anthropic_api_key:
        return CopilotResponse(
            response=(
                "AI Copilot is not configured. Please set the ANTHROPIC_API_KEY environment variable "
                "to enable the AI Copilot. Once configured, I can help with SLA risk analysis, "
                "route recommendations, border delay insights, and warehouse congestion management."
            ),
            model="none",
        )

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        system_prompt = build_system_prompt(db)

        messages = []
        for msg in request.history[-10:]:
            if msg.role in ("user", "assistant"):
                messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": request.message})

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        )

        answer = response.content[0].text if response.content else "No response generated."
        return CopilotResponse(response=answer, model="claude-sonnet-4-6")

    except Exception as e:
        logger.error(f"Copilot error: {e}")
        return CopilotResponse(
            response=f"An error occurred while processing your request: {str(e)}. Please check the API key and try again.",
            model="error",
        )
