"""
streamlit_app.py
────────────────
Streamlit UI for the Financial Deep Research Agent.

Run with:
    streamlit run streamlit_app.py
"""

import sys
import time
import threading
from pathlib import Path
from datetime import datetime

import streamlit as st

# ── ensure project root on path ───────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

# ── page config (MUST be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Financial Deep Research Agent",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Root variables ── */
:root {
    --bg:       #0a0e1a;
    --surface:  #111827;
    --card:     #1a2236;
    --border:   #1e3a5f;
    --accent:   #00d4ff;
    --accent2:  #7c3aed;
    --gold:     #f59e0b;
    --green:    #10b981;
    --red:      #ef4444;
    --text:     #e2e8f0;
    --muted:    #64748b;
    --radius:   12px;
}

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'Sora', sans-serif !important;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

.stApp { background: var(--bg); }

/* ── Hide default streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2rem !important; max-width: 1400px; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] * { font-family: 'Sora', sans-serif !important; }

/* ── Header banner ── */
.hero-banner {
    background: linear-gradient(135deg, #0a0e1a 0%, #0f1f3d 50%, #0a1628 100%);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.hero-banner::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(0,212,255,0.06) 0%, transparent 70%);
    border-radius: 50%;
}
.hero-banner::after {
    content: '';
    position: absolute;
    bottom: -30%;
    left: 20%;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(124,58,237,0.06) 0%, transparent 70%);
    border-radius: 50%;
}
.hero-title {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(90deg, #00d4ff, #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 0.3rem 0;
    letter-spacing: -0.5px;
}
.hero-sub {
    color: var(--muted);
    font-size: 0.9rem;
    font-weight: 300;
    letter-spacing: 0.5px;
}
.hero-badges {
    display: flex;
    gap: 0.6rem;
    margin-top: 1rem;
    flex-wrap: wrap;
}
.badge {
    background: rgba(0,212,255,0.08);
    border: 1px solid rgba(0,212,255,0.2);
    color: var(--accent);
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
    font-size: 0.72rem;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    letter-spacing: 0.5px;
}
.badge.purple {
    background: rgba(124,58,237,0.1);
    border-color: rgba(124,58,237,0.3);
    color: #a78bfa;
}
.badge.gold {
    background: rgba(245,158,11,0.1);
    border-color: rgba(245,158,11,0.3);
    color: var(--gold);
}

/* ── Cards ── */
.metric-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.2rem 1.5rem;
    text-align: center;
}
.metric-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--accent);
    font-family: 'JetBrains Mono', monospace;
}
.metric-label {
    font-size: 0.75rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-top: 0.2rem;
}

/* ── Section headers ── */
.section-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.6rem;
    margin: 1.5rem 0 1rem 0;
}

/* ── Step tracker ── */
.step-row {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    padding: 0.7rem 0;
    border-bottom: 1px solid rgba(30,58,95,0.4);
    animation: fadeIn 0.4s ease;
}
@keyframes fadeIn { from { opacity:0; transform:translateY(4px); } to { opacity:1; transform:none; } }
.step-num {
    background: rgba(0,212,255,0.1);
    border: 1px solid rgba(0,212,255,0.3);
    color: var(--accent);
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.72rem;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    flex-shrink: 0;
}
.step-content { flex: 1; }
.step-query {
    font-size: 0.82rem;
    color: var(--text);
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 0.2rem;
}
.step-insight {
    font-size: 0.76rem;
    color: var(--muted);
    line-height: 1.4;
}

/* ── Phase plan cards ── */
.phase-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: var(--radius);
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
}
.phase-title {
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.3rem;
}
.phase-obj {
    font-size: 0.8rem;
    color: var(--text);
    margin-bottom: 0.4rem;
}
.phase-queries {
    font-size: 0.72rem;
    color: var(--muted);
    font-family: 'JetBrains Mono', monospace;
}

/* ── Routing result ── */
.routing-box {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem 1.5rem;
    display: flex;
    align-items: center;
    gap: 1.5rem;
    margin-bottom: 1rem;
}
.routing-sector {
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--accent);
    font-family: 'JetBrains Mono', monospace;
}
.routing-detail { font-size: 0.8rem; color: var(--muted); }

