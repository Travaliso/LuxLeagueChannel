def inject_luxury_css():
    bg_style = """
        background-color: #060b26; 
        background-image: 
            repeating-linear-gradient(to bottom, transparent, transparent 4px, rgba(0, 0, 0, 0.2) 4px, rgba(0, 0, 0, 0.2) 8px),
            radial-gradient(circle at 0% 0%, rgba(58, 12, 163, 0.4) 0%, transparent 50%),
            radial-gradient(circle at 100% 100%, rgba(0, 201, 255, 0.2) 0%, transparent 50%);
        background-attachment: fixed; background-size: cover;
    """
    
    # Try to load local background if available
    for ext in ["jpg", "jpeg", "png", "webp"]:
        try:
            with open(f"background.{ext}", "rb") as f:
                bin_str = base64.b64encode(f.read()).decode()
                bg_style = f"""
                    background-image: url("data:image/{ext};base64,{bin_str}");
                    background-size: cover;
                    background-position: center;
                    background-repeat: no-repeat;
                    background-attachment: fixed;
                """
            break
        except FileNotFoundError: continue

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Lato:wght@400;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Lato', sans-serif; color: #E0E0E0; }}
    h1, h2, h3 {{ font-family: 'Playfair Display', serif; color: #D4AF37 !important; text-shadow: 0 2px 4px rgba(0,0,0,0.5); }}
    .stApp {{ {bg_style} }}
    
    /* --- SIDEBAR FIXES --- */
    /* Force background color on the sidebar container */
    section[data-testid="stSidebar"] {{
        background-color: #060b26 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }}
    
    /* Target the internal div that holds the sidebar content to remove top padding */
    section[data-testid="stSidebar"] > div:first-child {{
        padding-top: 0rem !important;
    }}
    
    /* Specifically target the top block spacing */
    div[data-testid="stSidebarUserContent"] {{
        padding-top: 1rem !important;
    }}

    /* --- NAVIGATION & MENU CONTROLS --- */
    footer {{ visibility: hidden; }}
    #MainMenu {{ visibility: hidden; }}
    .stAppDeployButton {{ display: none; }}
    div:has(> a[href*="streamlit.io"]) {{ visibility: hidden; display: none; }}
    [data-testid="stSidebarNav"] {{ display: block !important; visibility: visible !important; }}
    [data-testid="collapsedControl"] {{ display: block !important; visibility: visible !important; }}
    header[data-testid="stHeader"] {{ background: transparent; }}

    /* --- COMPONENTS --- */
    .luxury-card {{ background: rgba(17, 25, 40, 0.75); backdrop-filter: blur(16px); border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.08); padding: 20px; margin-bottom: 15px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3); }}
    .prop-badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; }}
    .badge-fire {{ background: rgba(255, 75, 75, 0.2); color: #FF4B4B; border: 1px solid #FF4B4B; }}
    .badge-gem {{ background: rgba(0, 201, 255, 0.2); color: #00C9FF; border: 1px solid #00C9FF; }}
    .badge-ok {{ background: rgba(146, 254, 157, 0.2); color: #92FE9D; border: 1px solid #92FE9D; }}
    .meta-badge {{ display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; margin-right: 4px; margin-bottom: 4px; border: 1px solid transparent; }}
    .matchup-good {{ color: #92FE9D; border-color: #92FE9D; background: rgba(146, 254, 157, 0.1); }}
    .matchup-bad {{ color: #FF4B4B; border-color: #FF4B4B; background: rgba(255, 75, 75, 0.1); }}
    .matchup-mid {{ color: #a0aaba; border-color: #a0aaba; background: rgba(160, 170, 186, 0.1); }}
    .weather-neutral {{ color: #a0aaba; border-color: #a0aaba; background: rgba(255,255,255,0.05); }}
    .weather-warn {{ color: #FF4B4B; border-color: #FF4B4B; background: rgba(255, 75, 75, 0.1); }}
    .insight-purple {{ background: rgba(114, 9, 183, 0.2); border-color: #7209b7; color: #f72585; }}
    .lab-cyan {{ background: rgba(76, 201, 240, 0.15); border-color: #4cc9f0; color: #4cc9f0; }}
    .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 5px; margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1); }}
    .stat-box {{ text-align: center; }}
    .stat-val {{ font-size: 1.1rem; font-weight: 700; color: white; }}
    .stat-label {{ font-size: 0.65rem; color: #a0aaba; text-transform: uppercase; }}
    .edge-box {{ margin-top: 10px; background: rgba(0,0,0,0.3); padding: 8px; border-radius: 8px; text-align: center; font-size: 0.8rem; }}
    .tooltip {{ position: relative; display: inline-block; cursor: pointer; margin-left: 4px; vertical-align: middle; }}
    .tooltip .tooltiptext {{ visibility: hidden; width: 240px; background-color: #1E1E1E; color: #fff; text-align: left; border-radius: 6px; padding: 10px; position: absolute; z-index: 100; bottom: 140%; left: 50%; margin-left: -120px; opacity: 0; transition: opacity 0.3s; border: 1px solid #D4AF37; font-size: 0.7rem; line-height: 1.4; box-shadow: 0 4px 15px rgba(0,0,0,0.6); }}
    .tooltip:hover .tooltiptext {{ visibility: visible; opacity: 1; }}
    .award-card {{ border-left: 4px solid #00C9FF; min-height: 380px; display: flex; flex-direction: column; align-items: center; text-align: center; }}
    .shame-card {{ background: rgba(40, 10, 10, 0.8); border-left: 4px solid #FF4B4B; min-height: 250px; text-align: center; }}
    .studio-box {{ border-left: 4px solid #7209b7; }}
    .podium-step {{ border-radius: 10px 10px 0 0; text-align: center; padding: 10px; display: flex; flex-direction: column; justify-content: flex-end; backdrop-filter: blur(10px); box-shadow: 0 4px 20px rgba(0,0,0,0.4); }}
    .rank-num {{ font-size: 3rem; font-weight: 900; opacity: 0.2; margin-bottom: -20px; }}
    @keyframes shine {{ to {{ background-position: 200% center; }} }}
    .luxury-loader-text {{ font-family: 'Helvetica Neue', sans-serif; font-size: 4rem; font-weight: 900; text-transform: uppercase; letter-spacing: 8px; background: linear-gradient(90deg, #1a1c24 0%, #00C9FF 25%, #ffffff 50%, #00C9FF 75%, #1a1c24 100%); background-size: 200% auto; -webkit-background-clip: text; background-clip: text; color: transparent; animation: shine 3s linear infinite; }}
    .luxury-overlay {{ position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(6, 11, 38, 0.92); backdrop-filter: blur(10px); z-index: 999999; display: flex; flex-direction: column; justify-content: center; align-items: center; }}
    </style>
    """, unsafe_allow_html=True)
