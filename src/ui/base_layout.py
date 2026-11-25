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
        .stApp [data-testid="stMarkdownContainer"] *,
        .stApp [data-testid="stMetricValue"],
        .stApp [data-testid="stMetricLabel"] {{
            color: var(--sa-text);
        }}
        .stApp [data-testid="stDataFrame"],
        .stApp [data-testid="stDataFrame"] * {{
            color: var(--sa-text) !important;
        }}
        .stApp [data-baseweb="tab"] {{
            color: var(--sa-muted) !important;
        }}
        .stApp [data-baseweb="tab"][aria-selected="true"] {{
            color: var(--sa-primary) !important;
        }}
        .stApp [data-testid="stExpander"] {{
            background: var(--sa-surface) !important;
            border: 1px solid var(--sa-border) !important;
            border-radius: 12px;
        }}
        .stApp [data-testid="stExpander"] summary,
        .stApp [data-testid="stExpander"] summary * {{
            color: var(--sa-text) !important;
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
            border-radius: 14px;
            border-color: var(--sa-border);
            white-space: nowrap;
            overflow-wrap: normal;
            line-height: 1.2;
            min-height: 2.7rem;
            touch-action: manipulation;
            transition:
                box-shadow 140ms ease,
                border-color 140ms ease,
                background-color 140ms ease,
                filter 100ms ease;
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
        .stApp [data-testid="stButton"] button[kind="primary"] {{
            border-radius: 18px;
            box-shadow: 0 4px 14px rgba(0, 102, 204, 0.18);
        }}
        .stApp button:not(:disabled):hover {{
            border-color: var(--sa-primary);
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.12);
        }}
        .stApp [data-testid="stButton"] button[kind="primary"]:not(:disabled):hover {{
            filter: brightness(1.04);
            box-shadow: 0 6px 18px rgba(0, 102, 204, 0.24);
        }}
        .stApp button:not(:disabled):active {{
            filter: brightness(0.94);
            box-shadow: inset 0 1px 3px rgba(15, 23, 42, 0.2);
        }}
        .stApp [data-testid="stButton"] button[kind="primary"]:not(:disabled):active {{
            filter: brightness(0.94);
            box-shadow: inset 0 2px 5px rgba(0, 0, 0, 0.2);
        }}
        .stApp button:focus-visible {{
            outline: 3px solid var(--sa-primary);
            outline-offset: 2px;
        }}
        .stApp button:disabled {{
            cursor: not-allowed;
            opacity: 0.62;
        }}
        @media (prefers-reduced-motion: reduce) {{
            .stApp button {{
                transition: none;
            }}
            .stApp [data-testid="stCheckbox"]:has(input[aria-label="Dark mode"]) > label > div:nth-of-type(1),
            .stApp [data-testid="stCheckbox"]:has(input[aria-label="Dark mode"]) > label > div:nth-of-type(1) > div {{
                transition: none;
            }}
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
        .sa-brand {{
            display: flex;
            align-items: center;
            gap: 0.35rem;
            font-size: 1.5rem;
            font-weight: 750;
            white-space: nowrap;
        }}
        .sa-brand-icon {{ font-size: 1.85rem; line-height: 1; }}
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
        .sa-nav-button [data-testid="stButton"] button {{
            min-height: 3.25rem;
            height: 3.25rem;
            padding: 0.45rem 0.35rem;
            font-size: 0.88rem;
            border-radius: 16px;
        }}
        .stApp [data-testid="stCheckbox"]:has(input[aria-label="Dark mode"]) {{
            width: 100%;
        }}
        .stApp [data-testid="stCheckbox"]:has(input[aria-label="Dark mode"]) > label {{
            display: flex !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
            justify-content: flex-end !important;
            gap: 0.65rem;
            width: 100%;
            white-space: nowrap !important;
        }}
        .stApp [data-testid="stCheckbox"]:has(input[aria-label="Dark mode"]) [data-testid="stMarkdownContainer"] p {{
            white-space: nowrap !important;
            overflow: visible !important;
            text-overflow: clip !important;
            margin: 0;
        }}
        .stApp [data-testid="stCheckbox"]:has(input[aria-label="Dark mode"]) > label > div:nth-of-type(1) {{
            position: relative;
            display: block;
            flex: 0 0 3.25rem;
            width: 3.25rem;
            height: 1.8rem;
            border-radius: 999px;
            background: #dbe4f2;
            box-shadow: inset 0 1px 3px rgba(15, 23, 42, 0.16);
            transition: background-color 240ms ease, box-shadow 240ms ease;
        }}
        .stApp [data-testid="stCheckbox"]:has(input[aria-label="Dark mode"]) > label > div:nth-of-type(1) > div {{
            position: absolute;
            top: 0.15rem;
            left: 0.15rem;
            display: grid;
            width: 1.5rem;
            height: 1.5rem;
            place-items: center;
            border-radius: 50%;
            background: #ffffff;
            color: #d97706;
            box-shadow: 0 1px 4px rgba(15, 23, 42, 0.24);
            transition:
                transform 240ms cubic-bezier(0.2, 0.8, 0.2, 1),
                background-color 240ms ease,
                color 240ms ease;
        }}
        .stApp [data-testid="stCheckbox"]:has(input[aria-label="Dark mode"]) > label > div:nth-of-type(1) > div::before {{
            content: "☀";
            font-family: "Segoe UI Symbol", sans-serif;
            font-size: 0.95rem;
            line-height: 1;
        }}
        .stApp [data-testid="stCheckbox"]:has(input[aria-label="Dark mode"]:checked) > label > div:nth-of-type(1) {{
            background: #273852;
            box-shadow: inset 0 1px 4px rgba(0, 0, 0, 0.35);
        }}
        .stApp [data-testid="stCheckbox"]:has(input[aria-label="Dark mode"]:checked) > label > div:nth-of-type(1) > div {{
            transform: translateX(1.45rem);
            background: #182437;
            color: #fbbf24;
        }}
        .stApp [data-testid="stCheckbox"]:has(input[aria-label="Dark mode"]:checked) > label > div:nth-of-type(1) > div::before {{
            content: "☾";
        }}
        .stApp [data-testid="stCheckbox"]:has(input[aria-label="Dark mode"]:focus-visible) > label > div:nth-of-type(1) {{
            outline: 3px solid var(--sa-primary);
            outline-offset: 3px;
        }}
        @media (max-width: 800px) {{
            .sa-nav-button [data-testid="stButton"] button {{
                white-space: normal;
                font-size: 0.78rem;
                line-height: 1.05;
            }}
        }}
        @media (max-width: 800px) {{
            [data-testid="stMainBlockContainer"] {{ padding-left: 1rem; padding-right: 1rem; }}
            .sa-brand {{ font-size: 1.25rem; }}
            .sa-brand-icon {{ font-size: 1.55rem; }}
            .sa-nav-button [data-testid="stButton"] button {{
                min-height: 2.8rem;
                height: auto;
            }}
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

    header_columns = st.columns([5, 1.5], vertical_alignment="center")
    with header_columns[0]:
        st.markdown(
            '<div class="sa-brand"><span class="sa-brand-icon" aria-hidden="true">'
            '🎓</span><span>ClassLens.ai</span></div>',
            unsafe_allow_html=True,
        )
        st.caption("Academic attendance")

    with header_columns[1]:
        st.toggle(
            "Dark mode",
            key="theme_switch",
            on_change=_update_theme,
            help="Switch between light and dark appearance.",
        )

    routes = (
        ("Home & Portal Gateway", "home"),
        ("Student Portal", "student"),
        ("Teacher Portal", "teacher"),
        ("Attendance Records", "records"),
        ("Mentor Portal", "mentor"),
    )
    navigation_columns = st.columns(5, gap="small", vertical_alignment="center")
    for column, (label, destination) in zip(navigation_columns, routes):
        with column:
            st.markdown('<div class="sa-nav-button">', unsafe_allow_html=True)
            if st.button(
                label,
                key=f"top_nav_{destination}",
                type="primary" if page == destination else "secondary",
                width="stretch",
            ):
                from src.ui.navigation import navigate_to

                navigate_to(destination)
            st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
