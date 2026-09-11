import time
import streamlit as st


def show():
    """Display an animated splash screen for ~3 seconds.

    Renders DC4X branding with pure CSS/HTML typography and animations.
    No static image assets are used for the main logo.
    """
    splash_html = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700;900&family=Outfit:wght@800;900&family=Playfair+Display:ital,wght@0,700;0,900;1,700&family=Plus+Jakarta+Sans:wght@700;800&display=swap');

    /* Hide Streamlit chrome during splash */
    #MainMenu {visibility: hidden; display: none !important;}
    header {visibility: hidden; display: none !important;}
    footer {visibility: hidden; display: none !important;}
    .stDeployButton {display: none !important;}
    div[data-testid="stToolbar"] {visibility: hidden; display: none !important;}
    div[data-testid="stDecoration"] {visibility: hidden; display: none !important;}
    div[data-testid="stStatusWidget"] {visibility: hidden; display: none !important;}

    .stApp {
        background-color: #000000 !important;
        background: #000000 !important;
        overflow: hidden !important;
    }

    .block-container {
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100% !important;
    }

    /* Fullscreen Splash Container */
    .dc4x-splash-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        height: 100vh;
        width: 100vw;
        background-color: #000000;
        position: fixed;
        top: 0;
        left: 0;
        z-index: 999999;
        overflow: hidden;
        user-select: none;
    }

    /* Subtle ambient background glow */
    .dc4x-ambient-glow {
        position: absolute;
        width: 450px;
        height: 450px;
        background: radial-gradient(circle, rgba(0, 168, 255, 0.18) 0%, rgba(0, 168, 255, 0.05) 45%, rgba(0, 0, 0, 0) 70%);
        border-radius: 50%;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -55%);
        pointer-events: none;
        animation: dc4xPulseGlow 3s ease-in-out infinite alternate;
    }

    /* Primary Brand Logo Text Container */
    .dc4x-logo-wrapper {
        display: inline-flex;
        align-items: baseline;
        justify-content: center;
        position: relative;
        font-size: clamp(4.5rem, 12vw, 8.5rem);
        line-height: 1;
        letter-spacing: 0.02em;
        animation: dc4xLogoScaleFade 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        transform-origin: center center;
    }

    /* DC Letters */
    .dc4x-logo-dc {
        font-family: 'Plus Jakarta Sans', 'Outfit', sans-serif;
        font-weight: 800;
        color: #F4EAD3;
        letter-spacing: -0.01em;
        text-shadow: 0 4px 20px rgba(244, 234, 211, 0.15);
    }

    /* 4 - Vibrant Electric Cyan */
    .dc4x-logo-4 {
        font-family: 'Plus Jakarta Sans', 'Outfit', sans-serif;
        font-weight: 900;
        color: #00A8FF;
        position: relative;
        text-shadow:
            0 0 20px rgba(0, 168, 255, 0.8),
            0 0 40px rgba(0, 168, 255, 0.5),
            0 0 80px rgba(0, 168, 255, 0.3);
        margin: 0 0.02em;
        animation: dc4xElectricPulse 2.5s ease-in-out infinite alternate;
    }

    /* X Letter */
    .dc4x-logo-x {
        font-family: 'Playfair Display', 'Cinzel Decorative', serif;
        font-weight: 900;
        color: #F4EAD3;
        font-style: normal;
        text-shadow: 0 4px 20px rgba(244, 234, 211, 0.15);
        margin-left: -0.02em;
    }

    /* Tagline / Subtitle */
    .dc4x-tagline-wrapper {
        margin-top: 2rem;
        opacity: 0;
        transform: translateY(24px);
        animation: dc4xSubtitleSlideUp 1s cubic-bezier(0.16, 1, 0.3, 1) 0.8s forwards;
    }

    .dc4x-tagline {
        font-family: 'Playfair Display', 'Cinzel Decorative', serif;
        font-weight: 700;
        font-size: clamp(1.4rem, 3.2vw, 2.6rem);
        color: #F4EAD3;
        letter-spacing: 0.04em;
        text-align: center;
        text-shadow: 0 2px 14px rgba(244, 234, 211, 0.2);
    }

    /* Sleek Loading Progress Bar */
    .dc4x-loading-bar-container {
        position: absolute;
        bottom: 40px;
        width: 180px;
        height: 3px;
        background: rgba(244, 234, 211, 0.12);
        border-radius: 4px;
        overflow: hidden;
        opacity: 0;
        animation: dc4xFadeInLoader 0.6s ease 0.6s forwards;
    }

    .dc4x-loading-bar-progress {
        height: 100%;
        width: 0%;
        background: linear-gradient(90deg, #00A8FF, #F4EAD3);
        border-radius: 4px;
        box-shadow: 0 0 10px #00A8FF;
        animation: dc4xFillLoader 2.4s cubic-bezier(0.4, 0, 0.2, 1) 0.6s forwards;
    }

    /* Keyframe Animations - all prefixed to avoid leaks */
    @keyframes dc4xLogoScaleFade {
        0% {
            opacity: 0;
            transform: scale(0.82) translateY(12px);
            filter: blur(8px);
        }
        100% {
            opacity: 1;
            transform: scale(1) translateY(0);
            filter: blur(0px);
        }
    }

    @keyframes dc4xSubtitleSlideUp {
        0% {
            opacity: 0;
            transform: translateY(24px);
            filter: blur(4px);
        }
        100% {
            opacity: 1;
            transform: translateY(0);
            filter: blur(0px);
        }
    }

    @keyframes dc4xPulseGlow {
        0% {
            transform: translate(-50%, -55%) scale(0.9);
            opacity: 0.6;
        }
        100% {
            transform: translate(-50%, -55%) scale(1.15);
            opacity: 1;
        }
    }

    @keyframes dc4xElectricPulse {
        0% {
            text-shadow:
                0 0 15px rgba(0, 168, 255, 0.7),
                0 0 35px rgba(0, 168, 255, 0.4);
        }
        100% {
            text-shadow:
                0 0 25px rgba(0, 168, 255, 0.95),
                0 0 50px rgba(0, 168, 255, 0.6),
                0 0 90px rgba(0, 168, 255, 0.4);
        }
    }

    @keyframes dc4xFadeInLoader {
        to { opacity: 1; }
    }

    @keyframes dc4xFillLoader {
        0% { width: 0%; }
        100% { width: 100%; }
    }
    </style>

    <div class="dc4x-splash-container">
        <div class="dc4x-ambient-glow"></div>
        <div class="dc4x-logo-wrapper">
            <span class="dc4x-logo-dc">DC</span><span class="dc4x-logo-4">4</span><span class="dc4x-logo-x">X</span>
        </div>
        <div class="dc4x-tagline-wrapper">
            <div class="dc4x-tagline">Data Cleaning For You</div>
        </div>
        <div class="dc4x-loading-bar-container">
            <div class="dc4x-loading-bar-progress"></div>
        </div>
    </div>
    """
    st.markdown(splash_html, unsafe_allow_html=True)
    # Hold splash visible for ~3 seconds
    time.sleep(3.0)