/* ── Report display ── */
.report-container {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 2rem;
    line-height: 1.75;
}
.report-container h1 { color: var(--accent); font-size: 1.5rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; }
.report-container h2 { color: #a5c8ff; font-size: 1.1rem; margin-top: 1.5rem; }
.report-container h3 { color: var(--gold); font-size: 0.95rem; }
.report-container table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
.report-container th { background: rgba(0,212,255,0.08); color: var(--accent); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.5px; padding: 0.6rem 1rem; border: 1px solid var(--border); }
.report-container td { padding: 0.6rem 1rem; border: 1px solid var(--border); font-size: 0.82rem; color: var(--text); }
.report-container tr:nth-child(even) td { background: rgba(255,255,255,0.02); }
.report-container code { background: rgba(0,212,255,0.08); color: var(--accent); padding: 0.1rem 0.4rem; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; }
.report-container blockquote { border-left: 3px solid var(--accent2); padding-left: 1rem; color: var(--muted); margin: 1rem 0; }
.report-container ul li { margin: 0.3rem 0; }
.report-container strong { color: #a5c8ff; }

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, var(--accent), #0099bb) !important;
    color: #000 !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Sora', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    padding: 0.55rem 1.5rem !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(0,212,255,0.3) !important;
}

/* ── Inputs ── */
.stTextArea textarea, .stTextInput input, .stSelectbox select {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 8px !important;
    font-family: 'Sora', sans-serif !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(0,212,255,0.1) !important;
}

/* ── Slider ── */
.stSlider > div > div > div { background: var(--accent) !important; }

/* ── Status / alerts ── */
.status-running {
    background: rgba(0,212,255,0.06);
    border: 1px solid rgba(0,212,255,0.2);
    border-radius: var(--radius);
    padding: 1rem 1.5rem;
    color: var(--accent);
    font-size: 0.85rem;
    display: flex;
    align-items: center;
    gap: 0.8rem;
}
.status-done {
    background: rgba(16,185,129,0.08);
    border: 1px solid rgba(16,185,129,0.25);
    border-radius: var(--radius);
    padding: 1rem 1.5rem;
    color: var(--green);
    font-size: 0.85rem;
}
.status-error {
    background: rgba(239,68,68,0.08);
    border: 1px solid rgba(239,68,68,0.25);
    border-radius: var(--radius);
    padding: 1rem 1.5rem;
    color: var(--red);
    font-size: 0.85rem;
}

/* ── Progress bar ── */
.stProgress > div > div > div > div {
    background: linear-gradient(90deg, var(--accent), var(--accent2)) !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--surface) !important;
    border-bottom: 1px solid var(--border) !important;
    gap: 0;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--muted) !important;
    font-family: 'Sora', sans-serif !important;
    font-size: 0.82rem !important;
    border-bottom: 2px solid transparent !important;
    padding: 0.7rem 1.5rem !important;
}
.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom-color: var(--accent) !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
    font-family: 'Sora', sans-serif !important;
    font-size: 0.85rem !important;
}

/* ── Divider ── */
hr { border-color: var(--border) !important; }

/* ── Spinner ── */
.stSpinner > div { border-top-color: var(--accent) !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--surface); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }
</style>
""", unsafe_allow_html=True)


# ── SESSION STATE INIT ─────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "phase": "query",          # query | plan | research | report
        "query": "",
        "sector": None,
        "query_type": None,
        "confidence": None,
        "plan": None,
        "session": None,
        "steps_log": [],           # list of {step, query, insight}
        "current_step": 0,
        "max_steps": 10,
        "report": None,
        "report_path": None,
        "error": None,
        "history": [],             # list of past completed sessions
        "agent": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ── LAZY IMPORTS (avoid slow startup) ─────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def load_router():
    from agents.router_agent import RouterAgent
    return RouterAgent()


# ── HELPER: HTML components ───────────────────────────────────────────────────
def hero():
    st.markdown("""
    <div class="hero-banner">
        <p class="hero-title">💹 Financial Deep Research Agent</p>
        <p class="hero-sub">Multi-step AI research engine · Indian IT & Pharma sectors · Powered by Groq + Tavily</p>
        <div class="hero-badges">
            <span class="badge">LLaMA 3.3 70B</span>
            <span class="badge purple">Tavily Search</span>
            <span class="badge gold">5–20 Research Steps</span>
            <span class="badge">ChromaDB RAG</span>
            <span class="badge purple">yFinance</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def section(icon, title):
    st.markdown(f'<div class="section-header"><span>{icon}</span><span>{title}</span></div>', unsafe_allow_html=True)


