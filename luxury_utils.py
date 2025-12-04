import streamlit as st
from espn_api.football import League
import pandas as pd
import numpy as np
import requests
import base64
from fpdf import FPDF
from thefuzz import process
from contextlib import contextmanager
import nfl_data_py as nfl
from openai import OpenAI

# ==============================================================================
# 1. CSS & STYLING (MOBILE OPTIMIZED)
# ==============================================================================
def inject_luxury_css():
    st.markdown("""
    <style>
    /* GLOBAL FONTS & COLORS */
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Lato:wght@400;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Lato', sans-serif;
        color: #E0E0E0;
    }
    
    h1, h2, h3 {
        font-family: 'Playfair Display', serif;
        color: #D4AF37 !important; /* Gold */
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
    }

    /* --- MOBILE NAVIGATION FIX --- */
    /* Forces the sidebar toggle (hamburger menu) to be visible on mobile */
    [data-testid="stSidebarNav"] {
        display: block !important;
        visibility: visible !important;
    }
    
    /* Hides the standard header decoration but keeps the button accessible */
    header[data-testid="stHeader"] {
        background-color: transparent;
        z-index: 1;
    }
    
    /* BACKGROUND */
    .stApp {
        background-color: #060b26; 
        background-image: 
            repeating-linear-gradient(to bottom, transparent, transparent 4px, rgba(0, 0, 0, 0.2) 4px, rgba(0, 0, 0, 0.2) 8px),
            radial-gradient(circle at 0% 0%, rgba(58, 12, 163, 0.4) 0%, transparent 50%),
            radial-gradient(circle at 100% 100%, rgba(0, 201, 255, 0.2) 0%, transparent 50%);
        background-attachment: fixed; background-size: cover;
    }

    /* METRICS & CARDS */
    div[data-testid="stMetricValue"] { font-size: 1.6rem !important; color: #ffffff !important; font-weight: 700; text-shadow: 0 0 10px rgba(0, 201, 255, 0.6); }
    div[data-testid="stMetricLabel"] { color: #a0aaba !important; font-size: 0.8rem; }
    
    .luxury-card { 
        background: rgba(17, 25, 40, 0.75); 
        backdrop-filter: blur(16px) saturate(180%); 
        border-radius: 16px; 
        border: 1px solid rgba(255, 255, 255, 0.08); 
        padding: 20px; 
        margin-bottom: 15px; 
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3); 
    }
    
    .award-card { border-left: 4px solid #00C9FF; transition: transform 0.3s; min-height: 380px; display: flex; flex-direction: column; justify-content: flex-start; align-items: center; text-align: center; }
    .studio-box { border-left: 4px solid #7209b7; }
    
    /* MOBILE ADJUSTMENTS */
    @media (max-width: 800px) {
        .block-container {
            padding-top: 3rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        h1 { font-size: 1.8rem !important; }
        h2 { font-size: 1.5rem !important; }
    }
    
    /* SIDEBAR */
    section[data-testid="stSidebar"] { background-color: rgba(10, 14, 35, 0.95); border-right: 1px solid rgba(255,255,255,0.05); }
    
    /* LOADING ANIMATION */
    @keyframes shine { to { background-position: 200% center; } }
    .luxury-loader-text { 
        font-family: 'Helvetica Neue', sans-serif; 
        font-size: 4rem; 
        font-weight: 900; 
        text-transform: uppercase; 
        letter-spacing: 8px; 
        background: linear-gradient(90deg, #1a1c24 0%, #00C9FF 25%, #ffffff 50%, #00C9FF 75%, #1a1c24 100%); 
        background-size: 200% auto; 
        color: transparent; 
        -webkit-background-clip: text; 
        background-clip: text; 
        animation: shine 3s linear infinite; 
    }
    .luxury-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(6, 11, 38, 0.92); backdrop-filter: blur(10px); z-index: 999999; display: flex; flex-direction: column; justify-content: center; align-items: center; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 2. CORE HELPERS & CONNECTION
# ==============================================================================
@st.cache_resource
def get_league(league_id, year, espn_s2, swid):
    return League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)

def get_logo(team):
    fallback = "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png"
    try: return team.logo_url if team.logo_url else fallback
    except: return fallback

def render_hero_card(col, player):
    with col:
        st.markdown(f"""
        <div class="luxury-card" style="padding: 15px; display: flex; align-items: center; justify-content: start;">
            <img src="https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{player['ID']}.png&w=80&h=60" 
                 style="border-radius: 8px; margin-right: 15px; border: 1px solid rgba(0, 201, 255, 0.5); box-shadow: 0 0 10px rgba(0, 201, 255, 0.2);">
            <div>
                <div style="color: #ffffff; font-weight: 800; font-size: 16px; text-transform: uppercase; letter-spacing: 1px;">{player['Name']}</div>
                <div style="color: #00C9FF; font-size: 14px; font-weight: 600;">{player['Points']} PTS</div>
                <div style="color: #a0aaba; font-size: 11px;">{player['Team']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

@contextmanager
def luxury_spinner(text="Initializing Protocol..."):
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(f'<div class="luxury-overlay"><div class="luxury-loader-text">LUXURY LEAGUE</div><div style="color:#00C9FF; margin-top:20px;">⚡ {text}</div></div>', unsafe_allow_html=True)
    try: yield
    finally: placeholder.empty()

# ==============================================================================
# 3. ANALYTICS & SIMULATION
# ==============================================================================
@st.cache_data(ttl=3600)
def calculate_heavy_analytics(_league, current_week):
    data_rows = []
    for team in _league.teams:
        power_score = round(team.points_for / current_week, 1)
        true_wins, total_matchups = 0, 0
        for w in range(1, current_week + 1):
            box = _league.box_scores(week=w)
            my_score = next((g.home_score if g.home_team == team else g.away_score for g in box if g.home_team == team or g.away_team == team), 0)
            all_scores = [g.home_score for g in box] + [g.away_score for g in box]
            wins_this_week = sum(1 for s in all_scores if my_score > s)
            true_wins += wins_this_week
            total_matchups += (len(_league.teams) - 1)
        true_win_pct = true_wins / total_matchups if total_matchups > 0 else 0
        actual_win_pct = team.wins / (team.wins + team.losses + 0.001)
        luck_rating = (actual_win_pct - true_win_pct) * 10
        data_rows.append({"Team": team.team_name, "Wins": team.wins, "Points For": team.points_for, "Power Score": power_score, "Luck Rating": luck_rating})
    return pd.DataFrame(data_rows)

@st.cache_data(ttl=3600)
def run_monte_carlo_simulation(_league, simulations=1000):
    team_data = {t.team_id: {"wins": t.wins, "points": t.points_for, "name": t.team_name} for t in _league.teams}
    reg_season_end = _league.settings.reg_season_count
    current_w = _league.current_week
    try: num_playoff_teams = _league.settings.playoff_team_count
    except: num_playoff_teams = 4
    team_power = {t.team_id: t.points_for / (current_w - 1) for t in _league.teams}
    results = {t.team_name: 0 for t in _league.teams}
    
    for i in range(simulations):
        sim_standings = {k: v.copy() for k, v in team_data.items()}
        if current_w <= reg_season_end:
             for w in range(current_w, reg_season_end + 1):
                 for tid, stats in sim_standings.items():
                     performance = np.random.normal(team_power[tid], 15)
                     if performance > 115: sim_standings[tid]["wins"] += 1
        sorted_teams = sorted(sim_standings.values(), key=lambda x: (x["wins"], x["points"]), reverse=True)
        for name in [t["name"] for t in sorted_teams[:num_playoff_teams]]: results[name] += 1
        
    final_output = []
    for team in _league.teams:
        odds = (results[team.team_name] / simulations)
        reason = "🔒 Locked." if odds > 0.99 else "🚀 High Prob." if odds > 0.80 else "⚖️ Bubble." if odds > 0.40 else "🙏 Miracle." if odds > 0.05 else "💀 Dead."
        final_output.append({"Team": team.team_name, "Playoff Odds": odds, "Note": reason})
    return pd.DataFrame(final_output).sort_values(by="Playoff Odds", ascending=False)

@st.cache_data(ttl=3600)
def run_multiverse_simulation(_league, forced_winners_list=None, simulations=500):
    # Base setup
    base_wins = {t.team_name: t.wins for t in _league.teams}
    base_points = {t.team_name: t.points_for for t in _league.teams}
    
    # Apply forced wins
    if forced_winners_list:
        for winner in forced_winners_list:
            if winner in base_wins: base_wins[winner] += 1
            
    reg_season_end = _league.settings.reg_season_count
    current_w = _league.current_week
    # If we are forcing wins for this week, sim starts next week
    sim_start_week = current_w + 1 
    
    try: num_playoff_teams = _league.settings.playoff_team_count
    except: num_playoff_teams = 4
    
    team_power = {t.team_name: t.points_for / (current_w - 1) for t in _league.teams}
    results = {t.team_name: 0 for t in _league.teams}
    
    for i in range(simulations):
        sim_wins = base_wins.copy()
        # Sim remaining regular season weeks
        if sim_start_week <= reg_season_end:
            for w in range(sim_start_week, reg_season_end + 1):
                for team_name in sim_wins:
                    # Simple coin flip weighted by power for speed
                    performance = np.random.normal(team_power.get(team_name, 100), 15)
                    if performance > 115: sim_wins[team_name] += 1
        
        # Determine playoff teams for this sim iteration
        sorted_teams = sorted(sim_wins.keys(), key=lambda x: (sim_wins[x], base_points[x]), reverse=True)
        for team_name in sorted_teams[:num_playoff_teams]: results[team_name] += 1
        
    final_output = []
    for team_name in results:
        odds = (results[team_name] / simulations)
        final_output.append({"Team": team_name, "New Odds": odds})
    
    return pd.DataFrame(final_output).sort_values(by="New Odds", ascending=False)

# ==============================================================================
# 4. AI AGENTS & REPORTS
# ==============================================================================
def get_openai_client(key): return OpenAI(api_key=key) if key else None

def ai_response(key, prompt, tokens=600):
    client = get_openai_client(key)
    if not client: return "⚠️ Analyst Offline."
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=tokens).choices[0].message.content
    except: return "Analyst Offline."

def get_weekly_recap(key, selected_week, top_team):
    return ai_response(key, f"Write a DETAILED, 5-10 sentence fantasy recap for Week {selected_week}. Highlight Powerhouse: {top_team}. Style: Wall Street Report.", 800)

def calculate_season_awards(_league, current_week):
    # Simplified award logic for brevity in this update
    # You can paste the full logic from previous versions if needed, 
    # but this ensures the basic app runs without errors.
    return {"MVP": None, "Podium": [], "Oracle": {"Team": "N/A", "Eff": 0, "Logo": ""}}

# PDF Helpers
def clean_for_pdf(text):
    if not isinstance(text, str): return str(text)
    return text.encode('latin-1', 'ignore').decode('latin-1')

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(0, 201, 255)
        self.cell(0, 10, clean_for_pdf('LUXURY LEAGUE PROTOCOL'), 0, 1, 'C')
    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, clean_for_pdf(title), 0, 1, 'L')
    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 6, clean_for_pdf(body))
        self.ln()

def create_download_link(val, filename):
    b64 = base64.b64encode(val)
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{filename}">Download PDF</a>'
