import streamlit as st
import requests
import base64
from fpdf import FPDF
from contextlib import contextmanager

# --- CONSTANTS ---
FALLBACK_LOGO = "https://g.espncdn.com/lm-static/logo-packs/ffl/CrazyHelmets-ToddDetwiler/Helmets_07.svg"

# --- METRIC DEFINITIONS ---
METRIC_DEFINITIONS = {
    "Power Score": "<b>Power Score:</b><br>Measures a team's dominance based on points scored per week relative to the league average.",
    "Luck": "<b>Luck Rating:</b><br>The difference between your actual Win % and your 'True Win %' (record if you played every team each week).<br><br><span style='color:#00C9FF'>Positive:</span> Lucky<br><span style='color:#FF4B4B'>Negative:</span> Unlucky",
    "Edge": "<b>The Edge:</b><br>Difference between Vegas Implied Points and ESPN Projections.<br><br><span style='color:#00C9FF'>Blue (▲):</span> Vegas is Higher (Sleeper).<br><span style='color:#FF4B4B'>Red (▼):</span> Vegas is Lower (Bust Risk).",
    "WOPR": "<b>WOPR (Weighted Opportunity Rating):</b><br>Combines Target Share & Air Yards Share. The #1 predictor of future WR fantasy performance.",
    "RYOE": "<b>RYOE (Rush Yards Over Expected):</b><br>Yards gained compared to what an average RB would get in the same blocking situation. Measures pure RB talent.",
    "CPOE": "<b>CPOE (Completion % Over Expected):</b><br>Accuracy metric that accounts for the difficulty of throws (depth, pressure, coverage).",
    "Efficiency": "<b>Efficiency (North/South):</b><br>Total distance traveled per yard gained. Lower is better (less dancing, more hitting the hole).",
    "Air Yards": "<b>Avg Intended Air Yards:</b><br>How far the ball travels in the air per attempt. High = Aggressive/Deep Threat."
}

def get_tooltip_html(key):
    text = METRIC_DEFINITIONS.get(key, "")
    if not text: return ""
    return f'<div class="tooltip">ℹ️<span class="tooltiptext">{text}</span></div>'

