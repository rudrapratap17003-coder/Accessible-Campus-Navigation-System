"""Accessible CSS styling and design system for Accessible Campus Navigator.

Provides:
- Design system CSS variables (--app-background, --surface-background, --text-primary, etc.)
- Dark navy sidebar (#091224) with crisp, high-contrast text (#e2e8f0) and blue headings (#60a5fa).
- Light, neutral main workspace (#f8fafc) with slate text (#0f172a).
- Explicit high-contrast text styling for all inputs, selectboxes, dropdowns, expanders, alerts, metrics, tables, tabs, and buttons.
- Elimination of invisible/white-on-white and black-on-black text bugs.
- WCAG AAA compliant contrasts and responsive cards.
"""

NAVIGATOR_CUSTOM_CSS = """
<style>
/* =============================================================
   1. CSS VARIABLES & DESIGN SYSTEM TOKENS
   ============================================================= */
:root {
    --app-background: #f8fafc;
    --surface-background: #ffffff;
    --surface-elevated: #f1f5f9;
    --sidebar-background: #091224;
    --sidebar-border: #1e293b;
    --text-primary: #0f172a;
    --text-secondary: #334155;
    --text-muted: #64748b;
    --text-inverse: #f8fafc;
    --border-color: #cbd5e1;
    --primary-color: #1e3a8a;
    --primary-hover: #172554;
    --accent-blue: #2563eb;
    --success-color: #047857;
    --success-bg: #ecfdf5;
    --warning-color: #b45309;
    --warning-bg: #fffbeb;
    --error-color: #b91c1c;
    --error-bg: #fef2f2;
}

/* =============================================================
   2. TYPOGRAPHY & APP WORKSPACE
   ============================================================= */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stMarkdown {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

.stApp {
    background-color: var(--app-background) !important;
    color: var(--text-primary) !important;
}

/* Main workspace headings */
.stApp h1, .stApp h2, .stApp h3 {
    color: #0f172a !important;
    font-weight: 700;
}
.stApp h4, .stApp h5, .stApp h6 {
    color: #1e293b !important;
    font-weight: 600;
}

/* Paragraphs & Markdown text in main workspace */
.stApp .main [data-testid="stMarkdownContainer"] p,
.stApp .main [data-testid="stMarkdownContainer"] span,
.stApp .main [data-testid="stMarkdownContainer"] li {
    color: #0f172a;
}

/* =============================================================
   3. SIDEBAR NAVIGATION & CONTRAST
   ============================================================= */
[data-testid="stSidebar"] {
    background-color: var(--sidebar-background) !important;
    border-right: 1px solid var(--sidebar-border) !important;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] label,
[data-testid="stSidebar"] label {
    color: #e2e8f0 !important;
}

[data-testid="stSidebar"] h1, 
[data-testid="stSidebar"] h2, 
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4 {
    color: #60a5fa !important;
    font-weight: 700 !important;
}

/* Radio buttons in Sidebar */
[data-testid="stSidebar"] .stRadio label {
    background-color: transparent !important;
    padding: 6px 10px;
    border-radius: 8px;
    transition: all 0.2s ease;
    cursor: pointer;
    color: #f1f5f9 !important;
}

[data-testid="stSidebar"] .stRadio label:hover {
    background-color: #1e293b !important;
    color: #ffffff !important;
}

/* Selectbox inside sidebar */
[data-testid="stSidebar"] [data-baseweb="select"] {
    background-color: #111e38 !important;
    border: 1px solid #334155 !important;
    color: #ffffff !important;
    border-radius: 8px;
}
[data-testid="stSidebar"] [data-baseweb="select"] * {
    color: #ffffff !important;
}

/* =============================================================
   4. FORM CONTROLS: INPUTS, SELECTBOXES, TEXTAREAS & DROPDOWNS
   ============================================================= */
/* Labels for all form controls */
label[data-testid="stWidgetLabel"],
label[data-testid="stWidgetLabel"] p,
label[data-testid="stWidgetLabel"] span {
    font-size: 14px !important;
    font-weight: 600 !important;
    color: #0f172a !important;
}

/* Text Input & Number Input */
input[type="text"], input[type="number"], input[type="password"] {
    background-color: #ffffff !important;
    color: #0f172a !important;
    border: 1.5px solid #cbd5e1 !important;
    border-radius: 8px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
}

input[type="text"]:focus, input[type="number"]:focus, input[type="password"]:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2) !important;
}

/* Text Area */
textarea {
    background-color: #ffffff !important;
    color: #0f172a !important;
    border: 1.5px solid #cbd5e1 !important;
    border-radius: 8px !important;
    font-size: 14px !important;
}

/* BaseWeb Select Box (Dropdowns) */
div[data-baseweb="select"] {
    background-color: #ffffff !important;
    border: 1.5px solid #cbd5e1 !important;
    border-radius: 8px !important;
}

div[data-baseweb="select"] * {
    color: #0f172a !important;
    font-weight: 500 !important;
}

/* Dropdown popover list menu options */
ul[data-baseweb="menu"],
div[data-baseweb="popover"],
div[data-baseweb="popover"] ul {
    background-color: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1) !important;
}

li[data-baseweb="menu-item"] {
    color: #0f172a !important;
    background-color: #ffffff !important;
    padding: 8px 12px !important;
}

li[data-baseweb="menu-item"]:hover,
li[data-baseweb="menu-item"][aria-selected="true"] {
    background-color: #e2e8f0 !important;
    color: #0f172a !important;
}

/* MultiSelect Tags */
span[data-baseweb="tag"] {
    background-color: #e0e7ff !important;
    color: #1e3a8a !important;
    border: 1px solid #c7d2fe !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
}
span[data-baseweb="tag"] * {
    color: #1e3a8a !important;
}

/* =============================================================
   5. BUTTONS: PRIMARY & SECONDARY
   ============================================================= */
button[kind="primary"],
button[data-testid="baseButton-primary"] {
    background-color: #1e3a8a !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    border: none !important;
    padding: 8px 18px !important;
    box-shadow: 0 2px 4px rgba(30, 58, 138, 0.25) !important;
    transition: background-color 0.15s ease !important;
}

button[kind="primary"]:hover,
button[data-testid="baseButton-primary"]:hover {
    background-color: #172554 !important;
    color: #ffffff !important;
}

button[kind="secondary"],
button[data-testid="baseButton-secondary"] {
    background-color: #ffffff !important;
    color: #0f172a !important;
    font-weight: 600 !important;
    border: 1.5px solid #cbd5e1 !important;
    border-radius: 8px !important;
    padding: 8px 18px !important;
    transition: all 0.15s ease !important;
}

button[kind="secondary"]:hover,
button[data-testid="baseButton-secondary"]:hover {
    background-color: #f1f5f9 !important;
    border-color: #94a3b8 !important;
    color: #0f172a !important;
}

/* Button text color enforcement */
button p, button span {
    color: inherit !important;
}

/* =============================================================
   6. METRIC CARDS & EXPANDERS
   ============================================================= */
div[data-testid="stMetric"] {
    background-color: #ffffff !important;
    border: 1.5px solid #e2e8f0 !important;
    border-radius: 10px !important;
    padding: 14px 18px !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
}

div[data-testid="stMetricLabel"] {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #475569 !important;
}

div[data-testid="stMetricValue"] {
    font-size: 26px !important;
    font-weight: 800 !important;
    color: #0f172a !important;
}

/* Expanders */
div[data-testid="stExpander"] {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
    margin-bottom: 14px !important;
}

div[data-testid="stExpander"] details summary {
    font-weight: 600 !important;
    color: #0f172a !important;
}

div[data-testid="stExpander"] details summary p,
div[data-testid="stExpander"] details summary span {
    color: #0f172a !important;
    font-weight: 600 !important;
}

/* =============================================================
   7. TABS, TABLES & DATAFRAMES
   ============================================================= */
/* Tabs */
button[data-baseweb="tab"] {
    font-weight: 600 !important;
    color: #475569 !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #1e3a8a !important;
    border-bottom-color: #1e3a8a !important;
}

/* DataFrames and Tables */
div[data-testid="stDataFrame"] {
    background-color: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
}

/* =============================================================
   8. ALERTS & NOTIFICATIONS
   ============================================================= */
div[data-testid="stAlert"] {
    border-radius: 8px !important;
    font-size: 14px !important;
    line-height: 1.5 !important;
}

div[data-testid="stAlert"] p,
div[data-testid="stAlert"] span {
    color: inherit !important;
}

/* =============================================================
   9. HERO BANNER, CARDS, BADGES & STEPS
   ============================================================= */
.campus-hero-banner {
    background: linear-gradient(135deg, #091224 0%, #172554 60%, #1e3a8a 100%);
    color: #ffffff;
    padding: 28px 32px;
    border-radius: 14px;
    margin-bottom: 24px;
    box-shadow: 0 10px 15px -3px rgba(15, 23, 42, 0.15), 0 4px 6px -4px rgba(15, 23, 42, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.campus-hero-title {
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -0.025em;
    margin: 0 0 6px 0;
    color: #ffffff !important;
}

.campus-hero-subtitle {
    font-size: 16px;
    font-weight: 500;
    color: #93c5fd !important;
    margin: 0 0 10px 0;
}

.campus-hero-tagline {
    display: inline-block;
    font-size: 14px;
    font-weight: 600;
    color: #fef08a !important;
    background: rgba(254, 240, 138, 0.12);
    border: 1px solid rgba(254, 240, 138, 0.3);
    padding: 4px 14px;
    border-radius: 9999px;
    letter-spacing: 0.01em;
}

/* Integrity and Transparency Notices */
.integrity-notice {
    background-color: #fef2f2;
    border-left: 5px solid #dc2626;
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 22px;
    color: #991b1b;
    font-size: 14px;
    line-height: 1.55;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}

.demo-watermark {
    display: inline-block;
    background-color: #fee2e2;
    color: #991b1b;
    border: 1px solid #f87171;
    font-size: 12px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 6px;
    margin-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* Professional Cards */
.nav-card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px 22px;
    margin-bottom: 18px;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.nav-card:hover {
    border-color: #cbd5e1;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08);
}

.nav-card h4 {
    margin: 0 0 8px 0;
    color: #0f172a;
    font-weight: 700;
}

.nav-card p {
    color: #334155;
    font-size: 14px;
    line-height: 1.5;
    margin: 0;
}

/* Status Badges */
.badge-verified {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 9999px;
    font-size: 11px;
    font-weight: 700;
    background-color: #ecfdf5;
    color: #065f46;
    border: 1px solid #a7f3d0;
}

.badge-provisional {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 9999px;
    font-size: 11px;
    font-weight: 700;
    background-color: #fffbeb;
    color: #92400e;
    border: 1px solid #fde68a;
}

.badge-demonstration {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 9999px;
    font-size: 11px;
    font-weight: 700;
    background-color: #fef2f2;
    color: #991b1b;
    border: 1px solid #fecaca;
}

/* Step-by-Step Directions */
.route-step-card {
    border-left: 5px solid #2563eb;
    background-color: #ffffff;
    border-top: 1px solid #f1f5f9;
    border-right: 1px solid #f1f5f9;
    border-bottom: 1px solid #f1f5f9;
    border-radius: 0 10px 10px 0;
    padding: 14px 18px;
    margin: 10px 0;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}

.route-step-card.elevator {
    border-left-color: #d97706;
    background-color: #fffdf5;
}

.route-step-card.ramp {
    border-left-color: #059669;
    background-color: #f0fdf4;
}

.route-step-card.stairs {
    border-left-color: #dc2626;
    background-color: #fef2f2;
}
</style>
"""
