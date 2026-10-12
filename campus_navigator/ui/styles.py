"""Accessible CSS styling and design system for Accessible Campus Navigator.

Provides:
- Dark navy sidebar (#0a1128 / #101c3d).
- Neutral light main workspace (#f8fafc / #ffffff) with high-contrast elements.
- High-contrast buttons, badges, and accessible typography (Inter / System UI).
- WCAG AAA compliant color contrasts.
- Restrained accent colors (#1d4ed8 royal blue, #047857 emerald, #b45309 amber, #b91c1c crimson).
- Clear visual hierarchy with distinct cards and callouts.
- Responsive layout containers and clean status pills.
"""

NAVIGATOR_CUSTOM_CSS = """
<style>
/* Base Typography & Color System */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stMarkdown {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

/* Background Workspace */
.stApp {
    background-color: #f8fafc;
    color: #0f172a;
}

/* Dark Navy Sidebar */
[data-testid="stSidebar"] {
    background-color: #091224 !important;
    border-right: 1px solid #1e293b;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li {
    color: #e2e8f0 !important;
}

[data-testid="stSidebar"] h1, 
[data-testid="stSidebar"] h2, 
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4 {
    color: #60a5fa !important;
    font-weight: 700;
}

/* Sidebar Radio Navigation Items */
[data-testid="stSidebar"] .stRadio label {
    background-color: transparent;
    padding: 6px 10px;
    border-radius: 8px;
    transition: all 0.2s ease;
    cursor: pointer;
}

[data-testid="stSidebar"] .stRadio label:hover {
    background-color: #1e293b !important;
}

/* Header Banner Component */
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
    color: #475569;
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

/* High Contrast Buttons */
button[kind="primary"] {
    background-color: #1e3a8a !important;
    color: #ffffff !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    border: none !important;
    padding: 8px 20px !important;
    box-shadow: 0 2px 4px rgba(30, 58, 138, 0.2) !important;
}

button[kind="primary"]:hover {
    background-color: #172554 !important;
}

button[kind="secondary"] {
    background-color: #f1f5f9 !important;
    color: #0f172a !important;
    font-weight: 600 !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 8px !important;
}

button[kind="secondary"]:hover {
    background-color: #e2e8f0 !important;
}

/* Accessible metric cards */
div[data-testid="stMetric"] {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 14px 18px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}

div[data-testid="stMetricLabel"] {
    font-size: 13px !important;
    font-weight: 600 !important;
    color: #475569 !important;
}

div[data-testid="stMetricValue"] {
    font-size: 24px !important;
    font-weight: 800 !important;
    color: #0f172a !important;
}
</style>
"""
