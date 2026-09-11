"""
DC4X - Login Page UI Component
Provides a premium, responsive, theme-aware authentication view with single primary Sign In and secondary Register action.
"""
import streamlit as st
from config.settings import APP_BRAND, APP_DISPLAY_NAME, LOGO_DARK_PATH, LOGO_LIGHT_PATH, LOGO_PATH
import os

def render_login_page(is_dark: bool):
    """
    Renders the DC4X authentication UI with centered card layout,
    single primary Sign In form button, and secondary Register action beneath.
    """
    # -------------------------------------------------------------
    # 1. SCOPED STYLESHEET FOR LOGIN PAGE
    # -------------------------------------------------------------
    bg_page = "#09090D" if is_dark else "#F8FAFC"
    bg_card = "#12121C" if is_dark else "#FFFFFF"
    border_card = "rgba(255, 255, 255, 0.08)" if is_dark else "#E2E8F0"
    shadow_card = (
        "0 24px 60px rgba(0, 0, 0, 0.7), 0 0 35px rgba(0, 168, 255, 0.12)"
        if is_dark
        else "0 20px 45px rgba(15, 23, 42, 0.08), 0 4px 12px rgba(2, 132, 199, 0.06)"
    )
    
    text_primary = "#F4EAD3" if is_dark else "#0F172A"
    text_secondary = "#94A3B8" if is_dark else "#64748B"
    accent_cyan = "#00A8FF" if is_dark else "#0284C7"
    accent_cyan_hover = "#33B8FF" if is_dark else "#0369A1"
    
    input_bg = "#181826" if is_dark else "#F1F5F9"
    input_border = "#2A2A3D" if is_dark else "#CBD5E1"
    input_text = "#F4EAD3" if is_dark else "#0F172A"

    sec_btn_bg = "#181826" if is_dark else "#FFFFFF"
    sec_btn_border = "#2E2E42" if is_dark else "#CBD5E1"
    sec_btn_text = "#D6D3E6" if is_dark else "#334155"
    sec_btn_hover_bg = "#222234" if is_dark else "#F8FAFC"

    divider_color = "rgba(255, 255, 255, 0.12)" if is_dark else "#E2E8F0"
    divider_text = "#64748B" if is_dark else "#94A3B8"

    login_css = f"""
    <style>
        /* Force page background override for login */
        .stApp {{
            background-color: {bg_page} !important;
        }}

        /* Hide sidebar on login screen */
        section[data-testid="stSidebar"] {{
            display: none !important;
        }}

        /* Outer centering layout */
        .dc4x-login-outer {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 10px 10px 20px 10px;
            margin: 0 auto;
            width: 100%;
        }}

        /* Card Container */
        .dc4x-login-card {{
            background: {bg_card};
            border: 1px solid {border_card};
            border-radius: 24px;
            padding: 38px 36px 34px 36px;
            width: 100%;
            max-width: 440px;
            box-shadow: {shadow_card};
            transition: all 0.3s ease;
            position: relative;
        }}

        /* Brand Typography Header */
        .dc4x-brand-header {{
            text-align: center;
            margin-bottom: 20px;
        }}

        .dc4x-logo-title {{
            font-family: 'Plus Jakarta Sans', 'Outfit', -apple-system, sans-serif;
            font-size: 2.8rem;
            font-weight: 900;
            letter-spacing: -0.02em;
            line-height: 1.1;
            color: {text_primary};
            margin: 0;
        }}

        .dc4x-logo-title span {{
            color: {accent_cyan};
            text-shadow: {"0 0 20px rgba(0, 168, 255, 0.6)" if is_dark else "none"};
        }}

        .dc4x-logo-tagline {{
            font-family: 'Inter', sans-serif;
            font-size: 0.88rem;
            font-weight: 600;
            color: {text_secondary};
            letter-spacing: 0.05em;
            margin-top: 4px;
            text-transform: uppercase;
        }}

        /* Welcome text */
        .dc4x-welcome-title {{
            font-family: 'Inter', sans-serif;
            font-size: 1.35rem;
            font-weight: 700;
            color: {text_primary};
            margin-top: 6px;
            margin-bottom: 4px;
            text-align: center;
        }}

        .dc4x-welcome-sub {{
            font-size: 0.88rem;
            color: {text_secondary};
            text-align: center;
            margin-bottom: 22px;
        }}

        /* Streamlit Input Styling Overrides inside Form */
        div[data-testid="stForm"] {{
            border: none !important;
            padding: 0 !important;
            background: transparent !important;
        }}

        div[data-testid="stForm"] input {{
            background-color: {input_bg} !important;
            color: {input_text} !important;
            border: 1px solid {input_border} !important;
            border-radius: 12px !important;
            padding: 12px 14px !important;
            font-size: 0.95rem !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }}

        div[data-testid="stForm"] input:focus {{
            border-color: {accent_cyan} !important;
            box-shadow: 0 0 0 3px {"rgba(0, 168, 255, 0.25)" if is_dark else "rgba(2, 132, 199, 0.2)"} !important;
            outline: none !important;
        }}

        div[data-testid="stForm"] label p {{
            color: {text_primary} !important;
            font-weight: 600 !important;
            font-size: 0.88rem !important;
            margin-bottom: 4px !important;
        }}

        /* Primary Form Submit Button */
        div[data-testid="stForm"] button[type="submit"] {{
            background-color: {accent_cyan} !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 13px 20px !important;
            font-size: 1.02rem !important;
            font-weight: 700 !important;
            letter-spacing: 0.02em !important;
            box-shadow: {"0 4px 18px rgba(0, 168, 255, 0.35)" if is_dark else "0 4px 14px rgba(2, 132, 199, 0.25)"} !important;
            transition: all 0.2s ease !important;
            margin-top: 8px !important;
            margin-bottom: 4px !important;
            cursor: pointer !important;
        }}

        div[data-testid="stForm"] button[type="submit"]:hover {{
            background-color: {accent_cyan_hover} !important;
            transform: translateY(-1px) !important;
            box-shadow: {"0 6px 22px rgba(0, 168, 255, 0.45)" if is_dark else "0 6px 18px rgba(2, 132, 199, 0.35)"} !important;
        }}

        div[data-testid="stForm"] button[type="submit"]:active {{
            transform: translateY(1px) !important;
        }}

        /* Secondary Action Button (Register / Back) */
        .dc4x-secondary-action button {{
            background-color: {sec_btn_bg} !important;
            color: {sec_btn_text} !important;
            border: 1px solid {sec_btn_border} !important;
            border-radius: 12px !important;
            padding: 10px 18px !important;
            font-size: 0.92rem !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
            cursor: pointer !important;
            margin-top: 4px !important;
        }}

        .dc4x-secondary-action button:hover {{
            background-color: {sec_btn_hover_bg} !important;
            border-color: {accent_cyan} !important;
            color: {accent_cyan} !important;
            box-shadow: {"0 2px 10px rgba(0, 168, 255, 0.15)" if is_dark else "0 2px 8px rgba(2, 132, 199, 0.1)"} !important;
        }}

        /* Visual Divider between Primary and Secondary actions */
        .dc4x-auth-divider {{
            display: flex;
            align-items: center;
            text-align: center;
            margin: 16px 0 12px 0;
            color: {divider_text};
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 600;
        }}

        .dc4x-auth-divider::before,
        .dc4x-auth-divider::after {{
            content: '';
            flex: 1;
            border-bottom: 1px solid {divider_color};
        }}

        .dc4x-auth-divider span {{
            padding: 0 12px;
        }}
    </style>
    """
    st.markdown(login_css, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # 2. LOGIN PAGE CONTAINER
    # -------------------------------------------------------------
    # Session state for auth mode (signin vs register)
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "signin"

    is_signin = (st.session_state.auth_mode == "signin")

    # Outer Layout Columns for exact centering
    col_l, col_center, col_r = st.columns([1, 2.2, 1])

    with col_center:
        # Top Bar: Theme Switcher
        t_col1, t_col2 = st.columns([3, 1])
        with t_col2:
            current_theme_label = "☀️ Light" if is_dark else "🌙 Dark"
            next_theme = "Clean Light" if is_dark else "Dark Neon"
            if st.button(current_theme_label, key="btn_login_theme_toggle", help="Toggle Visual Theme"):
                st.session_state.theme_mode = next_theme
                st.rerun()

        # Render Header & Card Shell
        st.markdown(f"""
        <div class="dc4x-login-outer">
            <div class="dc4x-login-card">
                <div class="dc4x-brand-header">
                    <div class="dc4x-logo-title">DC<span>4</span>X</div>
                    <div class="dc4x-logo-tagline">{APP_DISPLAY_NAME}</div>
                </div>
        """, unsafe_allow_html=True)

        if is_signin:
            # ---------------------------------------------------------
            # SIGN IN VIEW: Single primary Sign In button + Secondary Register
            # ---------------------------------------------------------
            st.markdown("""
            <div class="dc4x-welcome-title">Welcome back</div>
            <div class="dc4x-welcome-sub">Sign in to continue to your workspace.</div>
            """, unsafe_allow_html=True)

            # Primary Sign In Form
            with st.form("login_form"):
                user_input = st.text_input(
                    "Username / Email",
                    value=st.session_state.get("login_user_input", "analyst@dc4x.io"),
                    placeholder="name@workspace.com",
                    key="login_user"
                )
                pass_input = st.text_input(
                    "Password",
                    type="password",
                    value=st.session_state.get("login_pass_input", "demo123"),
                    placeholder="••••••••",
                    key="login_pass"
                )

                submitted = st.form_submit_button("Sign In →", use_container_width=True)

                if submitted:
                    if user_input and user_input.strip():
                        st.session_state.authenticated = True
                        st.session_state.username = user_input.strip()
                        st.session_state.login_user_input = user_input.strip()
                        st.session_state.login_pass_input = pass_input
                        st.rerun()
                    else:
                        st.error("Authentication failed: Please enter a valid username or email.")

            # Subtle separator
            st.markdown("""
            <div class="dc4x-auth-divider"><span>or</span></div>
            """, unsafe_allow_html=True)

            # Secondary Action: Register button below Sign In
            st.markdown('<div class="dc4x-secondary-action">', unsafe_allow_html=True)
            if st.button("Register / Request Access", key="btn_switch_to_register", use_container_width=True):
                st.session_state.auth_mode = "register"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        else:
            # ---------------------------------------------------------
            # REGISTER VIEW: Information + Return to Sign In
            # ---------------------------------------------------------
            st.markdown("""
            <div class="dc4x-welcome-title">Workspace Registration</div>
            <div class="dc4x-welcome-sub">Self-service registration & account provisioning</div>
            """, unsafe_allow_html=True)

            st.info("🔐 Account creation for DC4X is restricted to authorized analysts. Please contact your workspace administrator to request access credentials.")

            st.markdown("""
            <div class="dc4x-auth-divider"><span>already have an account?</span></div>
            """, unsafe_allow_html=True)

            st.markdown('<div class="dc4x-secondary-action">', unsafe_allow_html=True)
            if st.button("← Back to Sign In", key="btn_back_to_signin", use_container_width=True):
                st.session_state.auth_mode = "signin"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # Close Login Card DIV
        st.markdown("""
            </div>
        </div>
        """, unsafe_allow_html=True)