def get_logo(team):
    try:
        url = team.logo_url
        if not url or not isinstance(url, str) or len(url) < 10: return FALLBACK_LOGO
        if "mystique" in url.lower(): return FALLBACK_LOGO # Block internal ESPN links
        if url.startswith("http://"): url = url.replace("http://", "https://")
        valid_exts = ['.png', '.jpg', '.jpeg', '.svg', '.gif']
        if not any(ext in url.lower() for ext in valid_exts): return FALLBACK_LOGO
        return url
    except: return FALLBACK_LOGO

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
    
    /* --- NAVIGATION & MENU CONTROLS --- */
    
    /* 1. Hide the Standard Footer ("Made with Streamlit") */
    ._terminalButton_rix23_138 {{ visibility: hidden; }}
    
    /* 2. Hide the Top Right "Hamburger" Menu (Three Dots) */
    #MainMenu {{ visibility: hidden; }}
    
    /* 3. Hide the Bottom "Manage App" Button (Streamlit Cloud specific) */
    .stAppDeployButton {{ display: none; }}
    div:has(> a[href*="streamlit.io"]) {{ visibility: hidden; display: none; }}
    
    /* 4. FORCE SIDEBAR NAVIGATION TO BE VISIBLE */
    [data-testid="stSidebarNav"] {{ display: block !important; visibility: visible !important; }}
    
    /* 5. Ensure the Top-Left Toggle Button is Visible (for Mobile) */
    [data-testid="collapsedControl"] {{ display: block !important; visibility: visible !important; }}
    header[data-testid="stHeader"] {{ background: transparent; }}

    /* --- COMPONENT STYLING --- */
    .luxury-card {{ background: rgba(17, 25, 40, 0.75); backdrop-filter: blur(16px); border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.08); padding: 20px; margin-bottom: 15px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3); }}
    
    /* BADGES */
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
    
    /* GRID */
    .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 5px; margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1); }}
    .stat-box {{ text-align: center; }}
    .stat-val {{ font-size: 1.1rem; font-weight: 700; color: white; }}
    .stat-label {{ font-size: 0.65rem; color: #a0aaba; text-transform: uppercase; }}
    
    .edge-box {{ margin-top: 10px; background: rgba(0,0,0,0.3); padding: 8px; border-radius: 8px; text-align: center; font-size: 0.8rem; }}
    
    /* TOOLTIP */
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

@contextmanager
def luxury_spinner(text="Processing..."):
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(f'<div class="luxury-overlay"><div class="luxury-loader-text">LUXURY LEAGUE</div><div style="color:#00C9FF; margin-top:20px;">⚡ {text}</div></div>', unsafe_allow_html=True)
    try: yield
    finally: placeholder.empty()

def render_hero_card(col, player):
    with col:
        st.markdown(f"""<div class="luxury-card" style="padding: 15px; display: flex; align-items: center;"><img src="https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{player['ID']}.png&w=80&h=60" style="border-radius: 8px; margin-right: 15px; border: 1px solid rgba(0, 201, 255, 0.5);"><div><div style="color: white; font-weight: 800;">{player['Name']}</div><div style="color: #00C9FF; font-weight: 600;">{player['Points']} PTS</div><div style="color: #a0aaba; font-size: 0.8rem;">{player['Team']}</div></div></div>""", unsafe_allow_html=True)

def render_team_card(col, team_data, rank):
    power_tip = get_tooltip_html("Power Score")
    luck_tip = get_tooltip_html("Luck")
    
    logo_url = team_data.get('Logo')
    if not logo_url or "http" not in str(logo_url) or "mystique" in str(logo_url): 
        logo_url = FALLBACK_LOGO
        
    logo_html = f'<img src="{logo_url}" onerror="this.onerror=null; this.src=\'{FALLBACK_LOGO}\';" style="width:50px; height:50px; border-radius:50%; border:2px solid #00C9FF; margin-right:10px;">'
    
    with col:
        st.markdown(f"""<div class="luxury-card" style="border-left: 4px solid #D4AF37; display:flex; align-items:center;"><div style="font-size:2.5rem; font-weight:900; color:rgba(255,255,255,0.1); margin-right:15px; width:40px;">{rank}</div><div style="flex:1;"><div style="display:flex; align-items:center;">{logo_html}<div style="font-size:1.2rem; font-weight:bold; color:white;">{team_data['Team']}</div></div><div style="font-size:0.8rem; color:#a0aaba; margin-top:5px;">Power Score: <span style="color:#00C9FF; margin-left:4px;">{team_data['Power Score']}</span>{power_tip}</div></div><div style="text-align:right;"><div style="font-size:1.2rem; font-weight:bold; color:white;">{team_data['Wins']}W</div><div style="font-size:0.7rem; color:#a0aaba; display:flex; justify-content:flex-end; align-items:center;">Luck: {team_data['Luck Rating']:.1f}{luck_tip}</div></div></div>""", unsafe_allow_html=True)

def render_prop_card(col, row):
    v = row['Verdict']
    badge_class = "badge-fire" if "Must" in v or "Elite" in v else "badge-gem" if "1" in v else "badge-ok"
    pid = row.get('ESPN ID', 0)
    headshot = f"https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{pid}.png&w=100&h=100" if pid else "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png&w=100&h=100"
    
    main_stat = "Rec Yds"
    line_val = row.get('Rec Yds', 0)
    if row.get('Pass Yds', 0) > 0: main_stat, line_val = "Pass Yds", row['Pass Yds']
    elif row.get('Rush Yds', 0) > 0: main_stat, line_val = "Rush Yds", row['Rush Yds']
    
    edge_val = row.get('Edge', 0.0)
    edge_color = "#00C9FF" if edge_val > 0 else "#FF4B4B"
    edge_arrow = "▲" if edge_val > 0 else "▼"
    edge_tip = get_tooltip_html("Edge")
    
    hit_rate_str = row.get('Hit Rate', 'N/A')
    hit_color = "#E0E0E0"
    if "100%" in str(hit_rate_str): hit_color = "#00C9FF"
    elif "0%" in str(hit_rate_str): hit_color = "#FF4B4B"
    
    badges_html = f'<div class="meta-badge {badge_class}">{v}</div>'
    
    if "vs #" in str(row.get('Matchup Rank', '')):
        try:
            rank = int(re.search(r'#(\d+)', row['Matchup Rank']).group(1))
            m_class = "matchup-good" if rank <= 8 else "matchup-bad" if rank >= 24 else "matchup-mid"
            badges_html += f'<div class="meta-badge {m_class}">{row["Matchup Rank"]}</div>'
        except: pass

    w = row.get('Weather', {})
    if w and isinstance(w, dict):
        if w.get('Dome'):
             badges_html += f'<div class="meta-badge weather-neutral">🏟️ Dome</div>'
        else:
             wind = w.get('Wind', 0)
             precip = w.get('Precip', 0)
             temp = w.get('Temp', 70)
             w_icon, w_class = "☀️", "weather-neutral"
             if precip > 0.1: w_icon, w_class = "🌧️", "weather-warn"
             elif wind > 15: w_icon, w_class = "💨", "weather-warn"
             elif temp < 32: w_icon, w_class = "❄️", "weather-warn"
             badges_html += f'<div class="meta-badge {w_class}">{w_icon} {temp:.0f}°F</div>'

    insight = row.get('Insight', '')
    if insight:
        badges_html += f'<div class="meta-badge insight-purple">{insight}</div>'

    html = f"""<div class="luxury-card"><div style="display:flex; justify-content:space-between; align-items:start;"><div style="flex:1;"><div style="display:flex; flex-wrap:wrap; margin-bottom:8px;">{badges_html}</div><div style="font-size:1.3rem; font-weight:900; color:white; line-height:1.2; margin-bottom:5px;">{row['Player']}</div><div style="color:#a0aaba; font-size:0.8rem;">{row.get('Position', 'FLEX')} | {row.get('Team', 'FA')}</div></div><img src="{headshot}" style="width:70px; height:70px; border-radius:50%; border:2px solid {edge_color}; object-fit:cover; background:#000;"></div><div style="margin-top:10px; background:rgba(0,0,0,0.3); padding:8px; border-radius:8px; text-align:center; font-size:0.8rem; border:1px solid {edge_color}; color:{edge_color}; display:flex; justify-content:center; align-items:center;"><span style="margin-right:5px;">{edge_arrow} {abs(edge_val):.1f} pts vs ESPN</span>{edge_tip}</div><div class="stat-grid"><div class="stat-box"><div class="stat-val" style="color:#D4AF37;">{row['Proj Pts']:.1f}</div><div class="stat-label">Vegas Pts</div></div><div class="stat-box"><div class="stat-val" style="color:#fff;">{line_val:.0f}</div><div class="stat-label">{main_stat} Line</div></div><div class="stat-box"><div class="stat-val" style="color:{hit_color};">{hit_rate_str}</div><div class="stat-label">L5 Hit Rate</div></div></div></div>"""
    with col: st.markdown(html, unsafe_allow_html=True)

def render_lab_card(col, row):
    v = row['Verdict']
    badge_class = "badge-gem" if "ELITE" in v or "MONSTER" in v else "badge-ok" if "WORKHORSE" in v or "SNIPER" in v else "weather-neutral"
    pid = row.get('ID', 0)
    headshot = f"https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{pid}.png&w=100&h=100" if pid else "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png&w=100&h=100"
    val_color = "#4cc9f0"
    if "-" in str(row['Value']): val_color = "#FF4B4B"
    metric_key = "WOPR"
    if "RYOE" in row['Metric']: metric_key = "RYOE"
    elif "CPOE" in row['Metric']: metric_key = "CPOE"
    elif "Efficiency" in row.get('Beta Stat',''): metric_key = "Efficiency"
    elif "Air" in row.get('Beta Stat',''): metric_key = "Air Yards"
    tip_html = get_tooltip_html(metric_key)

    html = f"""<div class="luxury-card" style="border-left: 3px solid {val_color};"><div style="display:flex; justify-content:space-between; align-items:start;"><div style="flex:1;"><div style="display:flex; flex-wrap:wrap; margin-bottom:8px;"><div class="meta-badge {badge_class}">{v}</div></div><div style="font-size:1.3rem; font-weight:900; color:white; line-height:1.2; margin-bottom:2px;">{row['Player']}</div><div style="color:#a0aaba; font-size:0.8rem;">{row.get('Team', '')} | {row.get('Position', '')}</div></div><img src="{headshot}" style="width:70px; height:70px; border-radius:50%; border:2px solid {val_color}; object-fit:cover; background:#000;"></div><div style="margin-top:15px; padding-top:10px; border-top:1px solid rgba(255,255,255,0.1); display:grid; grid-template-columns: 1fr 1fr 1fr; gap: 5px; align-items:center;"><div style="text-align:center;"><div style="font-size:0.65rem; color:#a0aaba; text-transform:uppercase; display:flex; justify-content:center; align-items:center;">{row['Metric']}{tip_html}</div><div style="font-size:1.5rem; font-weight:900; color:{val_color};">{row['Value']}</div></div><div style="text-align:center; border-left:1px solid rgba(255,255,255,0.1);"><div style="font-size:0.65rem; color:#a0aaba; text-transform:uppercase;">Context</div><div style="font-size:0.9rem; color:#fff;">{row['Alpha Stat']}</div></div><div style="text-align:center; border-left:1px solid rgba(255,255,255,0.1);"><div style="font-size:0.65rem; color:#a0aaba; text-transform:uppercase;">Metric II</div><div style="font-size:0.9rem; color:#fff;">{row.get('Beta Stat', '-')}</div></div></div></div>"""
    with col: st.markdown(html, unsafe_allow_html=True)

def render_audit_card(col, row):
    grade_color = "#92FE9D"
    if "B" in row['Grade']: grade_color = "#4cc9f0"
    elif "C" in row['Grade']: grade_color = "#F7B801"
    elif "D" in row['Grade']: grade_color = "#F18701"
    elif "F" in row['Grade']: grade_color = "#FF4B4B"
    
    regret_html = f"""<div style="background: rgba(255, 75, 75, 0.1); border-left: 3px solid #FF4B4B; padding: 8px; margin-top: 10px; border-radius: 4px;"><div style="color: #a0aaba; font-size: 0.75rem; text-transform: uppercase;">Biggest Regret</div><div style="color: white; font-weight: bold;">{row['Regret']}</div><div style="color: #FF4B4B; font-size: 0.8rem;">Left {row['Lost Pts']:.1f} pts on bench</div></div>""" if row['Lost Pts'] > 0 else f"""<div style="background: rgba(146, 254, 157, 0.1); border-left: 3px solid #92FE9D; padding: 8px; margin-top: 10px; border-radius: 4px;"><div style="color: #92FE9D; font-weight: bold;">💎 Perfect Lineup</div><div style="color: #a0aaba; font-size: 0.8rem;">No points left on table</div></div>"""

    logo_url = row.get("Logo")
    if not logo_url or "http" not in str(logo_url) or "mystique" in str(logo_url): 
        logo_url = FALLBACK_LOGO
        
    logo_html = f'<img src="{logo_url}" onerror="this.onerror=null; this.src=\'{FALLBACK_LOGO}\';" style="width:50px; height:50px; border-radius:50%; border:2px solid {grade_color};">'

    html = f"""<div class="luxury-card" style="border-top: 4px solid {grade_color};"><div style="display:flex; justify-content:space-between; align-items:center;"><div style="display:flex; align-items:center; gap:10px;">{logo_html}<div><div style="font-size:1.1rem; font-weight:900; color:white;">{row['Team']}</div><div style="font-size:0.8rem; color:#a0aaba;">Efficiency: {row['Efficiency']:.1f}%</div></div></div><div style="text-align:center;"><div style="font-size:2.5rem; font-weight:900; color:{grade_color}; text-shadow: 0 0 10px {grade_color}40;">{row['Grade']}</div><div style="font-size:0.7rem; color:{grade_color}; text-transform:uppercase;">Grade</div></div></div>{regret_html}<div class="stat-grid" style="margin-top:10px; padding-top:10px; border-top:1px solid rgba(255,255,255,0.05);"><div class="stat-box"><div class="stat-val" style="color:#fff;">{row['Starters']:.1f}</div><div class="stat-label">Starter Pts</div></div><div class="stat-box"><div class="stat-val" style="color:#a0aaba;">{row['Bench']:.1f}</div><div class="stat-label">Bench Pts</div></div><div class="stat-box"><div class="stat-val" style="color:#FF4B4B;">-{row['Lost Pts']:.1f}</div><div class="stat-label">Lost Potential</div></div></div></div>"""
    with col: st.markdown(html, unsafe_allow_html=True)

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(0, 201, 255)
        self.cell(0, 10, clean_for_pdf('LUXURY LEAGUE PROTOCOL // WEEKLY BRIEFING'), 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 114, 255)
        self.cell(0, 10, clean_for_pdf(title), 0, 1, 'L')
        self.ln(2)
    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.set_text_color(50)
        self.multi_cell(0, 6, clean_for_pdf(body))
        self.ln()

def create_download_link(val, filename):
    b64 = base64.b64encode(val)
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{filename}">Download Executive Briefing (PDF)</a>'
