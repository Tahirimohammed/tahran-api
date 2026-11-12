import html
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import plotly.graph_objects as go
import redis
import streamlit as st


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DEVICE_COUNT = 20
ALERTS_KEY = "alerts:recent"
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

st.set_page_config(page_title="Surveillance IoT", page_icon="◈", layout="wide")


st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

    :root {
        --page: #0e1117;
        --surface: #161b22;
        --surface-raised: #1c2128;
        --line: #30363d;
        --text: #e6edf3;
        --muted: #8b949e;
        --green: #3fb950;
        --red: #f85149;
        --cyan: #58a6ff;
    }
    html, body, [data-testid="stAppViewContainer"] {
        background: var(--page);
        color: var(--text);
        font-family: 'DM Sans', sans-serif;
    }
    [data-testid="stHeader"] { background: rgba(14, 17, 23, 0.92); }
    [data-testid="stSidebar"] {
        background: #11161d;
        border-right: 1px solid var(--line);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: var(--muted); }
    [data-testid="stMainBlockContainer"] { max-width: 1500px; padding-top: 2rem; }
    h1, h2, h3, .brand-title { font-family: 'Space Grotesk', sans-serif !important; }
    h1 { font-size: 2rem !important; letter-spacing: 0 !important; color: #f8fafc; }
    .page-subtitle { color: var(--muted); margin: -0.55rem 0 1.6rem; font-size: 0.95rem; }
    .brand { display: flex; align-items: center; gap: 0.75rem; padding: 0.3rem 0 1.5rem; }
    .brand-mark {
        display: grid; place-items: center; width: 38px; height: 38px; border-radius: 10px;
        background: linear-gradient(145deg, rgba(56,189,248,.2), rgba(16,185,129,.12));
        color: var(--cyan); border: 1px solid rgba(56,189,248,.28); font-size: 1.2rem;
    }
    .brand-title { color: #f8fafc; font-weight: 700; font-size: 1rem; }
    .brand-caption { color: var(--muted); font-size: 0.72rem; margin-top: 0.1rem; }
    .section-heading {
        display: flex; align-items: center; gap: 0.55rem; margin: 1.65rem 0 0.85rem;
        color: #e2e8f0; font: 600 1.05rem 'Space Grotesk', sans-serif;
    }
    .section-heading:before { content: ''; width: 3px; height: 17px; border-radius: 2px; background: var(--cyan); }
    .kpi-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
    .kpi-card {
        min-height: 112px; padding: 17px 19px; background: var(--surface);
        border: 1px solid var(--line); border-radius: 8px;
        box-shadow: 0 4px 14px rgba(0, 0, 0, .18);
    }
    .kpi-label { color: var(--muted); font-size: 0.82rem; font-weight: 500; }
    .kpi-row { display: flex; align-items: center; justify-content: space-between; margin-top: 12px; }
    .kpi-value { color: #f8fafc; font: 700 1.7rem 'Space Grotesk', sans-serif; }
    .kpi-value.alert-value { color: #f87171; }
    .kpi-icon { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 8px; background: #1c2128; color: var(--cyan); }
    .kpi-icon.alert-icon { color: #f87171; background: rgba(239,68,68,.12); }
    .kpi-icon.ok-icon { color: var(--green); background: rgba(16,185,129,.12); }
    .kpi-status { display: flex; align-items: center; gap: 0.5rem; color: var(--green); font-size: 1rem; font-weight: 600; }
    .status-dot { width: 8px; height: 8px; display: inline-block; border-radius: 50%; background: currentColor; }
    .status-dot.online { box-shadow: 0 0 10px rgba(16,185,129,.55); }
    .status-dot.offline { color: var(--red); box-shadow: 0 0 10px rgba(239,68,68,.5); }
    .device-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
    .device-card {
        min-width: 0; min-height: 176px; padding: 15px; border-radius: 8px;
        background: var(--surface); border: 1px solid var(--line);
        border-top: 2px solid var(--green); box-shadow: 0 4px 14px rgba(0, 0, 0, .16);
    }
    .device-card.is-critical {
        border-color: rgba(248,81,73,.48); border-top-color: var(--red);
    }
    @keyframes alert-glow {
        0%, 100% { box-shadow: 0 0 0 rgba(239,68,68,0); }
        50% { box-shadow: 0 0 16px rgba(248,81,73,.14); }
    }
    .device-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
    .device-id { color: #f1f5f9; font: 600 0.95rem 'Space Grotesk', sans-serif; }
    .device-seen { margin-top: 4px; color: var(--muted); font-size: 0.7rem; }
    .device-badge {
        flex: 0 0 auto; display: inline-flex; align-items: center; gap: 6px; padding: 4px 8px;
        border-radius: 999px; background: rgba(63,185,80,.12); color: #7ee787; font-size: 0.68rem; font-weight: 600;
    }
    .is-critical .device-badge { background: rgba(248,81,73,.13); color: #ff7b72; }
    .device-badge .status-dot { width: 6px; height: 6px; }
    .device-metrics { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin-top: 20px; padding-top: 12px; border-top: 1px solid var(--line); }
    .metric-label { color: var(--muted); font-size: 0.7rem; }
    .metric-value { margin-top: 4px; color: #f8fafc; font: 600 1rem 'Space Grotesk', sans-serif; }
    .metric-unit { color: var(--muted); font: 400 0.72rem 'DM Sans', sans-serif; }
    .empty-state { padding: 28px; text-align: center; color: var(--muted); background: var(--surface); border: 1px dashed var(--line); border-radius: 8px; }
    [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 8px; }
    @media (max-width: 1050px) { .device-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
    @media (max-width: 760px) {
        [data-testid="stMainBlockContainer"] { padding: 1.25rem 1rem; }
        .device-grid { grid-template-columns: 1fr; }
        .kpi-grid { grid-template-columns: 1fr; gap: 10px; }
        .kpi-card { min-height: 92px; }
    }
    @media (prefers-reduced-motion: reduce) { .device-card.is-critical { animation: none; } }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid var(--line); }
    .stTabs [data-baseweb="tab"] { color: var(--muted); }
    .stTabs [aria-selected="true"] { color: var(--text) !important; }
    [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def parse_timestamp(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp


def format_timestamp(value: str) -> str:
    timestamp = parse_timestamp(value)
    if timestamp is None:
        return "Jamais" if not value else "Inconnue"
    return timestamp.astimezone().strftime("%d/%m/%Y %H:%M:%S")


@st.cache_data(ttl=5)
def get_dashboard_data() -> tuple[bool, list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], Optional[str]]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    cutoff_id = f"{int(cutoff.timestamp() * 1000)}-0"
    try:
        redis_client.ping()
        with redis_client.pipeline() as pipeline:
            for device_number in range(1, DEVICE_COUNT + 1):
                pipeline.hgetall(f"device:device_{device_number:02d}")
            device_states = pipeline.execute()
        stream_entries = redis_client.xrange("telemetry:stream", min=cutoff_id, max="+")
        alert_ids = redis_client.zrevrange(ALERTS_KEY, 0, -1)
        alert_values = redis_client.mget(alert_ids) if alert_ids else []
    except redis.RedisError as exc:
        return False, [{} for _ in range(DEVICE_COUNT)], [], [], str(exc)

    metric_rows = [{"stream_id": stream_id, **fields} for stream_id, fields in stream_entries]
    alert_rows = []
    expired_ids = []
    for alert_id, value in zip(alert_ids, alert_values):
        if value is None:
            expired_ids.append(alert_id)
            continue
        try:
            alert_rows.append(json.loads(value))
        except json.JSONDecodeError:
            continue
    if expired_ids:
        redis_client.zrem(ALERTS_KEY, *expired_ids)

    return True, device_states, metric_rows, alert_rows, None


def classify_device(device_id: str, state: dict[str, str], alerts_by_device: dict[str, dict[str, str]]) -> str:
    if not state or state.get("status") == "offline":
        return "Hors ligne"
    alert = alerts_by_device.get(device_id)
    if alert is None:
        return "Normal"
    if alert.get("type") == "overheating":
        return "Chauffage"
    if alert.get("type") == "invalid_measurement":
        return "Données invalides"
    if alert.get("type") == "device_offline":
        return "Hors ligne"
    return "Normal"


def render_dashboard(status_filter: str, class_filter: str) -> None:
    redis_connected, device_states, metric_rows, alert_rows, redis_error = get_dashboard_data()
    alerts_by_device = {}
    for alert in alert_rows:
        alerts_by_device.setdefault(alert.get("device_id", ""), alert)

    devices = []
    for index, state in enumerate(device_states):
        device_id = f"device_{index + 1:02d}"
        device_class = classify_device(device_id, state, alerts_by_device)
        status = "Hors ligne" if device_class == "Hors ligne" else (
            "Alerte" if device_class != "Normal" else "En ligne"
        )
        if status_filter != "Tous" and status != status_filter:
            continue
        if class_filter != "Toutes" and device_class != class_filter:
            continue
        devices.append({"device_id": device_id, "state": state, "class": device_class, "status": status})

    st.markdown(
        '<h1>Surveillance IoT</h1><p class="page-subtitle">'
        'État des équipements, alertes et télémétrie en temps réel.</p>',
        unsafe_allow_html=True,
    )

    server_value = "Connecté" if redis_connected else "Hors ligne"
    server_status = "online" if redis_connected else "offline"
    st.markdown(
        f"""
        <div class="kpi-grid">
          <div class="kpi-card"><div class="kpi-label">Mesures reçues (24 h)</div>
            <div class="kpi-row"><div class="kpi-value">{len(metric_rows):,}</div><span class="kpi-icon">⌁</span></div></div>
          <div class="kpi-card"><div class="kpi-label">Alertes actives (24 h)</div>
            <div class="kpi-row"><div class="kpi-value alert-value">{len(alert_rows)}</div><span class="kpi-icon alert-icon">!</span></div></div>
          <div class="kpi-card"><div class="kpi-label">Statut du serveur Redis</div>
            <div class="kpi-row"><div class="kpi-status"><span class="status-dot {server_status}"></span>{server_value}</div>
              <span class="kpi-icon {'ok-icon' if redis_connected else 'alert-icon'}">◈</span></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if redis_error:
        st.warning(f"Redis indisponible : {redis_error}")

    equipment_tab, telemetry_tab, raw_tab = st.tabs(
        ["🖥️ Équipements", "📈 Graphiques & Télémétrie", "📋 Données Brutes"]
    )

    with equipment_tab:
        st.markdown('<div class="section-heading">Équipements</div>', unsafe_allow_html=True)
        if devices:
            for start in range(0, len(devices), 3):
                columns = st.columns(3, gap="medium")
                for column, device in zip(columns, devices[start:start + 3]):
                    state = device["state"]
                    is_critical = device["status"] != "En ligne"
                    card_class = "is-critical" if is_critical else "is-normal"
                    dot_class = "offline" if is_critical else "online"
                    temperature = html.escape(state.get("temperature", "--"))
                    battery = html.escape(state.get("battery_level", "--"))
                    humidity = html.escape(state.get("humidity", "--"))
                    last_seen = html.escape(format_timestamp(state.get("timestamp", "")))
                    with column:
                        st.markdown(
                            f"""
                            <article class="device-card {card_class}">
                              <div class="device-top">
                                <div><div class="device-id">{device['device_id']}</div>
                                  <div class="device-seen">Dernier vu · {last_seen}</div></div>
                                <span class="device-badge"><span class="status-dot {dot_class}"></span>{device['status']}</span>
                              </div>
                              <div class="device-metrics">
                                <div><div class="metric-label">Température</div><div class="metric-value">{temperature}<span class="metric-unit"> °C</span></div></div>
                                <div><div class="metric-label">Batterie</div><div class="metric-value">{battery}<span class="metric-unit"> %</span></div></div>
                                <div><div class="metric-label">Humidité</div><div class="metric-value">{humidity}<span class="metric-unit"> %</span></div></div>
                              </div>
                            </article>
                            """,
                            unsafe_allow_html=True,
                        )
        else:
            st.markdown('<div class="empty-state">Aucun équipement ne correspond à ces filtres.</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-heading">Alertes récentes</div>', unsafe_allow_html=True)
        if alert_rows:
            st.dataframe(
                alert_rows,
                hide_index=True,
                width="stretch",
                column_config={
                    "id": "Événement",
                    "device_id": "Équipement",
                    "type": "Type",
                    "message": "Détail",
                    "temperature": "Température",
                    "timestamp": "Horodatage",
                },
            )
        else:
            st.markdown('<div class="empty-state">Aucune alerte active sur les dernières 24 heures.</div>', unsafe_allow_html=True)

    with telemetry_tab:
        st.markdown('<div class="section-heading">Évolution des températures</div>', unsafe_allow_html=True)
        history_by_device = {}
        for row in metric_rows[-1500:]:
            timestamp = parse_timestamp(row.get("timestamp", ""))
            try:
                temperature = float(row.get("temperature", ""))
            except (TypeError, ValueError):
                continue
            if timestamp is not None:
                history_by_device.setdefault(row.get("device_id", "Inconnu"), []).append((timestamp, temperature))

        if history_by_device:
            figure = go.Figure()
            for device_id, points in history_by_device.items():
                figure.add_trace(
                    go.Scatter(
                        x=[point[0] for point in points],
                        y=[point[1] for point in points],
                        mode="lines",
                        name=device_id,
                    )
                )
            figure.update_layout(
                template="plotly_dark",
                height=390,
                margin=dict(l=12, r=12, t=18, b=12),
                paper_bgcolor="#0e1117",
                plot_bgcolor="#161b22",
                xaxis_title="Heure",
                yaxis_title="Température (°C)",
                legend_title="Équipement",
            )
            st.plotly_chart(figure, width="stretch")
        else:
            st.info("Aucune mesure de température disponible sur les dernières 24 heures.")

        st.markdown('<div class="section-heading">Répartition des statuts</div>', unsafe_allow_html=True)
        status_counts = {"En ligne": 0, "Alerte": 0, "Hors ligne": 0}
        for index, state in enumerate(device_states):
            device_id = f"device_{index + 1:02d}"
            device_class = classify_device(device_id, state, alerts_by_device)
            status = "Hors ligne" if device_class == "Hors ligne" else (
                "Alerte" if device_class != "Normal" else "En ligne"
            )
            status_counts[status] += 1
        pie = go.Figure(
            data=[go.Pie(labels=list(status_counts), values=list(status_counts.values()), hole=0.56,
                          marker=dict(colors=["#3fb950", "#f85149", "#8b949e"]))]
        )
        pie.update_layout(
            template="plotly_dark",
            height=330,
            margin=dict(l=12, r=12, t=18, b=12),
            paper_bgcolor="#0e1117",
            legend_title="Statut",
        )
        st.plotly_chart(pie, width="stretch")

    with raw_tab:
        st.markdown('<div class="section-heading">Télémétrie reçue (24 h)</div>', unsafe_allow_html=True)
        if metric_rows:
            st.dataframe(metric_rows, hide_index=True, width="stretch", height=520)
        else:
            st.info("Aucune télémétrie disponible sur les dernières 24 heures.")


with st.sidebar:
    st.markdown(
        '<div class="brand"><div class="brand-mark">📡</div><div>'
        '<div class="brand-title">IoT Monitor</div><div class="brand-caption">SUPERVISION EN TEMPS RÉEL</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown("#### Actualisation")
    auto_refresh = st.toggle("Actualisation automatique", value=True)
    refresh_interval = st.slider("Fréquence (secondes)", min_value=1, max_value=10, value=3)
    st.markdown("#### Filtres")
    status_filter = st.selectbox("Statut", ["Tous", "En ligne", "Hors ligne", "Alerte"])
    class_filter = st.selectbox(
        "Classe d’équipements",
        ["Toutes", "Normal", "Chauffage", "Hors ligne", "Données invalides"],
    )


if auto_refresh:
    st.fragment(run_every=refresh_interval)(render_dashboard)(status_filter, class_filter)
else:
    render_dashboard(status_filter, class_filter)