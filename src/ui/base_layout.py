import streamlit as st


def style_base_layout():
    theme = st.session_state.get("theme", "light")
    if theme == "dark":
        background = "#0f131c"
        surface = "#181c24"
        raised_surface = "#1c222e"
        text = "#f1f5f9"
        muted = "#a9b5c7"
        border = "#2c3545"
        primary = "#5ba7ff"
        color_scheme = "dark"
    else:
        background = "#f8f9ff"
        surface = "#ffffff"
        raised_surface = "#f1f5ff"
        text = "#1e293b"
        muted = "#64748b"
        border = "#e2e8f0"
        primary = "#0066cc"
        color_scheme = "light"

    st.markdown(
        f"""
        <style>
        :root {{
            --sa-background: {background};
            --sa-surface: {surface};
            --sa-raised-surface: {raised_surface};
            --sa-text: {text};
            --sa-muted: {muted};
            --sa-border: {border};
            --sa-primary: {primary};
            color-scheme: {color_scheme};
        }}
        #MainMenu, footer {{ visibility: hidden; }}
        header[data-testid="stHeader"] {{ visibility: hidden; height: 0; }}
        [data-testid="stMainBlockContainer"] {{
            padding-top: 1rem;
            padding-bottom: 2rem;
            max-width: 1440px;
        }}
        .stApp {{
            background: var(--sa-background) !important;
            color: var(--sa-text) !important;
        }}
        .stApp, .stApp [data-testid="stMarkdownContainer"] {{
            color: var(--sa-text);
        }}
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p,
        .stApp label, .stApp [data-testid="stCaptionContainer"] {{
            color: var(--sa-text);
        }}
        .stApp [data-testid="stCaptionContainer"] p,
        .stApp small {{ color: var(--sa-muted) !important; }}
        .stApp [data-testid="stVerticalBlockBorderWrapper"] {{
            background: var(--sa-surface) !important;
            border-color: var(--sa-border) !important;
            border-radius: 14px;
        }}
        .stApp [data-testid="stMetric"] {{
            background: var(--sa-surface);
            border: 1px solid var(--sa-border);
            border-radius: 12px;
            padding: 0.9rem 1rem;
        }}
        .stApp [data-testid="stMetricLabel"] *,
        .stApp [data-testid="stMetricDelta"] {{
            color: var(--sa-muted) !important;
        }}
        .stApp button {{
            border-radius: 10px;
            border-color: var(--sa-border);
            white-space: normal;
            overflow-wrap: anywhere;
            line-height: 1.15;
            min-height: 2.7rem;
            transition: transform 120ms ease, border-color 120ms ease;
        }}
        .stApp [data-testid="stButton"] button {{
            height: auto;
        }}
        .stApp .stMarkdownEllipsis {{
            overflow: visible !important;
            display: block !important;
            width: 100% !important;
            max-width: 100% !important;
            white-space: normal !important;
            text-overflow: clip !important;
        }}
        .stApp .stMarkdownEllipsis p {{
            overflow: visible !important;
            width: 100% !important;
            min-width: 0 !important;
            max-width: 100% !important;
            white-space: normal !important;
            overflow-wrap: anywhere !important;
            text-overflow: clip !important;
        }}
        .stApp button[kind="primary"] {{
            background: var(--sa-primary);
            border-color: var(--sa-primary);
            color: #ffffff;
        }}
        .stApp button[kind="primary"] p {{
            color: #ffffff !important;
        }}
        .stApp [data-testid="stButton"] button[kind="secondary"] {{
            background-color: var(--sa-surface) !important;
            background-image: none !important;
            border-color: var(--sa-border) !important;
            color: var(--sa-text) !important;
        }}
        .stApp [data-testid="stButton"] button[kind="secondary"] p {{
            color: var(--sa-text) !important;
        }}
        .stApp button:not(:disabled):hover {{
            border-color: var(--sa-primary);
            transform: translateY(-1px);
        }}
        .stApp input, .stApp textarea,
        .stApp [data-baseweb="select"] > div,
        .stApp [data-testid="stFileUploaderDropzone"],
        .stApp [data-testid="stAudioInput"] {{
            background-color: var(--sa-surface) !important;
            border-color: var(--sa-border) !important;
            color: var(--sa-text) !important;
        }}
        .stApp [data-testid="stFileUploader"] section,
        .stApp [data-testid="stFileUploaderDropzone"] {{
            border-color: var(--sa-border) !important;
        }}
        .stApp [data-testid="stFileUploaderDropzone"] *,
        .stApp [data-testid="stFileUploader"] small,
        .stApp [data-testid="stFileUploader"] span {{
            color: var(--sa-text) !important;
        }}
        .stApp [data-testid="stFileUploader"] button {{
            background: var(--sa-raised-surface) !important;
            background-color: var(--sa-raised-surface) !important;
            color: var(--sa-text) !important;
            border: 1px solid var(--sa-border) !important;
        }}
        .stApp [data-testid="stFileUploader"] button * {{
            color: var(--sa-text) !important;
        }}
        .stApp [data-testid="stAlert"] {{
            background: var(--sa-raised-surface) !important;
            border-color: var(--sa-border) !important;
            color: var(--sa-text) !important;
        }}
        .stApp [data-testid="stAlert"] * {{
            color: var(--sa-text) !important;
            background-color: transparent !important;
            background-image: none !important;
        }}
        .stApp [data-testid="stSpinner"],
        .stApp [data-testid="stStatusWidget"],
        .stApp [role="status"] {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            color: var(--sa-text) !important;
        }}
        .stApp [data-testid="stException"] {{
            background: #fff7ed !important;
            color: #111827 !important;
            border: 2px solid #c2410c !important;
            border-radius: 0.75rem !important;
            padding: 1rem !important;
        }}
        .stApp [data-testid="stException"] * {{ color: #111827 !important; }}
        .sa-brand {{ font-size: 1.15rem; font-weight: 750; white-space: nowrap; }}
        .sa-kicker {{
            color: var(--sa-muted) !important;
            font-size: 0.78rem;
            letter-spacing: 0.04em;
        }}
        .sa-hero {{
            border: 1px solid var(--sa-border);
            border-radius: 18px;
            background: linear-gradient(120deg, var(--sa-surface), var(--sa-raised-surface));
            padding: clamp(1.2rem, 3vw, 2rem);
            margin: 0.5rem 0 1.2rem;
        }}
        .sa-badge {{
            display: inline-block;
            border: 1px solid var(--sa-border);
            border-radius: 999px;
            background: var(--sa-raised-surface);
            color: var(--sa-text);
            padding: 0.2rem 0.65rem;
            font-size: 0.8rem;
            font-weight: 650;
        }}
        @media (max-width: 800px) {{
            [data-testid="stMainBlockContainer"] {{ padding-left: 1rem; padding-right: 1rem; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def style_background_home():
    style_base_layout()


def style_background_dashboard():
    style_base_layout()


def _update_theme():
    st.session_state["theme"] = (
        "dark" if st.session_state["theme_switch"] else "light"
    )


def render_top_navigation(page):
    st.session_state.setdefault("theme", "light")
    st.session_state.setdefault("theme_switch", st.session_state.theme == "dark")

    columns = st.columns([1.55, 1, 1, 1, 1, 0.9], vertical_alignment="center")
    with columns[0]:
        st.markdown('<div class="sa-brand">🎓 SmartAttend</div>', unsafe_allow_html=True)
        st.caption("Academic attendance")

    routes = (
        ("Home & Portal Gateway", "home"),
        ("Student Portal", "student"),
        ("Teacher Portal", "teacher"),
        ("Attendance Records", "records"),
    )
    for column, (label, destination) in zip(columns[1:5], routes):
        with column:
            if st.button(
                label,
                key=f"top_nav_{destination}",
                type="primary" if page == destination else "secondary",
                width="stretch",
            ):
                from src.ui.navigation import navigate_to

                navigate_to(destination)

    with columns[5]:
        st.toggle(
            "Dark",
            key="theme_switch",
            on_change=_update_theme,
            help="Switch between light and dark appearance.",
        )

    st.divider()