def metric_row(metrics: list):
    cols = st.columns(len(metrics))
    for col, (label, value, color) in zip(cols, metrics):
        col.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color:{color}">{value}</div>
            <div class="metric-label">{label}</div>
        </div>""", unsafe_allow_html=True)


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
def sidebar():
    with st.sidebar:
        st.markdown("### 🗂 Navigation")
        st.markdown("---")

        # Current phase indicator
        phases = [
            ("🔍", "Query Input",   "query"),
            ("📋", "Research Plan", "plan"),
            ("⚙️", "Researching",   "research"),
            ("📄", "Report",        "report"),
        ]
        for icon, label, key in phases:
            active = st.session_state.phase == key
            color = "#00d4ff" if active else "#64748b"
            weight = "700" if active else "400"
            st.markdown(
                f'<div style="color:{color};font-weight:{weight};font-size:0.85rem;'
                f'padding:0.4rem 0.6rem;border-radius:6px;'
                f'background:{"rgba(0,212,255,0.08)" if active else "transparent"};'
                f'margin-bottom:2px">{icon} {label}</div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.markdown("### 💡 Example Queries")
        examples = [
            "Analyze Indian IT sector outlook 2025",
            "Compare TCS vs Infosys financial performance",
            "Emerging trends in Indian pharma biosimilars",
            "Impact of US tariffs on Indian IT sector",
            "Sun Pharma vs Dr Reddy's vs Cipla analysis",
            "HCL Technologies vs Wipro revenue comparison",
        ]
        for ex in examples:
            if st.button(f"→ {ex[:38]}…" if len(ex) > 38 else f"→ {ex}", key=f"ex_{ex[:20]}",
                         use_container_width=True):
                st.session_state.query = ex
                st.session_state.phase = "query"
                st.rerun()

        st.markdown("---")
        st.markdown("### 📁 Recent Reports")
        reports_dir = Path("./data/reports")
        if reports_dir.exists():
            reports = sorted(reports_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)[:5]
            if reports:
                for r in reports:
                    name = r.stem[:35] + "…" if len(r.stem) > 35 else r.stem
                    size = f"{r.stat().st_size / 1024:.1f} KB"
                    st.markdown(
                        f'<div style="font-size:0.75rem;color:#64748b;padding:0.3rem 0;'
                        f'border-bottom:1px solid #1e3a5f">'
                        f'<span style="color:#94a3b8">{name}</span><br>'
                        f'<span style="font-family:monospace">{size}</span></div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown('<span style="color:#64748b;font-size:0.8rem">No reports yet</span>',
                            unsafe_allow_html=True)
        else:
            st.markdown('<span style="color:#64748b;font-size:0.8rem">No reports yet</span>',
                        unsafe_allow_html=True)

        # Reset button
        st.markdown("---")
        if st.button("🔄 New Research Session", use_container_width=True):
            for key in ["phase","query","sector","query_type","confidence","plan",
                        "session","steps_log","current_step","report","report_path","error","agent"]:
                st.session_state[key] = init_state.__defaults__  # reset
            # Re-init properly
            st.session_state.phase = "query"
            st.session_state.query = ""
            st.session_state.plan = None
            st.session_state.steps_log = []
            st.session_state.report = None
            st.session_state.error = None
            st.rerun()


# ── PHASE 1: QUERY INPUT ──────────────────────────────────────────────────────
def phase_query():
    hero()

    col_main, col_info = st.columns([2, 1], gap="large")

    with col_main:
        section("🔍", "Research Query")
        query = st.text_area(
            "Enter your financial research query",
            value=st.session_state.query,
            height=110,
            placeholder=(
                "e.g. Analyze the Indian IT sector outlook for 2025\n"
                "e.g. Compare TCS vs Infosys financial performance\n"
                "e.g. Emerging trends in Indian pharma biosimilars"
            ),
            label_visibility="collapsed",
        )
        st.session_state.query = query

        col_steps, col_btn = st.columns([1, 1], gap="medium")
        with col_steps:
            max_steps = st.slider("Research depth (steps)", 5, 20, 10, 1)
            st.session_state.max_steps = max_steps
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            go = st.button("🚀 Start Research", use_container_width=True, type="primary")

        if go:
            if not query.strip():
                st.error("Please enter a research query.")
                return

            with st.spinner("Analyzing query & routing to sector agent..."):
                try:
                    router = load_router()
                    decision = router.route_query(query)
                except Exception as e:
                    st.error(f"Failed to load agent: {e}")
                    return

            if decision.sector == "out_of_scope":
                st.markdown(f"""
                <div class="status-error">
                    ❌ <strong>Out of scope</strong> — This query is outside the financial domain.<br>
                    <span style="font-size:0.78rem;margin-top:0.3rem;display:block">{decision.reasoning}</span>
                </div>""", unsafe_allow_html=True)
                return

            st.session_state.sector = decision.sector
            st.session_state.query_type = decision.query_type
            st.session_state.confidence = decision.confidence

            if decision.sector == "clarification_needed":
                st.warning(decision.clarification_question or "Please refine your query.")
                return

            # Route to plan phase
            st.session_state.phase = "plan"
            st.rerun()

    with col_info:
        section("🏭", "Covered Sectors")
        st.markdown("""
        <div class="phase-card" style="border-left-color:#00d4ff">
            <div class="phase-title">🖥 IT Services</div>
            <div class="phase-obj">TCS · Infosys · Wipro · HCL · Tech Mahindra · LTIMindtree · Mphasis</div>
            <div class="phase-queries">Deal TCV · Attrition · EBIT margins · Cloud revenue</div>
        </div>
        <div class="phase-card" style="border-left-color:#7c3aed">
            <div class="phase-title">💊 Pharmaceuticals</div>
            <div class="phase-obj">Sun Pharma · Dr Reddy's · Cipla · Lupin · Divi's · Biocon · Aurobindo</div>
            <div class="phase-queries">USFDA approvals · Biosimilars · API · CDMO · R&D spend</div>
        </div>
        """, unsafe_allow_html=True)

        section("⚙️", "Research Capabilities")
        caps = ["Multi-step adaptive research", "Live Tavily web search", "yFinance stock data",
                "ChromaDB RAG on annual reports", "Programmatic financial calculations",
                "Institutional-grade reports"]
        for c in caps:
            st.markdown(f'<div style="font-size:0.78rem;color:#94a3b8;padding:0.2rem 0">✦ {c}</div>',
                        unsafe_allow_html=True)


# ── PHASE 2: RESEARCH PLAN ────────────────────────────────────────────────────
def phase_plan():
    hero()

    # Routing result banner
    sector_icons = {"it": "🖥", "pharma": "💊", "both": "🔀"}
    sector_labels = {"it": "IT Services", "pharma": "Pharmaceuticals", "both": "IT + Pharma"}
    icon = sector_icons.get(st.session_state.sector, "📊")
    label = sector_labels.get(st.session_state.sector, st.session_state.sector.upper())
    conf = int((st.session_state.confidence or 0) * 100)

    st.markdown(f"""
    <div class="routing-box">
        <span style="font-size:2rem">{icon}</span>
        <div>
            <div class="routing-sector">{label}</div>
            <div class="routing-detail">
                Query type: <strong style="color:#e2e8f0">{st.session_state.query_type}</strong> &nbsp;·&nbsp;
                Confidence: <strong style="color:#10b981">{conf}%</strong>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Generate plan if not yet done
    if st.session_state.plan is None:
        with st.spinner("🧠 Generating research plan with LLaMA 3.3 70B..."):
            try:
                router = load_router()
                agents = router.get_agents_for_sector(st.session_state.sector)
                agent = agents[0]
                st.session_state.agent = agent
                plan = agent.create_research_plan(st.session_state.query)
                st.session_state.plan = plan
            except Exception as e:
                st.error(f"Plan generation failed: {e}")
                return

    plan = st.session_state.plan

    section("📋", "Research Plan")
    col_meta, col_phases = st.columns([1, 2], gap="large")

    with col_meta:
        st.markdown(f"""
        <div class="metric-card" style="text-align:left;margin-bottom:0.8rem">
            <div style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:1px">Title</div>
            <div style="font-size:0.9rem;color:#e2e8f0;margin-top:0.3rem;font-weight:600">{plan.research_title}</div>
        </div>
        """, unsafe_allow_html=True)

        metric_row([
            ("Est. Steps", plan.estimated_steps, "#00d4ff"),
            ("Phases", len(plan.research_phases), "#7c3aed"),
        ])
        st.markdown("<br>", unsafe_allow_html=True)

        section("❓", "Key Questions")
        for q in plan.key_questions_to_answer:
            st.markdown(f'<div style="font-size:0.78rem;color:#94a3b8;padding:0.25rem 0;border-bottom:1px solid #1e3a5f">▸ {q}</div>',
                        unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        section("📄", "Report Sections")
        for s in plan.expected_report_sections:
            st.markdown(f'<div style="font-size:0.78rem;color:#94a3b8;padding:0.2rem 0">· {s}</div>',
                        unsafe_allow_html=True)

    with col_phases:
        section("🗺", "Research Phases")
        colors = ["#00d4ff", "#7c3aed", "#f59e0b", "#10b981", "#ef4444",
                  "#06b6d4", "#8b5cf6", "#d97706", "#059669", "#dc2626"]
        for i, phase in enumerate(plan.research_phases):
            color = colors[i % len(colors)]
            queries_html = " · ".join(f'<code style="background:rgba(255,255,255,0.05);padding:1px 5px;border-radius:3px;font-size:0.7rem">{q[:50]}</code>'
                                       for q in phase.search_queries[:2])
            st.markdown(f"""
            <div class="phase-card" style="border-left-color:{color}">
                <div class="phase-title" style="color:{color}">Phase {phase.phase_number} · {phase.phase_name}</div>
                <div class="phase-obj">{phase.objective}</div>
                <div class="phase-queries">{queries_html}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_back, col_go = st.columns([1, 3])
    with col_back:
        if st.button("← Edit Query"):
            st.session_state.phase = "query"
            st.rerun()
    with col_go:
        if st.button(f"▶ Execute Research ({st.session_state.max_steps} steps)", type="primary", use_container_width=True):
            st.session_state.phase = "research"
            st.session_state.steps_log = []
            st.session_state.current_step = 0
            st.rerun()


# ── PHASE 3: LIVE RESEARCH ────────────────────────────────────────────────────
def phase_research():
    hero()
    section("⚙️", "Deep Research In Progress")

    query = st.session_state.query
    plan = st.session_state.plan
    max_steps = st.session_state.max_steps

    # Progress display containers
    progress_bar = st.progress(0)
    status_box = st.empty()
    steps_container = st.container()

    status_box.markdown("""
    <div class="status-running">
        <span style="font-size:1.2rem">⚙️</span>
        <span>Initialising research agents and loading sector knowledge...</span>
    </div>""", unsafe_allow_html=True)

    # --- Run research synchronously (Streamlit doesn't support true async) ---
    steps_log = []

    def progress_callback(step: int, step_query: str):
        """Called by research engine at each step."""
        st.session_state.current_step = step
        steps_log.append({"step": step, "query": step_query, "insight": "Searching..."})
        # Update UI
        pct = min(step / max_steps, 1.0)
        progress_bar.progress(pct)
        status_box.markdown(f"""
        <div class="status-running">
            <span style="font-size:1.2rem">🔍</span>
            <span>Step {step}/{max_steps} · <code style="background:rgba(0,212,255,0.1);padding:2px 6px;border-radius:4px;font-size:0.8rem">{step_query[:80]}</code></span>
        </div>""", unsafe_allow_html=True)

        # Render all steps so far
        with steps_container:
            for s in steps_log:
                st.markdown(f"""
                <div class="step-row">
                    <div class="step-num">{s['step']}</div>
                    <div class="step-content">
                        <div class="step-query">→ {s['query'][:100]}</div>
                        <div class="step-insight">{s.get('insight','')}</div>
                    </div>
                </div>""", unsafe_allow_html=True)

    try:
        router = load_router()
        if st.session_state.agent is None:
            agents = router.get_agents_for_sector(st.session_state.sector)
            st.session_state.agent = agents[0]

        agent = st.session_state.agent
        session = agent.run_research(
            query=query,
            plan=plan,
            max_steps=max_steps,
            progress_callback=progress_callback,
        )

        # Update step logs with actual insights
        for i, step in enumerate(session.steps):
            if i < len(steps_log):
                insight = "; ".join(step.key_insights[:2]) if step.key_insights else ""
                steps_log[i]["insight"] = insight[:120] + "…" if len(insight) > 120 else insight

        st.session_state.steps_log = steps_log
        st.session_state.session = session
        st.session_state.report = session.final_report
        st.session_state.report_path = session.report_path

        progress_bar.progress(1.0)
        status_box.markdown(f"""
        <div class="status-done">
            ✅ Research complete · <strong>{len(session.steps)} steps</strong> executed ·
            Report saved to <code style="background:rgba(16,185,129,0.1);padding:2px 6px;border-radius:4px">{session.report_path}</code>
        </div>""", unsafe_allow_html=True)

        time.sleep(1.2)
        st.session_state.phase = "report"

        # Save to history
        st.session_state.history.append({
            "query": query,
            "sector": st.session_state.sector,
            "steps": len(session.steps),
            "path": session.report_path,
            "time": datetime.now().strftime("%H:%M"),
        })
        st.rerun()

    except Exception as e:
        st.session_state.error = str(e)
        status_box.markdown(f"""
        <div class="status-error">
            ❌ Research failed: {e}<br>
            <span style="font-size:0.78rem">Check your API keys and internet connection.</span>
        </div>""", unsafe_allow_html=True)
        if st.button("← Go Back"):
            st.session_state.phase = "query"
            st.rerun()


# ── PHASE 4: REPORT DISPLAY ───────────────────────────────────────────────────
def phase_report():
    hero()

    session = st.session_state.session
    steps_log = st.session_state.steps_log

    # Top metrics
    metric_row([
        ("Research Steps", len(session.steps) if session else "—", "#00d4ff"),
        ("Sector",         (st.session_state.sector or "—").upper(), "#7c3aed"),
        ("Query Type",     (st.session_state.query_type or "—").replace("_", " ").title(), "#f59e0b"),
        ("Status",         "✅ Complete", "#10b981"),
    ])
    st.markdown("<br>", unsafe_allow_html=True)

    tab_report, tab_steps, tab_download = st.tabs(["📄 Report", "🔍 Research Trail", "⬇ Download"])

    # ── TAB 1: REPORT ─────────────────────────────────────────────────────────
    with tab_report:
        if st.session_state.report:
            st.markdown(f'<div class="report-container">', unsafe_allow_html=True)
            st.markdown(st.session_state.report)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.warning("No report content available.")

    # ── TAB 2: RESEARCH TRAIL ─────────────────────────────────────────────────
    with tab_steps:
        section("🔍", f"Research Trail — {len(steps_log)} Steps")

        if session:
            for step in session.steps:
                with st.expander(f"Step {step.step_number} · {step.query[:70]}…" if len(step.query) > 70 else f"Step {step.step_number} · {step.query}"):
                    if step.key_insights:
                        st.markdown("**Key Insights:**")
                        for insight in step.key_insights:
                            st.markdown(f"- {insight}")
                    if step.data_points:
                        st.markdown("**Data Points:**")
                        st.json(step.data_points)
                    comp = step.completeness_score
                    color = "#10b981" if comp > 0.7 else "#f59e0b" if comp > 0.4 else "#ef4444"
                    st.markdown(
                        f'<div style="font-size:0.75rem;color:{color};margin-top:0.5rem">'
                        f'Completeness: {comp:.0%}</div>',
                        unsafe_allow_html=True,
                    )
        else:
            for s in steps_log:
                st.markdown(f"""
                <div class="step-row">
                    <div class="step-num">{s['step']}</div>
                    <div class="step-content">
                        <div class="step-query">→ {s['query']}</div>
                        <div class="step-insight">{s.get('insight','')}</div>
                    </div>
                </div>""", unsafe_allow_html=True)

    # ── TAB 3: DOWNLOAD ───────────────────────────────────────────────────────
    with tab_download:
        section("⬇", "Download Options")

        col1, col2 = st.columns(2)
        with col1:
            if st.session_state.report:
                st.download_button(
                    label="⬇ Download Markdown Report",
                    data=st.session_state.report,
                    file_name=f"research_{st.session_state.sector}_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
        with col2:
            if st.session_state.report_path and Path(st.session_state.report_path).exists():
                with open(st.session_state.report_path, "r", encoding="utf-8") as f:
                    st.download_button(
                        label="⬇ Download Saved Report File",
                        data=f.read(),
                        file_name=Path(st.session_state.report_path).name,
                        mime="text/markdown",
                        use_container_width=True,
                    )

        if st.session_state.report_path:
            st.markdown(
                f'<div style="font-size:0.78rem;color:#64748b;margin-top:0.5rem">'
                f'📁 Saved to: <code>{st.session_state.report_path}</code></div>',
                unsafe_allow_html=True,
            )

    st.markdown("---")
    if st.button("🔍 New Research Query", type="primary"):
        st.session_state.phase = "query"
        st.session_state.plan = None
        st.session_state.steps_log = []
        st.session_state.report = None
        st.session_state.session = None
        st.session_state.agent = None
        st.rerun()


# ── ROUTER ────────────────────────────────────────────────────────────────────
def main():
    sidebar()
    phase = st.session_state.phase

    if phase == "query":
        phase_query()
    elif phase == "plan":
        phase_plan()
    elif phase == "research":
        phase_research()
    elif phase == "report":
        phase_report()


if __name__ == "__main__":
    main()