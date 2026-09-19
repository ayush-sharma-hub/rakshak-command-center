"""
Project Rakshak — Streamlit Analytics Dashboard
Uttarakhand SEOC Intelligence & Monitoring Centre
Run: streamlit run streamlit_app.py --server.port 8501
"""

import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Rakshak SEOC — Analytics",
    page_icon="🏔️",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "http://localhost:3000/api"

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@500;700&display=swap');

    .stApp { background-color: #0a0e1a; color: #c9d1e0; }
    .main .block-container { padding: 1.2rem 2rem; }

    /* Header */
    .rakshak-header {
        background: linear-gradient(135deg, #0d1b2a 0%, #1a2f4a 100%);
        border: 1px solid #00d4ff33;
        border-radius: 12px;
        padding: 18px 28px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .rakshak-header h1 {
        font-family: 'Rajdhani', sans-serif;
        font-size: 2rem;
        color: #00d4ff;
        margin: 0;
        text-shadow: 0 0 20px #00d4ff55;
        letter-spacing: 3px;
    }
    .rakshak-header .status-pill {
        background: #00ff8833;
        border: 1px solid #00ff88;
        color: #00ff88;
        padding: 6px 16px;
        border-radius: 20px;
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.85rem;
    }

    /* Metric Cards */
    .metric-card {
        background: linear-gradient(135deg, #0d1b2a, #0f2236);
        border: 1px solid #00d4ff22;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        margin-bottom: 10px;
    }
    .metric-card .label {
        font-size: 0.72rem;
        color: #7a9bb5;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 6px;
        font-family: 'Share Tech Mono', monospace;
    }
    .metric-card .value {
        font-size: 2.2rem;
        font-weight: 700;
        font-family: 'Rajdhani', sans-serif;
        color: #00d4ff;
    }
    .metric-card .value.red { color: #ff4757; }
    .metric-card .value.orange { color: #ffa502; }
    .metric-card .value.green { color: #00ff88; }

    /* River Basin Bars */
    .basin-row {
        background: #0d1b2a;
        border: 1px solid #1e3a5f;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }
    .basin-name { font-weight: 600; color: #c9d1e0; margin-bottom: 6px; font-size: 0.9rem; }
    .basin-status-DANGER  { color: #ff4757; font-weight: 700; }
    .basin-status-WARNING { color: #ffa502; font-weight: 700; }
    .basin-status-NOMINAL { color: #00d4ff; }
    .basin-status-SAFE    { color: #00ff88; }

    /* SOS Table */
    .sos-card {
        border-left: 3px solid #ff4757;
        background: #0d1b2a;
        border-radius: 0 8px 8px 0;
        padding: 10px 14px;
        margin-bottom: 8px;
    }
    .sos-card.dispatched { border-left-color: #ffa502; }
    .sos-card.cleared { border-left-color: #00ff88; }

    /* Divider */
    hr { border-color: #1e3a5f !important; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #080d1a; }
    section[data-testid="stSidebar"] * { color: #c9d1e0 !important; }

    /* Plotly background fix */
    .js-plotly-plot .plotly .bg { fill: #0a0e1a !important; }

    /* Command-center design system overrides */
    :root { --canvas:#060a12; --panel:#0e1728; --line:rgba(148,163,184,.16); --ink:#edf5ff; --muted:#8da1bd; --cyan:#4ee9ff; --violet:#8b7cff; }
    .stApp {
        background: radial-gradient(circle at 88% -8%, rgba(88,72,188,.24), transparent 33%),
                    radial-gradient(circle at 10% 72%, rgba(5,117,148,.13), transparent 27%), var(--canvas) !important;
        color:var(--ink);
    }
    .main .block-container { max-width:1540px; padding:1.5rem 2.2rem 2rem; }
    .rakshak-header { background:linear-gradient(115deg,rgba(19,30,50,.94),rgba(30,29,75,.82),rgba(6,38,54,.7)); border-color:rgba(117,138,255,.3); border-radius:18px; box-shadow:0 18px 45px rgba(0,0,0,.23); }
    .rakshak-header h1 { color:#f5f7ff; font-family:'Rajdhani',sans-serif; font-weight:700; text-shadow:none; }
    .rakshak-header .status-pill { background:rgba(34,197,94,.1); border-color:rgba(74,222,128,.35); letter-spacing:.06em; }
    .metric-card { background:linear-gradient(145deg,rgba(20,31,52,.84),rgba(10,16,29,.86)); border-color:var(--line); border-radius:16px; box-shadow:0 12px 28px rgba(0,0,0,.15); padding:18px; transition:transform .18s ease,border-color .18s ease; }
    .metric-card:hover { transform:translateY(-3px); border-color:rgba(78,233,255,.35); }
    .metric-card .label { color:var(--muted); }.metric-card .value { color:var(--cyan); text-shadow:0 0 18px rgba(78,233,255,.13); }
    .basin-row,.sos-card { background:linear-gradient(135deg,rgba(15,25,42,.88),rgba(7,13,24,.82)); border-color:var(--line); box-shadow:0 8px 22px rgba(0,0,0,.12); }
    .basin-row { border-radius:12px; }.sos-card { border-radius:0 12px 12px 0; }
    h1,h2,h3 { letter-spacing:.015em!important; color:var(--ink)!important; }
    [data-testid="stSidebar"] { background:linear-gradient(180deg,#0d1423,#060a12)!important; border-right:1px solid var(--line); }
    [data-testid="stSidebar"] .stButton > button { border-color:rgba(139,124,255,.42)!important; background:linear-gradient(100deg,#5b4acb,#3d67bb)!important; color:white!important; border-radius:10px!important; }
    .stButton > button { border-radius:10px!important; transition:transform .16s ease,filter .16s ease!important; }.stButton > button:hover { transform:translateY(-1px); filter:brightness(1.1); }
    [data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:14px; overflow:hidden; }
    div[data-baseweb="select"] > div, [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea { background:#0a1220!important; border-color:rgba(148,163,184,.25)!important; color:var(--ink)!important; border-radius:10px!important; }
    hr { border-color:var(--line)!important; }
    @media(max-width: 720px) { .main .block-container { padding:1rem; }.rakshak-header { padding:16px 18px; }.rakshak-header h1 { font-size:1.55rem; } }
</style>
""", unsafe_allow_html=True)


# ─── Helpers ───────────────────────────────────────────────────────────────────
def fetch(endpoint: str, fallback=None):
    try:
        r = requests.get(f"{API_BASE}{endpoint}", timeout=4)
        r.raise_for_status()
        return r.json()
    except Exception:
        return fallback


def status_color(s: str) -> str:
    return {"DANGER": "🔴", "WARNING": "🟡", "NOMINAL": "🔵", "SAFE": "🟢",
            "PENDING": "🔴", "DISPATCHED": "🟡", "EN ROUTE": "🟠", "CLEARED": "🟢",
            "DEPLOYED": "🟠", "STANDBY": "🔵", "PATROL EN ROUTE": "🟡",
            "PRE-POSITIONED": "🟢", "CLEARING DEBRIS": "🟠"}.get(s, "⚪")


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏔️ RAKSHAK SEOC")
    st.markdown("**Uttarakhand Disaster Intelligence**")
    st.markdown("---")
    auto_refresh = st.toggle("⚡ Live Auto-Refresh", value=True)
    refresh_rate = st.slider("Refresh Interval (sec)", 5, 60, 15)
    st.markdown("---")
    st.markdown("**🔗 Quick Links**")
    st.markdown("- [🌐 Main Dashboard](http://localhost:3000/dashboard.html)")
    st.markdown("- [🗺️ Tactical Map](http://localhost:3000/map.html)")
    st.markdown("- [🚨 Alerts Hub](http://localhost:3000/alerts.html)")
    st.markdown("- [📡 Radio Comms](http://localhost:3000/assistant.html)")
    st.markdown("- [⚗️ Simulator](http://localhost:3000/simulator.html)")
    st.markdown("- [📋 API Docs](http://localhost:3000/api/docs)")
    st.markdown("---")

    # Gemini AI Broadcast Test
    st.markdown("**🤖 AI Broadcast Test**")
    sim_city = st.selectbox("City", ["Kedarnath", "Chamoli", "Joshimath", "Uttarkashi", "Rudraprayag"])
    sim_risk = st.selectbox("Risk Level", ["CRITICAL", "HIGH", "MEDIUM", "LOW"])
    sim_rain = st.slider("Rainfall (mm)", 0, 300, 120)
    if st.button("🔊 Generate AI Broadcast"):
        try:
            resp = requests.post(f"{API_BASE}/broadcast/synthesize", json={
                "city": sim_city, "risk_level": sim_risk,
                "rainfall_mm": float(sim_rain), "slope_deg": 35.0,
            }, timeout=10)
            data = resp.json()
            bc = data.get("broadcast", {})
            st.success("✅ Broadcast Generated!")
            st.info(f"🇬🇧 **EN:** {bc.get('english','N/A')}")
            st.info(f"🇮🇳 **HI:** {bc.get('hindi','N/A')}")
            st.caption(f"Source: `{bc.get('source','fallback')}`")
        except Exception as e:
            st.error(f"API Error: {e}")

    st.markdown("---")
    now_str = datetime.now().strftime("%d %b %Y — %H:%M:%S IST")
    st.caption(f"🕐 {now_str}")


# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="rakshak-header">
    <h1>🏔️ RAKSHAK — SEOC Analytics</h1>
    <div class="status-pill">⬤ OPERATIONAL — {datetime.now().strftime('%H:%M IST')}</div>
</div>
""", unsafe_allow_html=True)


# ─── Fetch Live Data ──────────────────────────────────────────────────────────
state    = fetch("/state", {})
basins   = fetch("/river-basins", [])
units    = fetch("/field-units", [])
sos_list = fetch("/sos?", [])
incidents = fetch("/incidents?limit=30", [])

summary = state.get("summary", {})

# ─── KPI Row ──────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)

def metric(col, label, value, color=""):
    col.markdown(f"""
    <div class="metric-card">
        <div class="label">{label}</div>
        <div class="value {color}">{value}</div>
    </div>""", unsafe_allow_html=True)

metric(c1, "🔴 Pending SOS", summary.get("pendingSOSCount", "—"), "red")
metric(c2, "⚠️ Critical Basins", summary.get("criticalBasins", "—"), "orange" if summary.get("criticalBasins",0) > 0 else "green")
metric(c3, "🚁 Units Deployed", summary.get("deployedUnits", "—"), "orange")
metric(c4, "👥 Field Strength", summary.get("totalFieldStrength", "—"))
metric(c5, "📋 Total Incidents", len(incidents), "red" if len(incidents) > 10 else "")

st.markdown("---")

# ─── Row 1: River Basins + Field Units ────────────────────────────────────────
col_a, col_b = st.columns([3, 2])

with col_a:
    st.markdown("### 🌊 River Basin Gauge Status")
    if basins:
        try:
            import plotly.graph_objects as go
            fig = go.Figure()
            for b in basins:
                name = b.get("river","").split(" at ")[0]
                curr = b.get("current_level", 0)
                danger = b.get("danger_level", curr * 1.1)
                warn   = b.get("warning_level", curr * 1.05)
                pct    = min(100, (curr / danger) * 100)
                color  = "#ff4757" if b["status"]=="DANGER" else "#ffa502" if b["status"]=="WARNING" else "#00d4ff"
                fig.add_trace(go.Bar(
                    name=name, x=[pct], y=[name],
                    orientation="h",
                    marker=dict(color=color, opacity=0.85),
                    text=f"{curr:.1f}m ({b.get('trend','Steady')})",
                    textposition="inside",
                ))
            fig.update_layout(
                showlegend=False, barmode="overlay",
                paper_bgcolor="#0a0e1a", plot_bgcolor="#0d1b2a",
                font=dict(color="#c9d1e0", size=12),
                margin=dict(l=10, r=10, t=10, b=10),
                height=280,
                xaxis=dict(title="% of Danger Level", range=[0, 110],
                           gridcolor="#1e3a5f", ticksuffix="%"),
                yaxis=dict(gridcolor="#1e3a5f"),
            )
            fig.add_vline(x=100, line_dash="dash", line_color="#ff4757",
                          annotation_text="DANGER", annotation_font_color="#ff4757")
            fig.add_vline(x=85, line_dash="dot", line_color="#ffa502",
                          annotation_text="WARNING", annotation_font_color="#ffa502")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        except ImportError:
            for b in basins:
                pct = min(100, (b["current_level"] / b["danger_level"]) * 100)
                st.progress(pct/100, text=f"{b['river']} — {b['current_level']}m {status_color(b['status'])} {b['status']}")
    else:
        st.warning("River basin data unavailable.")

with col_b:
    st.markdown("### 🚁 Field Units")
    if units:
        for u in units:
            st.markdown(f"""
            <div class="basin-row">
                <div class="basin-name">{status_color(u['status'])} {u['callsign']} — {u['unit_type']}</div>
                <div style="font-size:0.8rem;color:#7a9bb5">{u['sector']}</div>
                <div style="font-size:0.82rem;margin-top:4px">
                    👥 <b>{u['strength']}</b> personnel &nbsp;|&nbsp;
                    <span class="basin-status-{u['status']}">{u['status']}</span>
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.warning("Field unit data unavailable.")

st.markdown("---")

# ─── Row 2: SOS Signals + Incident Log ────────────────────────────────────────
col_c, col_d = st.columns([2, 3])

with col_c:
    st.markdown("### 🆘 Active SOS Signals")
    if sos_list:
        for s in sos_list[:8]:
            css_cls = "dispatched" if s["status"] == "DISPATCHED" else ("cleared" if s["status"] == "CLEARED" else "")
            st.markdown(f"""
            <div class="sos-card {css_cls}">
                <div style="font-weight:700;font-size:0.9rem">{s['id']} — {s['caller_name']}</div>
                <div style="font-size:0.78rem;color:#7a9bb5;margin:3px 0">{s.get('location_name','Unknown')}</div>
                <div style="font-size:0.8rem">
                    {status_color(s['status'])} <b>{s['status']}</b>
                    &nbsp;→&nbsp; {s.get('assigned_unit','Unassigned')}
                    {f"&nbsp;| ⏱ {s['eta_minutes']} min" if s.get('eta_minutes') else ""}
                </div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("No active SOS signals.")

    # Quick SOS Form
    st.markdown("**📞 Log New SOS**")
    with st.form("sos_form", clear_on_submit=True):
        caller = st.text_input("Caller Name")
        loc    = st.text_input("Location")
        det    = st.text_area("Details", height=60)
        lat    = st.number_input("Latitude", value=30.3165, format="%.4f")
        lng    = st.number_input("Longitude", value=78.0322, format="%.4f")
        if st.form_submit_button("📡 Submit SOS"):
            if caller and loc:
                try:
                    r = requests.post(f"{API_BASE}/sos", json={
                        "caller_name": caller, "location_name": loc,
                        "details": det, "lat": lat, "lng": lng,
                    }, timeout=5)
                    d = r.json()
                    st.success(f"✅ {d['sos_id']} — Assigned: {d['assigned_unit']} (ETA {d.get('eta_minutes','?')} min)")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Please fill in caller name and location.")

with col_d:
    st.markdown("### 📋 Incident Log")
    if incidents:
        df_inc = pd.DataFrame(incidents)[["type", "zone", "priority", "msg", "created_at"]]
        df_inc.columns = ["Type", "Zone", "Priority", "Message", "Time"]
        df_inc["Time"] = pd.to_datetime(df_inc["Time"]).dt.strftime("%d %b %H:%M")
        df_inc["Message"] = df_inc["Message"].str[:80] + "…"

        # Color priority
        def color_priority(val):
            colors = {"CRITICAL": "color:#ff4757", "HIGH": "color:#ffa502",
                      "MEDIUM": "color:#00d4ff", "INFO": "color:#7a9bb5"}
            return colors.get(val, "")

        st.dataframe(
            df_inc,
            use_container_width=True,
            height=380,
            column_config={
                "Priority": st.column_config.TextColumn("Priority"),
                "Message": st.column_config.TextColumn("Message", width="large"),
            },
            hide_index=True,
        )

        # Priority breakdown chart
        try:
            import plotly.express as px
            priority_counts = df_inc["Priority"].value_counts().reset_index()
            priority_counts.columns = ["Priority", "Count"]
            color_map = {"CRITICAL": "#ff4757", "HIGH": "#ffa502", "MEDIUM": "#00d4ff", "INFO": "#7a9bb5"}
            fig2 = px.pie(
                priority_counts, names="Priority", values="Count",
                color="Priority", color_discrete_map=color_map,
                hole=0.55,
            )
            fig2.update_layout(
                paper_bgcolor="#0a0e1a", font=dict(color="#c9d1e0"),
                showlegend=True, height=200, margin=dict(l=0, r=0, t=10, b=0),
            )
            fig2.update_traces(textinfo="percent+label")
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        except ImportError:
            pass
    else:
        st.info("No incidents logged yet.")

st.markdown("---")

# ─── Run Simulation Section ───────────────────────────────────────────────────
st.markdown("### ⚗️ Real-Time Risk Simulator")
sc1, sc2, sc3, sc4, sc5 = st.columns(5)
sim2_city  = sc1.selectbox("City", ["Kedarnath","Joshimath","Chamoli","Badrinath","Uttarkashi","Rudraprayag","Pithoragarh","Tehri"], key="s2c")
sim2_rain  = sc2.slider("Rainfall mm", 0, 350, 150, key="s2r")
sim2_slope = sc3.slider("Slope °", 5, 65, 38, key="s2sl")
sim2_elev  = sc4.slider("Elevation m", 500, 6000, 3000, key="s2e")
sim2_cb    = sc5.checkbox("☁️ Cloudburst", key="s2cb")

if st.button("▶ Run Simulation", type="primary"):
    with st.spinner("Calculating risk..."):
        try:
            r = requests.post(f"{API_BASE}/simulate", json={
                "city": sim2_city, "rainfall": sim2_rain,
                "slope": sim2_slope, "elevation": sim2_elev,
                "soil": "Clay", "cloudburst": sim2_cb,
            }, timeout=15)
            result = r.json()
            rr1, rr2, rr3, rr4 = st.columns(4)
            colors = {"CRITICAL":"🔴","HIGH":"🟠","MEDIUM":"🟡","LOW":"🟢"}
            rr1.metric("Risk Level", f"{colors.get(result['riskLevel'],'')} {result['riskLevel']}")
            rr2.metric("Risk Score", f"{result['riskScore']}/100")
            rr3.metric("Population at Risk", f"{result['populationAtRisk']:,}")
            rr4.metric("Lead Time", f"{result['leadTimeMinutes']} min")
            st.info(f"**AI Analysis:** {result.get('explanation','N/A')}")
            with st.expander("📊 Runoff Physics"):
                ro = result.get("runoff", {})
                st.write(f"- Surface Runoff: **{ro.get('runoff_m3ps','—')} m³/s**")
                st.write(f"- Debris Velocity: **{ro.get('velocity_ms','—')} m/s**")
                st.write(f"- Time of Concentration: **{ro.get('time_of_concentration_min','—')} min**")
        except Exception as e:
            st.error(f"Simulation failed: {e}")

# ─── Simulation History ───────────────────────────────────────────────────────
sim_hist = fetch("/simulate/history?limit=10", [])
if sim_hist:
    with st.expander("📈 Simulation History (Last 10 Runs)"):
        df_sim = pd.DataFrame(sim_hist)[["city_name","rainfall","slope","risk_level","risk_score","pop_at_risk","lead_time_minutes","created_at"]]
        df_sim.columns = ["City","Rain(mm)","Slope°","Risk","Score","Pop@Risk","Lead(min)","Time"]
        df_sim["Time"] = pd.to_datetime(df_sim["Time"]).dt.strftime("%d %b %H:%M")
        st.dataframe(df_sim, use_container_width=True, hide_index=True)

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#3a5a7a;font-size:0.8rem;font-family:monospace'>"
    "RAKSHAK SEOC v2.0 · Uttarakhand Disaster Intelligence · SDMA · Helpline 1077 · 112"
    "</div>",
    unsafe_allow_html=True
)

# ─── Auto-Refresh ─────────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
