import streamlit as st


def apply_style():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        :root {
            --rina-dark-blue: #13294B;
            --rina-blue: #0076A5;
            --background: #F4F6FA;
            --surface: #FFFFFF;
            --surface-soft: #F8FAFC;
            --border: #E5EBF3;
            --border-strong: #D1DAE6;
            --muted: #6B7280;
            --text: var(--rina-dark-blue);
            --accent: var(--rina-blue);
            --accent-soft: #E6F2F8;
            --sidebar: #FAFCFE;
            --shadow-sm: 0 1px 2px rgba(19, 41, 75, 0.04);
            --shadow-md: 0 4px 12px rgba(19, 41, 75, 0.06);
            --radius-sm: 8px;
            --radius-md: 12px;
        }

        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }

        .stApp { background: var(--background); color: var(--text); }

        .dashboard-view {
            display: none;
        }

        [data-testid="stSidebar"] {
            background: var(--sidebar);
            border-right: 1px solid var(--border);
        }

        [data-testid="stSidebar"] * { color: var(--text) !important; }

        [data-testid="stSidebar"] h3 {
            color: var(--rina-dark-blue) !important;
            font-size: 0.78rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-top: 1.4rem;
            margin-bottom: 0.5rem;
            padding-bottom: 0.4rem;
            border-bottom: 1px solid var(--border);
        }

        [data-testid="stSidebar"] input,
        [data-testid="stSidebar"] textarea,
        [data-testid="stSidebar"] [data-baseweb="select"] > div,
        [data-testid="stSidebar"] [data-baseweb="input"] > div,
        [data-testid="stSidebar"] [data-baseweb="popover"] {
            background-color: #ffffff !important;
            border-color: var(--border) !important;
            border-radius: var(--radius-sm) !important;
        }

        [data-testid="stSidebar"] [data-baseweb="tag"] {
            background-color: var(--accent-soft) !important;
            color: var(--rina-blue) !important;
            border: 1px solid rgba(0, 118, 165, 0.2) !important;
        }

        [data-testid="stSidebar"] svg { fill: var(--text) !important; }

        [data-testid="stSidebar"] button[kind="primary"] {
            background: var(--rina-blue) !important;
            border: 1px solid var(--rina-blue) !important;
            color: #ffffff !important;
            font-weight: 600 !important;
            border-radius: var(--radius-sm) !important;
            transition: all 0.2s ease !important;
            padding: 0.6rem 1rem !important;
        }

        [data-testid="stSidebar"] button[kind="primary"]:hover {
            background: var(--rina-dark-blue) !important;
            border-color: var(--rina-dark-blue) !important;
            transform: translateY(-1px);
            box-shadow: var(--shadow-md);
        }

        [data-testid="stSidebar"] button[kind="primary"] * { color: #ffffff !important; }

        .sidebar-logo {
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 0.35rem;
        }

        .sidebar-logo img {
            max-height: 200px;
            width: auto;
            object-fit: contain;
        }

        .sidebar-logo-fallback {
            color: #ffffff !important;
            font-weight: 800;
            font-size: 1.05rem;
            letter-spacing: 0.18em;
        }

        .block-container {
            padding-top: 3rem;
            padding-bottom: 3rem;
            max-width: 1400px;
            margin: 0 auto;
        }

        h1, h2, h3 {
            letter-spacing: -0.01em;
            color: var(--rina-dark-blue);
        }

        .page-header {
            display: flex;
            align-items: flex-start;
            gap: 1rem;
            margin: 0.2rem 0 1.4rem 0;
        }

        .page-header-content { flex: 1; min-width: 0; }

        .page-header-title {
            font-size: 2rem;
            font-weight: 750;
            color: var(--rina-dark-blue);
            margin: 0 0 0.25rem 0;
            line-height: 1.1;
            letter-spacing: -0.02em;
        }

        .page-header-subtitle {
            color: var(--muted);
            font-size: 0.95rem;
            margin: 0 0 0.2rem 0;
        }

        .page-header-meta {
            color: #94A3B8;
            font-size: 0.82rem;
            margin: 0;
        }

        .metric-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-sm);
            padding: 1.05rem 1.15rem 1rem;
            min-height: 140px;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        }

        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
            border-color: var(--border-strong);
        }

        .metric-header {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin-bottom: 0.55rem;
        }

        .metric-label {
            color: var(--muted);
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 600;
            line-height: 1.3;
            flex: 1;
        }

        .metric-info {
            width: 18px;
            height: 18px;
            border-radius: 999px;
            border: 1px solid var(--border-strong);
            color: var(--muted);
            background: var(--surface-soft);
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 0.72rem;
            font-weight: 800;
            line-height: 1;
            cursor: help;
            flex-shrink: 0;
        }

        .metric-icon {
            width: 36px;
            height: 36px;
            border-radius: 9px;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }

        .metric-symbol {
            font-size: 1.05rem;
            font-weight: 800;
            line-height: 1;
        }

        .metric-card.c-blue   .metric-icon { background: rgba(30, 136, 229, 0.12);  color: #1E88E5; }
        .metric-card.c-orange .metric-icon { background: rgba(234, 88, 12, 0.12);   color: #EA580C; }
        .metric-card.c-purple .metric-icon { background: rgba(124, 58, 237, 0.12);  color: #7C3AED; }
        .metric-card.c-green  .metric-icon { background: rgba(5, 150, 105, 0.12);   color: #059669; }
        .metric-card.c-teal   .metric-icon { background: rgba(13, 148, 136, 0.12);  color: #0D9488; }
        .metric-card.c-sky    .metric-icon { background: rgba(2, 132, 199, 0.12);   color: #0284C7; }

        .metric-value {
            font-size: 1.95rem;
            line-height: 1.05;
            font-weight: 700;
            color: var(--rina-dark-blue);
            letter-spacing: -0.025em;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(.chart-title) {
            background: #ffffff !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-md) !important;
            box-shadow: var(--shadow-sm);
            transition: box-shadow 0.2s ease;
            padding: 1.1rem 1.2rem 0.9rem !important;
            min-height: 430px;
            overflow: hidden;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(.chart-title) > div,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.chart-title) [data-testid="stVerticalBlock"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.chart-title) [data-testid="stElementContainer"] {
            background: #ffffff !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:has(.chart-title):hover {
            box-shadow: var(--shadow-md);
        }

        .stVerticalBlock.st-emotion-cache-kv5w0i.e1rw0b1u3 {
            background: #ffffff !important;

        }

        .chart-title {
            font-size: 1.05rem;
            font-weight: 700;
            color: var(--rina-dark-blue);
            margin: 0 0 0.2rem 0;
            letter-spacing: -0.01em;
        }

        .chart-caption {
            color: var(--muted);
            font-size: 0.84rem;
            margin: 0 0 0.6rem 0;
        }

        [data-testid="stVegaLiteChart"], .stAltairChart {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
        }

        .section-title {
            font-size: 1.1rem;
            font-weight: 700;
            margin: 0.6rem 0 0.2rem 0;
            color: var(--rina-dark-blue);
            letter-spacing: -0.01em;
        }

        .section-caption {
            color: var(--muted);
            font-size: 0.86rem;
            margin: 0 0 0.6rem 0;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            overflow: hidden;
            box-shadow: var(--shadow-sm);
        }

        .stApp:has(.dashboard-view) [data-testid="stDownloadButton"] {
            display: flex;
            justify-content: flex-end;
            margin: -0.2rem 0 0.45rem;
        }

        .stApp:has(.dashboard-view) [data-testid="stDownloadButton"] button {
            background: transparent !important;
            border: 1px solid var(--border) !important;
            border-radius: var(--radius-sm) !important;
            color: var(--muted) !important;
            font-size: 0.78rem !important;
            font-weight: 600 !important;
            min-height: 2rem !important;
            padding: 0.25rem 0.65rem !important;
            box-shadow: none !important;
        }

        .stApp:has(.dashboard-view) [data-testid="stDownloadButton"] button:hover {
            background: var(--surface-soft) !important;
            border-color: var(--border-strong) !important;
            color: var(--rina-dark-blue) !important;
        }

        .stApp:has(.dashboard-view) [data-testid="stDownloadButton"] button * {
            color: inherit !important;
        }

        .stTabs [data-baseweb="tab-list"] { gap: 0.4rem; border-bottom: 1px solid var(--border); }

        .stTabs [data-baseweb="tab"] {
            background: transparent;
            border-radius: var(--radius-sm) var(--radius-sm) 0 0;
            color: var(--muted);
            padding: 0.5rem 0.95rem;
            font-weight: 500;
        }

        .stTabs [aria-selected="true"] {
            background: var(--accent-soft) !important;
            color: var(--rina-blue) !important;
            font-weight: 600;
        }

        hr, [data-testid="stDivider"] {
            border: none !important;
            border-top: 1px solid var(--border) !important;
            margin: 1.4rem 0 !important;
        }

        [data-testid="stAlert"] {
            border-radius: var(--radius-md);
            border: 1px solid var(--border);
        }

        .login-view {
            display: none;
        }

        .stApp:has(.login-view) {
            background: #12294b !important;
        }

        .stApp:has(.login-view) [data-testid="stSidebar"],
        .stApp:has(.login-view) header,
        .stApp:has(.login-view) footer {
            display: none !important;
        }

        .stApp:has(.login-view) .block-container {
            min-height: 100vh;
            max-width: 980px;
            padding: 3.2rem 1.5rem 3rem;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .stApp:has(.login-view) div[data-testid="stForm"] {
            width: min(470px, calc(100vw - 2rem));
            margin: 0 auto !important;
            background: #ffffff !important;
            border: 0 !important;
            border-radius: 7px !important;
            box-shadow: 0 24px 70px rgba(0, 0, 0, 0.24) !important;
            padding: 0 2.85rem 1.65rem !important;
            overflow: hidden;
        }

        .login-help-panel {
            background: #ffd15c;
            margin: 0 -2.85rem 1.35rem;
            padding: 1.25rem 1.75rem 1.1rem;
            color: #051a34;
        }

        .login-help-title {
            color: #051a34;
            font-size: 0.86rem;
            font-weight: 650;
            margin: 0 0 0.16rem;
        }

        .login-help-copy {
            color: #051a34;
            font-size: 0.76rem;
            line-height: 1.35;
            margin: 0;
        }

        .login-card-header {
            text-align: center;
            margin-bottom: 1.25rem;
        }

        .login-logo {
            display: block;
            width: min(150px, 56%);
            height: auto;
            margin: 0 auto 1.35rem;
            object-fit: contain;
        }

        .login-logo-fallback {
            color: var(--rina-dark-blue);
            font-size: 1.5rem;
            font-weight: 800;
            letter-spacing: 0.16em;
            margin-bottom: 1.35rem;
        }

        .login-title {
            color: var(--rina-dark-blue);
            font-size: 1.55rem;
            font-weight: 800;
            line-height: 1.12;
            margin: 0;
            text-align: left;
        }

        .stApp:has(.login-view) div[data-testid="stForm"] label p {
            color: var(--rina-dark-blue) !important;
            font-size: 0.82rem !important;
            font-weight: 500 !important;
        }

        .stApp:has(.login-view) div[data-testid="stForm"] [data-baseweb="input"] > div {
            background-color: #f0f0f0 !important;
            border: 1px solid #f0f0f0 !important;
            border-radius: 5px !important;
            box-shadow: none !important;
            overflow: hidden !important;
        }

        .stApp:has(.login-view) div[data-testid="stForm"] [data-baseweb="input"] > div:focus-within {
            border-color: var(--rina-dark-blue) !important;
            box-shadow: 0 0 0 3px rgba(19, 41, 75, 0.12) !important;
        }

        .stApp:has(.login-view) div[data-testid="stForm"] [data-baseweb="input"] > div > div {
            background-color: #f0f0f0 !important;
        }

        .stApp:has(.login-view) div[data-testid="stForm"] input {
            background-color: #f0f0f0 !important;
            color: var(--rina-dark-blue) !important;
            font-size: 0.95rem !important;
            height: 100% !important;
        }

        .stApp:has(.login-view) div[data-testid="stForm"] input::placeholder {
            color: #9aa1ad !important;
            opacity: 1 !important;
        }

        .stApp:has(.login-view) div[data-testid="stForm"] button[kind="primary"] {
            background: var(--rina-dark-blue) !important;
            border: 1px solid var(--rina-dark-blue) !important;
            border-radius: 3px !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            min-height: 2.5rem;
            margin-top: 0.45rem;
        }

        .stApp:has(.login-view) div[data-testid="stForm"] button[kind="primary"]:hover {
            background: color-mix(in srgb, var(--rina-dark-blue) 88%, #000000) !important;
            border-color: color-mix(in srgb, var(--rina-dark-blue) 88%, #000000) !important;
        }

        .stApp:has(.login-view) div[data-testid="stForm"] button[kind="primary"] * {
            color: #ffffff !important;
        }

        @media print {
            [data-testid="stSidebar"], header, footer { display: none !important; }
            .block-container { padding: 0.6rem !important; }
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.chart-title) {
                box-shadow: none !important;
                page-break-inside: avoid;
            }
        }

        @media (max-width: 900px) {
            .block-container {
                padding: 1.2rem 1rem 2rem;
            }

            .page-header {
                flex-direction: column;
                align-items: flex-start;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
