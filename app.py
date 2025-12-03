import streamlit as st
from espn_api.football import League
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI
from streamlit_lottie import st_lottie
import requests
import random
import base64
from fpdf import FPDF
from thefuzz import process
import time
from contextlib import contextmanager
import nfl_data_py as nfl

# ------------------------------------------------------------------
# 1. CONFIGURATION & VISION UI THEME
# ------------------------------------------------------------------
st.set_page_config(page_title="Luxury League Dashboard", page_icon="💎", layout="wide")

# SETTINGS
START_YEAR = 2021 

st.markdown("""
    <style>
    /* 1. HIDE DEFAULT STREAMLIT ELEMENTS */
    header[data-testid="stHeader"] { display: none; }
    footer { display: none; }
    .block-container { padding-top: 1rem !important; }

    /* 2. MAIN BACKGROUND */
    .stApp {
        background-color: #060b26; 
        background-image: 
            repeating-linear-gradient(to bottom, transparent, transparent 4px, rgba(0, 0, 0, 0.2) 4px, rgba(0, 0, 0, 0.2) 8px),
            radial-gradient(circle at 0% 0%, rgba(58, 12, 163, 0.4) 0%, transparent 50%),
            radial-gradient(circle at 100% 100%, rgba(0, 201, 255, 0.2) 0%, transparent 50%);
        background-attachment: fixed;
        background-size: cover;
    }

    /* 3. TYPOGRAPHY */
    h1, h2, h3, h4 { color: #ffffff !important; font-family: 'Helvetica Neue', sans-serif; font-weight: 700 !important; letter-spacing: 0.5px; text-shadow: 0 2px 4px rgba(0,0,0,0.5); }
    div[data-testid="stMetricValue"] { font-size: 1.8rem !important; color: #ffffff !important; font-weight: 700; text-shadow: 0 0 15px rgba(0, 201, 255, 0.6); }
    div[data-testid="stMetricLabel"] { color: #a0aaba !important; font-size: 0.9rem; }

    /* 4. CARDS */
    .luxury-card {
        background: rgba(17, 25, 40, 0.75); backdrop-filter: blur(16px) saturate(180%);
        border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 24px; margin-bottom: 20px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    }
    .award-card { border-left: 4px solid #00C9FF; }
    .studio-box { border-left: 4px solid #7209b7; }

    /* 5. SIDEBAR & MENU FIX */
    section[data-testid="stSidebar"] { background-color: rgba(10, 14, 35, 0.95); border-right: 1px solid rgba(255,255,255,0.05); }
    div[data-testid="stRadio"] > label { color: #8a9ab0 !important; font-size: 0.9rem; margin-bottom: 10px; }
    div[role="radiogroup"] label { 
        padding: 12px 15px !important; border-radius: 10px !important; transition: all 0.3s ease; 
        margin-bottom: 5px; border: 1px solid transparent; background-color: transparent;
    }
    div[role="radiogroup"] label:hover { background-color: rgba(255, 255, 255, 0.05) !important; color: #ffffff !important; transform: translateX(5px); }
    div[role="radiogroup"] label[data-checked="true"] {
        background: linear-gradient(90deg, rgba(0, 201, 255, 0.15), transparent) !important;
        border-left: 4px solid #00C9FF !important; color: #ffffff !important; font-weight: 700 !important;
    }
    div[role="radiogroup"] label > div:first-child { display: none !important; }
    div[data-testid="stMarkdownContainer"] p { font-size: 1rem; }

    /* 6. TABLES */
    div[data-testid="stDataFrame"] { background-color: rgba(17, 25, 40, 0.5); border-radius: 15px; padding: 15px; border: 1px solid rgba(255,255,255,0.05); }

    /* 7. LOADING OVERLAY */
    @keyframes shine { to { background-position: 200% center; } }
    .luxury-loader-text {
        font-family: 'Helvetica Neue', sans-serif; font-size: 4rem; font-weight: 900; text-transform: uppercase; letter-spacing: 8px;
        background: linear-gradient(90deg, #1a1c24 0%, #00C9FF 25%, #ffffff 50%, #00C9FF 75%, #1a1c24 100%);
        background-size: 200% auto; color: transparent; -webkit-background-clip: text; background-clip: text; animation: shine 3s linear infinite;
    }
    .loader-sub { font-family: monospace; color: #00C9FF; font-size: 1.2rem; margin-top: 20px; text-transform: uppercase; letter-spacing: 3px; animation: blink 1.5s infinite ease-in-out; }
    .luxury-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(6, 11, 38, 0.92); backdrop-filter: blur(10px); z-index: 999999; display: flex; flex-direction: column; justify-content: center; align-items: center; }
    </style>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------------
# 2. CONNECTION & HELPER FUNCTIONS
# ------------------------------------------------------------------
try:
    league_id = st.secrets["league_id"]
    swid = st.secrets["swid"]
    espn_s2 = st.secrets["espn_s2"]
    openai_key = st.secrets.get("openai_key")
    odds_api_key = st.secrets.get("odds_api_key")
    year = 2025

    @st.cache_resource
    def get_league():
        return League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)

    league = get_league()

except Exception as e:
    st.error(f"🔒 Connection Error: {e}")
    st.stop()

def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200: return None
        return r.json()
    except: return None

@contextmanager
def luxury_spinner(text="Initializing Protocol..."):
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(f'<div class="luxury-overlay"><div class="luxury-loader-text">LUXURY LEAGUE</div><div class="loader-sub">⚡ {text}</div></div>', unsafe_allow_html=True)
    try: yield
    finally: placeholder.empty()

def clean_for_pdf(text):
    if not isinstance(text, str): return str(text)
    return text.encode('latin-1', 'ignore').decode('latin-1')

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

@st.cache_data(ttl=3600)
def get_vegas_props(api_key):
    url = 'https://api.the-odds-api.com/v4/sports/americanfootball_nfl/events/upcoming/odds'
    params = {'api_key': api_key, 'regions': 'us', 'markets': 'player_pass_yds,player_rush_yds,player_reception_yds,player_anytime_td', 'oddsFormat': 'american', 'dateFormat': 'iso'}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 422: return pd.DataFrame({"Status": ["Market Closed"]}) 
        if response.status_code != 200: return None
        data = response.json()
        if not data: return pd.DataFrame({"Status": ["Market Closed"]}) 
        
        player_props = {}
        for event in data:
            for bookmaker in event['bookmakers']:
                if bookmaker['key'] in ['draftkings', 'fanduel', 'mgm', 'caesars']:
                    for market in bookmaker['markets']:
                        key = market['key']
                        for outcome in market['outcomes']:
                            name = outcome['description']
                            if name not in player_props: player_props[name] = {'pass':0, 'rush':0, 'rec':0, 'td':0}
                            if key == 'player_pass_yds': player_props[name]['pass'] = outcome.get('point', 0)
                            elif key == 'player_rush_yds': player_props[name]['rush'] = outcome.get('point', 0)
                            elif key == 'player_reception_yds': player_props[name]['rec'] = outcome.get('point', 0)
                            elif key == 'player_anytime_td':
                                odds = outcome.get('price', 0)
                                prob = 100/(odds+100) if odds > 0 else abs(odds)/(abs(odds)+100)
                                player_props[name]['td'] = prob
        vegas_data = []
        for name, s in player_props.items():
            score = (s['pass']*0.04) + (s['rush']*0.1) + (s['rec']*0.1) + (s['td']*6)
            if score > 1: vegas_data.append({"Player": name, "Vegas Score": score})
        return pd.DataFrame(vegas_data)
    except: return None

lottie_loading = load_lottieurl("https://lottie.host/5a882010-89b6-45bc-8a4d-06886982f8d8/WfK7bXoGqj.json")
lottie_forecast = load_lottieurl("https://lottie.host/936c69f6-0b89-4b68-b80c-0390f777c5d7/C0Z2y3S0bM.json")
lottie_trophy = load_lottieurl("https://lottie.host/362e7839-2425-4c75-871d-534b82d02c84/hL9w4jR9aF.json")
lottie_trade = load_lottieurl("https://lottie.host/e65893a7-e54e-4f0b-9366-0749024f2b1d/z2Xg6c4h5r.json")
lottie_wire = load_lottieurl("https://lottie.host/4e532997-5b65-4f4c-8b2b-077555627798/7Q9j7Z9g9z.json")
lottie_lab = load_lottieurl("https://lottie.host/49907932-975d-453d-b8f1-2d6408468123/bF2y8T8k7s.json")

# ------------------------------------------------------------------
# 3. ANALYTICS ENGINES
# ------------------------------------------------------------------
@st.cache_data(ttl=3600)
def calculate_heavy_analytics(current_week):
    data_rows = []
    for team in league.teams:
        power_score = round(team.points_for / current_week, 1)
        true_wins, total_matchups = 0, 0
        for w in range(1, current_week + 1):
            box = league.box_scores(week=w)
            my_score = next((g.home_score if g.home_team == team else g.away_score for g in box if g.home_team == team or g.away_team == team), 0)
            all_scores = [g.home_score for g in box] + [g.away_score for g in box]
            wins_this_week = sum(1 for s in all_scores if my_score > s)
            true_wins += wins_this_week
            total_matchups += (len(league.teams) - 1)
        true_win_pct = true_wins / total_matchups if total_matchups > 0 else 0
        actual_win_pct = team.wins / (team.wins + team.losses + 0.001)
        luck_rating = (actual_win_pct - true_win_pct) * 10
        data_rows.append({"Team": team.team_name, "Wins": team.wins, "Points For": team.points_for, "Power Score": power_score, "Luck Rating": luck_rating, "True Win %": true_win_pct})
    return pd.DataFrame(data_rows)

@st.cache_data(ttl=3600)
def calculate_season_awards(current_week):
    player_points = {}
    team_bench_points = {t.team_name: 0 for t in league.teams}
    single_game_high = {"Team": "", "Score": 0, "Week": 0}
    biggest_blowout = {"Winner": "", "Loser": "", "Margin": 0, "Week": 0}
    heartbreaker = {"Winner": "", "Loser": "", "Margin": 999, "Week": 0}
    current_streaks = {t.team_name: 0 for t in league.teams}
    max_streaks = {t.team_name: 0 for t in league.teams}
    asleep_count = {t.team_name: 0 for t in league.teams}
    
    for w in range(1, current_week + 1):
        box = league.box_scores(week=w)
        for game in box:
            h_name, a_name = game.home_team.team_name, game.away_team.team_name
            margin = abs(game.home_score - game.away_score)
            if game.home_score > game.away_score: winner, loser = h_name, a_name
            else: winner, loser = a_name, h_name
            
            current_streaks[winner] += 1
            current_streaks[loser] = 0
            if current_streaks[winner] > max_streaks[winner]: max_streaks[winner] = current_streaks[winner]
            
            if margin > biggest_blowout["Margin"]: biggest_blowout = {"Winner": winner, "Loser": loser, "Margin": margin, "Week": w}
            if margin < heartbreaker["Margin"]: heartbreaker = {"Winner": winner, "Loser": loser, "Margin": margin, "Week": w}
            if game.home_score > single_game_high["Score"]: single_game_high = {"Team": h_name, "Score": game.home_score, "Week": w}
            if game.away_score > single_game_high["Score"]: single_game_high = {"Team": a_name, "Score": game.away_score, "Week": w}
            
            def process_roster(lineup, team_name):
                for p in lineup:
                    if p.playerId not in player_points: player_points[p.playerId] = {"Name": p.name, "Points": 0, "Owner": team_name, "ID": p.playerId}
                    player_points[p.playerId]["Points"] += p.points
                    if p.slot_position == 'BE': team_bench_points[team_name] += p.points
                    else: 
                        if p.points == 0: asleep_count[team_name] += 1
            process_roster(game.home_lineup, h_name)
            process_roster(game.away_lineup, a_name)
            
    sorted_players = sorted(player_points.values(), key=lambda x: x['Points'], reverse=True)
    sorted_bench = sorted(team_bench_points.items(), key=lambda x: x[1], reverse=True)
    sorted_teams = sorted(league.teams, key=lambda x: x.points_for, reverse=True)
    longest_streak_team = max(max_streaks, key=max_streaks.get)
    sleepiest_team = max(asleep_count, key=asleep_count.get)
    
    return {
        "MVP": sorted_players[0] if sorted_players else None,
        "Bench King": sorted_bench[0] if sorted_bench else None,
        "Single Game": single_game_high, "Blowout": biggest_blowout, "Heartbreaker": heartbreaker,
        "Streak": {"Team": longest_streak_team, "Length": max_streaks[longest_streak_team]},
        "Sleeper": {"Team": sleepiest_team, "Count": asleep_count[sleepiest_team]},
        "Best Manager": {"Team": sorted_teams[0].team_name, "Points": sorted_teams[0].points_for, "Logo": sorted_teams[0].logo_url}
    }

@st.cache_data(ttl=3600)
def run_monte_carlo_simulation(simulations=1000):
    team_data = {t.team_id: {"wins": t.wins, "points": t.points_for, "name": t.team_name} for t in league.teams}
    reg_season_end = league.settings.reg_season_count
    current_w = league.current_week
    try: num_playoff_teams = league.settings.playoff_team_count
    except: num_playoff_teams = 4
    team_power = {t.team_id: t.points_for / (current_w - 1) for t in league.teams}
    
    results = {t.team_name: 0 for t in league.teams}
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
    for team in league.teams:
        odds = (results[team.team_name] / simulations) * 100
        reason = "🔒 Locked." if odds > 99 else "🚀 High Prob." if odds > 80 else "⚖️ Bubble." if odds > 40 else "🙏 Miracle." if odds > 5 else "💀 Dead."
        final_output.append({"Team": team.team_name, "Playoff Odds": odds, "Note": reason})
    return pd.DataFrame(final_output).sort_values(by="Playoff Odds", ascending=False)

@st.cache_data(ttl=3600)
def scan_dark_pool(limit=15):
    free_agents = league.free_agents(size=100)
    pool_data = []
    for player in free_agents:
        try:
            status = getattr(player, 'injuryStatus', 'ACTIVE')
            status_str = str(status).upper().replace("_", " ") if status else "ACTIVE"
            if any(k in status_str for k in ['OUT', 'IR', 'RESERVE', 'SUSPENDED', 'PUP', 'DOUBTFUL']): continue
            total = player.total_points if player.total_points > 0 else player.projected_total_points
            avg_pts = total / league.current_week if league.current_week > 0 else 0
            if avg_pts > 1.0:
                pool_data.append({"Name": player.name, "Position": player.position, "Team": player.proTeam, "Avg Pts": avg_pts, "Total Pts": total, "ID": player.playerId, "Status": status_str})
        except: continue
    df = pd.DataFrame(pool_data)
    if not df.empty: df = df.sort_values(by="Avg Pts", ascending=False).head(limit)
    return df

@st.cache_data(ttl=3600)
def get_dynasty_data(current_year, start_year):
    all_seasons_data = []
    for y in range(start_year, current_year + 1):
        try:
            hist_league = League(league_id=league_id, year=y, espn_s2=espn_s2, swid=swid)
            for team in hist_league.teams:
                if team.owners:
                    owner_id = team.owners[0]['id']
                    owner_name = f"{team.owners[0]['firstName']} {team.owners[0]['lastName']}"
                else:
                    owner_id = f"Unknown_{team.team_id}"
                    owner_name = f"Team {team.team_id}"
                made_playoffs = 1 if team.final_standing <= hist_league.settings.playoff_team_count else 0
                is_champ = 1 if team.final_standing == 1 else 0
                all_seasons_data.append({"Year": y, "Owner ID": owner_id, "Manager": owner_name, "Team Name": team.team_name, "Wins": team.wins, "Losses": team.losses, "Points For": team.points_for, "Champ": is_champ, "Playoffs": made_playoffs})
        except Exception as e: continue
    return pd.DataFrame(all_seasons_data)

def process_dynasty_leaderboard(df_history):
    if df_history.empty: return pd.DataFrame()
    leaderboard = df_history.groupby("Owner ID").agg({"Manager": "last", "Wins": "sum", "Losses": "sum", "Points For": "sum", "Champ": "sum", "Playoffs": "sum", "Year": "count"}).reset_index()
    leaderboard["Win %"] = leaderboard["Wins"] / (leaderboard["Wins"] + leaderboard["Losses"]) * 100
    leaderboard = leaderboard.rename(columns={"Year": "Seasons"})
    return leaderboard.sort_values(by="Wins", ascending=False)

# --- F. NEXT GEN STATS ENGINE (UPDATED WITH ADVANCED METRICS) ---
@st.cache_data(ttl=3600 * 12) 
def load_nextgen_data(year):
    try:
        # Fetch raw data
        df_rec = nfl.import_ngs_data(stat_type='receiving', years=[year])
        df_rush = nfl.import_ngs_data(stat_type='rushing', years=[year])
        df_pass = nfl.import_ngs_data(stat_type='passing', years=[year])
        # Fetch seasonal data for WOPR/Target Share
        df_seas = nfl.import_seasonal_data([year])
        return df_rec, df_rush, df_pass, df_seas
    except: return None, None, None, None

def analyze_nextgen_metrics(roster, year):
    df_rec, df_rush, df_pass, df_seas = load_nextgen_data(year)
    if df_rec is None or df_rec.empty: return pd.DataFrame()

    insights = []
    for player in roster:
        p_name = player.name
        pos = player.position
        
        # Fix: Safely get ID and Team
        pid = getattr(player, 'playerId', None)
        p_team = getattr(player, 'proTeam', 'N/A')

        # WR/TE Analysis
        if pos in ['WR', 'TE']:
            match_result = process.extractOne(p_name, df_rec['player_display_name'].unique())
            if match_result and match_result[1] > 90:
                match_name = match_result[0]
                # NGS Stats
                player_stats = df_rec[df_rec['player_display_name'] == match_name]
                if not player_stats.empty:
                    stats = player_stats.mean(numeric_only=True)
                    sep = stats.get('avg_separation', 0)
                    yac_exp = stats.get('avg_yac_above_expectation', 0)
                    
                    # Seasonal Stats (WOPR/Target Share)
                    # We match on name again in the seasonal dataframe
                    # Note: nfl_data_py names might slightly differ, but usually consistent enough
                    seas_match = process.extractOne(p_name, df_seas['player_name'].unique())
                    if seas_match and seas_match[1] > 90:
                        seas_stats = df_seas[df_seas['player_name'] == seas_match[0]].iloc[0]
                        wopr = seas_stats.get('wopr', 0)
                        tgt_sh = seas_stats.get('tgt_sh', 0)
                    else:
                        wopr, tgt_sh = 0, 0

                    verdict = "HOLD"
                    if wopr > 0.7: verdict = "💎 ELITE (Alpha WR1)"
                    elif sep > 3.5: verdict = "⚡ SEPARATOR (Open)"
                    elif tgt_sh > 0.25: verdict = "📈 VOLUME KING"
                    elif yac_exp > 2.0: verdict = "🚀 YAC MONSTER"
                    
                    insights.append({
                        "Player": p_name, "ID": pid, "Team": p_team, "Position": pos,
                        "Metric": "WOPR (Opp Share)", "Value": f"{wopr:.2f}", 
                        "Alpha Stat": f"{sep:.1f} yds Sep", "Verdict": verdict
                    })

        # RB Analysis
        elif pos == 'RB' and not df_rush.empty:
            match_result = process.extractOne(p_name, df_rush['player_display_name'].unique())
            if match_result and match_result[1] > 90:
                match_name = match_result[0]
                player_stats = df_rush[df_rush['player_display_name'] == match_name]
                if not player_stats.empty:
                    stats = player_stats.mean(numeric_only=True)
                    ryoe = stats.get('rush_yards_over_expected_per_att', 0)
                    eff = stats.get('efficiency', 0) 
                    box_8 = stats.get('percent_attempts_gte_eight_defenders', 0)
                    
                    verdict = "HOLD"
                    if ryoe > 1.0: verdict = "💎 ELITE (Creator)"
                    elif box_8 > 30: verdict = "💪 WORKHORSE (Stacked Box)"
                    elif ryoe < -0.5: verdict = "🚫 PLODDER"
                    
                    insights.append({
                        "Player": p_name, "ID": pid, "Team": p_team, "Position": pos,
                        "Metric": "RYOE / Att", "Value": f"{ryoe:+.2f}", 
                        "Alpha Stat": f"{box_8:.0f}% 8-Man Box", "Verdict": verdict
                    })
        
        # QB Analysis
        elif pos == 'QB' and not df_pass.empty:
            match_result = process.extractOne(p_name, df_pass['player_display_name'].unique())
            if match_result and match_result[1] > 90:
                match_name = match_result[0]
                player_stats = df_pass[df_pass['player_display_name'] == match_name]
                if not player_stats.empty:
                    stats = player_stats.mean(numeric_only=True)
                    cpoe = stats.get('completion_percentage_above_expectation', 0)
                    time_throw = stats.get('avg_time_to_throw', 0)
                    
                    verdict = "HOLD"
                    if cpoe > 5.0: verdict = "🎯 SNIPER"
                    elif time_throw > 3.0: verdict = "⏳ HOLDER (Sack Risk)"
                    elif cpoe < -2.0: verdict = "📉 SHAKY"
                    
                    insights.append({
                        "Player": p_name, "ID": pid, "Team": p_team, "Position": pos,
                        "Metric": "CPOE", "Value": f"{cpoe:+.1f}%", 
                        "Alpha Stat": f"{time_throw:.2f}s Time/Throw", "Verdict": verdict
                    })

    return pd.DataFrame(insights)

# ------------------------------------------------------------------
# 4. SIDEBAR NAVIGATION
# ------------------------------------------------------------------
st.sidebar.title("🥂 The Concierge")
current_week = league.current_week - 1
if current_week == 0: current_week = 1
selected_week = st.sidebar.slider("Select Week", 1, current_week, current_week)
st.sidebar.markdown("---")

P_LEDGER, P_HIERARCHY, P_AUDIT, P_HEDGE, P_LAB, P_FORECAST, P_NEXT, P_PROP, P_DEAL, P_DARK, P_TROPHY, P_VAULT = "📜 The Ledger", "📈 The Hierarchy", "🔎 The Audit", "💎 The Hedge Fund", "🧬 The Lab", "🔮 The Forecast", "🚀 Next Week", "📊 The Prop Desk", "🤝 The Dealmaker", "🕵️ The Dark Pool", "🏆 Trophy Room", "⏳ The Vault"
page_options = [P_LEDGER, P_HIERARCHY, P_AUDIT, P_HEDGE, P_LAB, P_FORECAST, P_NEXT, P_PROP, P_DEAL, P_DARK, P_TROPHY, P_VAULT]
selected_page = st.sidebar.radio("Navigation", page_options, label_visibility="collapsed")

st.sidebar.markdown("---")
if st.sidebar.button("📄 Generate PDF Report"):
    with luxury_spinner("Compiling Intelligence Report..."):
        if "recap" not in st.session_state: st.session_state["recap"] = "Analysis Generated for PDF."
        if "awards" not in st.session_state: st.session_state["awards"] = calculate_season_awards(current_week)
        if "playoff_odds" not in st.session_state: st.session_state["playoff_odds"] = run_monte_carlo_simulation()

        pdf = PDF()
        pdf.add_page()
        pdf.chapter_title(f"WEEK {selected_week} EXECUTIVE BRIEFING")
        pdf.chapter_body(st.session_state["recap"].replace("*", "").replace("#", ""))
        
        awards = st.session_state["awards"]
        pdf.chapter_title("THE TROPHY ROOM")
        if awards['MVP']: pdf.chapter_body(f"MVP: {awards['MVP']['Name']} ({awards['MVP']['Points']:.1f} pts)")
        if awards['Best Manager']: pdf.chapter_body(f"The Whale: {awards['Best Manager']['Team']} ({awards['Best Manager']['Points']:.1f} pts)")
        
        if "playoff_odds" in st.session_state:
            pdf.chapter_title("PLAYOFF PROJECTIONS")
            df_odds = st.session_state["playoff_odds"]
            if df_odds is not None and not df_odds.empty:
                for i, row in df_odds.head(5).iterrows(): pdf.chapter_body(f"{row['Team']}: {row['Playoff Odds']:.1f}%")

        html = create_download_link(pdf.output(dest="S").encode("latin-1"), f"Luxury_League_Week_{selected_week}.pdf")
        st.sidebar.markdown(html, unsafe_allow_html=True)

# ------------------------------------------------------------------
# 5. DATA PROCESSING & AI
# ------------------------------------------------------------------
if 'box_scores' not in st.session_state or st.session_state.get('week') != selected_week:
    with luxury_spinner(f"Accessing Week {selected_week} Data..."):
        st.session_state['box_scores'] = league.box_scores(week=selected_week)
        st.session_state['week'] = selected_week
    st.rerun()

box_scores = st.session_state['box_scores']
matchup_data, efficiency_data, all_active_players, bench_highlights = [], [], [], []

for game in box_scores:
    home, away = game.home_team, game.away_team
    def get_roster_data(lineup, team_name):
        starters, bench, p_start, p_bench = [], [], 0, 0
        for p in lineup:
            info = {"Name": p.name, "Score": p.points, "Pos": p.slot_position}
            status = getattr(p, 'injuryStatus', 'ACTIVE')
            status_str = str(status).upper().replace("_", " ") if status else "ACTIVE"
            is_injured = any(k in status_str for k in ['OUT', 'IR', 'RESERVE', 'SUSPENDED'])
            if p.slot_position == 'BE':
                bench.append(info); p_bench += p.points
                if p.points > 15: bench_highlights.append({"Team": team_name, "Player": p.name, "Score": p.points})
            else:
                starters.append(info); p_start += p.points
                if not is_injured: all_active_players.append({"Name": p.name, "Points": p.points, "Team": team_name, "ID": p.playerId})
        return starters, bench, p_start, p_bench

    h_r, h_br, h_s, h_b = get_roster_data(game.home_lineup, home.team_name)
    a_r, a_br, a_s, a_b = get_roster_data(game.away_lineup, away.team_name)
    matchup_data.append({"Home": home.team_name, "Home Score": game.home_score, "Home Logo": home.logo_url, "Home Roster": h_r, "Away": away.team_name, "Away Score": game.away_score, "Away Logo": away.logo_url, "Away Roster": a_r})
    efficiency_data.append({"Team": home.team_name, "Starters": h_s, "Bench": h_b, "Total Potential": h_s + h_b})
    efficiency_data.append({"Team": away.team_name, "Starters": a_s, "Bench": a_b, "Total Potential": a_s + a_b})

df_eff = pd.DataFrame(efficiency_data).sort_values(by="Total Potential", ascending=False)
df_players = pd.DataFrame(all_active_players).sort_values(by="Points", ascending=False).head(5)
df_bench_stars = pd.DataFrame(bench_highlights).sort_values(by="Score", ascending=False).head(5)

def get_openai_client(): return OpenAI(api_key=openai_key) if openai_key else None
def ai_response(prompt, tokens=600):
    client = get_openai_client()
    if not client: return "⚠️ Analyst Offline."
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=tokens).choices[0].message.content
    except: return "Analyst Offline."

def get_ai_scouting_report(free_agents_str):
    client = get_openai_client()
    if not client: return "⚠️ Analyst Offline."
    prompt = f"""
    You are an elite NFL Talent Scout. Here is a list of available, healthy free agents (The Dark Pool):
    {free_agents_str}
    
    Identify 3 "Must Add" players.
    For each, provide a 1-sentence "Scouting Report" on why they are a hidden gem (e.g. recent volume, injury opportunity).
    Style: Scouting Notebook (Gritty, technical).
    """
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=500).choices[0].message.content
    except: return "Analyst Offline."

def get_weekly_recap():
    client = get_openai_client()
    if not client: return "⚠️ Add 'openai_key' to secrets."
    top_scorer = df_eff.iloc[0]['Team']
    prompt = f"Write a DETAILED, 5-10 sentence fantasy recap for Week {selected_week}. Highlight Powerhouse: {top_scorer}. Style: Wall Street Report."
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=800).choices[0].message.content
    except: return "Analyst Offline."

def get_rankings_commentary():
    client = get_openai_client()
    if not client: return "⚠️ Analyst Offline."
    top = df_eff.iloc[0]['Team']
    bottom = df_eff.iloc[-1]['Team']
    prompt = f"Write a 5-8 sentence commentary on Power Rankings. Praise {top} and mock {bottom}. Style: Stephen A. Smith."
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=600).choices[0].message.content
    except: return "Analyst Offline."

def get_next_week_preview(games_list):
    client = get_openai_client()
    if not client: return "⚠️ Analyst Offline."
    matchups_str = ", ".join([f"{g['home']} vs {g['away']} (Spread: {g['spread']})" for g in games_list])
    prompt = f"Act as a Vegas Sports Bookie. Provide a detailed preview of next week's matchups: {matchups_str}. Pick 'Lock of the Week' and 'Upset Alert'."
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=800).choices[0].message.content
    except: return "Analyst Offline."

def get_season_retrospective(mvp, best_mgr):
    client = get_openai_client()
    if not client: return "⚠️ Analyst Offline."
    prompt = f"Write a 'State of the Union' address for the league. MVP: {mvp}. Best Manager: {best_mgr}. Style: Presidential."
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=1000).choices[0].message.content
    except: return "Analyst Offline."

def get_ai_trade_proposal(team_a, team_b, roster_a, roster_b):
    client = get_openai_client()
    if not client: return "⚠️ Analyst Offline."
    prompt = f"Act as Trade Broker. Propose a fair trade between Team A ({team_a}): {roster_a} and Team B ({team_b}): {roster_b}. Explain why."
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=600).choices[0].message.content
    except: return "Analyst Offline."

# ------------------------------------------------------------------
# 7. DASHBOARD UI
# ------------------------------------------------------------------
st.title(f"🏛️ Luxury League Protocol: Week {selected_week}")
# HERO ROW (Weekly Elite)
st.markdown("### 🌟 Weekly Elite")
hero_c1, hero_c2, hero_c3 = st.columns(3)
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
top_3 = df_players.head(3).reset_index(drop=True)
if len(top_3) >= 1: render_hero_card(hero_c1, top_3.iloc[0])
if len(top_3) >= 2: render_hero_card(hero_c2, top_3.iloc[1])
if len(top_3) >= 3: render_hero_card(hero_c3, top_3.iloc[2])
st.markdown("---")

if selected_page == P_LEDGER:
    if "recap" not in st.session_state:
        with luxury_spinner("Analyst is reviewing portfolios..."): 
            st.session_state["recap"] = get_weekly_recap()
    st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ The Studio Report</h3>{st.session_state["recap"]}</div>', unsafe_allow_html=True)
    st.header("Weekly Transactions")
    m_col1, m_col2 = st.columns(2)
    for i, m in enumerate(matchup_data):
        current_col = m_col1 if i % 2 == 0 else m_col2
        with current_col:
            st.markdown(f"""<div class="luxury-card" style="padding: 15px; margin-bottom: 10px;"><div style="display: flex; justify-content: space-between; align-items: center;"><div style="text-align: center; width: 40%;"><img src="{m['Home Logo']}" width="50" style="border-radius: 50%; border: 2px solid #00C9FF; padding: 2px; box-shadow: 0 0 15px rgba(0, 201, 255, 0.4);"><div style="font-weight: 700; color: white; font-size: 0.9em; margin-top: 5px;">{m['Home']}</div><div style="font-size: 20px; color: #00C9FF; font-weight: 800;">{m['Home Score']}</div></div><div style="color: #a0aaba; font-size: 10px; font-weight: bold;">VS</div><div style="text-align: center; width: 40%;"><img src="{m['Away Logo']}" width="50" style="border-radius: 50%; border: 2px solid #92FE9D; padding: 2px; box-shadow: 0 0 15px rgba(146, 254, 157, 0.4);"><div style="font-weight: 700; color: white; font-size: 0.9em; margin-top: 5px;">{m['Away']}</div><div style="font-size: 20px; color: #00C9FF; font-weight: 800;">{m['Away Score']}</div></div></div></div>""", unsafe_allow_html=True)
            with st.expander(f"📉 View Lineups"):
                max_len = max(len(m['Home Roster']), len(m['Away Roster']))
                df_matchup = pd.DataFrame({
                    f"{m['Home']}": [p['Name'] for p in m['Home Roster']] + [''] * (max_len - len(m['Home Roster'])),
                    f"{m['Home']} Pts": [p['Score'] for p in m['Home Roster']] + [0] * (max_len - len(m['Home Roster'])),
                    "Pos": [p['Pos'] for p in m['Home Roster']] + [''] * (max_len - len(m['Home Roster'])),
                    f"{m['Away']} Pts": [p['Score'] for p in m['Away Roster']] + [0] * (max_len - len(m['Away Roster'])),
                    f"{m['Away']}": [p['Name'] for p in m['Away Roster']] + [''] * (max_len - len(m['Away Roster'])),
                })
                st.dataframe(df_matchup, use_container_width=True, hide_index=True, column_config={f"{m['Home']} Pts": st.column_config.NumberColumn(format="%.1f"), f"{m['Away']} Pts": st.column_config.NumberColumn(format="%.1f")})

elif selected_page == P_HIERARCHY:
    if "rank_comm" not in st.session_state:
        with luxury_spinner("Analyzing hierarchy..."): st.session_state["rank_comm"] = get_rankings_commentary()
    st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ Pundit\'s Take</h3>{st.session_state["rank_comm"]}</div>', unsafe_allow_html=True)
    st.header("Power Rankings")
    st.bar_chart(df_eff.set_index("Team")["Total Potential"], color="#00C9FF")

elif selected_page == P_AUDIT:
    st.header("Efficiency Audit")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_eff["Team"], y=df_eff["Starters"], name='Starters', marker_color='#00C9FF'))
    fig.add_trace(go.Bar(x=df_eff["Team"], y=df_eff["Bench"], name='Bench Waste', marker_color='rgba(255, 255, 255, 0.1)'))
    fig.update_layout(barmode='stack', plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aaba", title="Total Potential", height=500)
    st.plotly_chart(fig, use_container_width=True)
    if not df_bench_stars.empty: 
        st.markdown("#### 🚨 'Should Have Started'")
        st.dataframe(df_bench_stars, use_container_width=True, hide_index=True)

elif selected_page == P_HEDGE:
    st.header("Market Analytics")
    if "df_advanced" not in st.session_state:
        st.info("⚠️ Accessing historical market data requires intensive calculation.")
        if st.button("🚀 Analyze Market Data"):
            with luxury_spinner("Compiling Assets..."): st.session_state["df_advanced"] = calculate_heavy_analytics(current_week); st.rerun()
    else:
        df_advanced = st.session_state["df_advanced"]
        fig = px.scatter(df_advanced, x="Power Score", y="Wins", text="Team", size="Points For", color="Luck Rating", color_continuous_scale=["#7209b7", "#4361ee", "#4cc9f0"], title="Luck Matrix", height=600)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aaba")
        fig.update_traces(marker=dict(size=15, line=dict(width=2, color='White')), textposition='top center')
        st.plotly_chart(fig, use_container_width=True)

elif selected_page == P_LAB:
    st.header("🧬 The Lab (Next Gen Biometrics)")
    with st.expander("🔎 Biometric Legend (The Code)", expanded=False):
        st.markdown("""
        - 💎 **ELITE:** Top 10% performance in underlying metric (Separation/Efficiency).
        - 🚀 **MONSTER:** Incredible efficiency (YAC > Expected).
        - 🎯 **SNIPER:** Completion % > Expected (Highly Accurate).
        - ⚠️ **TRAP:** High Volume but Low Efficiency (Sell High Candidate).
        - 🚫 **PLODDER:** Inefficient rushing (Rushing Yards < Expected).
        - **Separation:** Yards of distance from nearest defender at catch.
        - **CPOE:** Completion Percentage Over Expectation.
        - **RYOE:** Rushing Yards Over Expectation (Line adjusted).
        - **WOPR:** Weighted Opportunity Rating (Target Share + Air Yards Share).
        - **8-Man Box:** Percentage of attempts against a stacked box (8+ defenders).
        - **Aggressiveness:** Percentage of attempts into tight windows (<1 yard separation).
        """)
    
    team_list = [t.team_name for t in league.teams]
    target_team = st.selectbox("Select Test Subject:", team_list)
    
    if st.button("🧪 Analyze Roster Efficiency"):
        if lottie_lab: st_lottie(lottie_lab, height=200)
        with luxury_spinner("Calibrating Tracking Satellites..."):
            roster_obj = next(t for t in league.teams if t.team_name == target_team).roster
            df_ngs = analyze_nextgen_metrics(roster_obj, year)
            st.session_state["ngs_data"] = df_ngs
            st.rerun()
            
    if "ngs_data" in st.session_state and not st.session_state["ngs_data"].empty:
        st.markdown("### 🔬 Biometric Results")
        df_res = st.session_state["ngs_data"]
        cols = st.columns(2)
        for i, row in df_res.iterrows():
            col = cols[i % 2]
            with col:
                st.markdown(f"""
                <div class="luxury-card" style="border-left: 4px solid #00C9FF; display: flex; align-items: center;">
                    <img src="https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{row['ID']}.png&w=80&h=60" 
                         style="border-radius: 8px; margin-right: 15px; border: 1px solid rgba(0, 201, 255, 0.3);">
                    <div style="flex: 1;">
                        <h4 style="margin:0; color: white; font-size: 1.1em;">{row['Player']}</h4>
                        <div style="font-size: 0.8em; color: #a0aaba;">{row['Team']} • {row['Position']}</div>
                        <div style="color: #00C9FF; font-weight: bold; font-size: 0.9em; margin-top: 4px;">{row['Verdict']}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 0.75em; color: #a0aaba;">{row['Metric']}</div>
                        <div style="font-size: 1.4em; font-weight: bold; color: white;">{row['Value']}</div>
                        <div style="font-size: 0.75em; color: #92FE9D;">{row['Alpha Stat']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    elif "ngs_data" in st.session_state:
        st.info("No Next Gen Data found for this roster (or API connection failed).")


elif selected_page == P_FORECAST:
    st.header("The Crystal Ball")
    if "playoff_odds" not in st.session_state:
        if st.button("🎲 Run Simulation"):
            with luxury_spinner("Running Monte Carlo simulations..."): st.session_state["playoff_odds"] = run_monte_carlo_simulation(); st.rerun()
    else:
        df_odds = st.session_state["playoff_odds"]
        st.dataframe(df_odds, use_container_width=True, hide_index=True, column_config={"Playoff Odds": st.column_config.ProgressColumn("Prob", format="%.1f%%", min_value=0, max_value=100)})
        if st.button("🔄 Re-Simulate"): del st.session_state["playoff_odds"]; st.rerun()

elif selected_page == P_NEXT:
    try:
        next_week = league.current_week
        next_box_scores = league.box_scores(week=next_week)
        games_list = []
        for game in next_box_scores:
            h_proj, a_proj = game.home_projected, game.away_projected
            if h_proj == 0: h_proj = 100
            if a_proj == 0: a_proj = 100
            spread = abs(h_proj - a_proj)
            games_list.append({"home": game.home_team.team_name, "away": game.away_team.team_name, "spread": f"{spread:.1f}"})
        if "next_week_commentary" not in st.session_state:
            with luxury_spinner("Checking Vegas lines..."): st.session_state["next_week_commentary"] = get_next_week_preview(games_list)
        st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ Vegas Insider</h3>{st.session_state["next_week_commentary"]}</div>', unsafe_allow_html=True)
        st.header("Next Week's Market Preview")
        nc1, nc2 = st.columns(2)
        for i, game in enumerate(next_box_scores):
            h_proj, a_proj = game.home_projected, game.away_projected
            if h_proj == 0: h_proj = 100
            if a_proj == 0: a_proj = 100
            spread = abs(h_proj - a_proj)
            fav = game.home_team.team_name if h_proj > a_proj else game.away_team.team_name
            curr_col = nc1 if i % 2 == 0 else nc2
            with curr_col:
                st.markdown(f"""<div class="luxury-card" style="padding: 15px;"><div style="display: flex; justify-content: space-between; align-items: center; text-align: center;"><div style="flex: 2;"><div style="font-weight: bold; font-size: 1.1em; color: #ffffff;">{game.home_team.team_name}</div><div style="color: #00C9FF; text-shadow: 0 0 8px rgba(0, 201, 255, 0.4);">Proj: {h_proj:.1f}</div></div><div style="flex: 1; color: #a0aaba; font-size: 0.8em;"><div>VS</div><div style="color: #00C9FF; margin-top: 5px;">Fav: {fav}</div><div style="color: #fff;">+{spread:.1f}</div></div><div style="flex: 2;"><div style="font-weight: bold; font-size: 1.1em; color: #ffffff;">{game.away_team.team_name}</div><div style="color: #92FE9D; text-shadow: 0 0 8px rgba(146, 254, 157, 0.4);">Proj: {a_proj:.1f}</div></div></div></div>""", unsafe_allow_html=True)
    except: st.info("Projections unavailable.")

elif selected_page == P_PROP:
    st.header("📊 The Prop Desk (Vegas vs. ESPN)")
    if not odds_api_key: st.warning("Please add 'odds_api_key' to your secrets.")
    else:
        if "vegas_data" not in st.session_state:
            with luxury_spinner("Calling the bookies in Las Vegas..."): st.session_state["vegas_data"] = get_vegas_props(odds_api_key)
        df_vegas = st.session_state["vegas_data"]
        if df_vegas is not None and not df_vegas.empty:
            if "Status" in df_vegas.columns and df_vegas.iloc[0]["Status"] == "Market Closed":
                st.markdown("""<div class="luxury-card" style="border-left: 4px solid #FFD700;"><h3 style="color: #FFD700; margin-top: 0;">🏦 Market Status: ADJUSTMENT PERIOD</h3><p style="color: #e0e0e0;"><strong>Why is this empty?</strong> It is early in the week. Major books pull player props on Tuesdays.</p></div>""", unsafe_allow_html=True)
            else:
                next_week = league.current_week
                box = league.box_scores(week=next_week)
                trust_data = []
                for game in box:
                    all_players = game.home_lineup + game.away_lineup
                    for player in all_players:
                        if player.slot_position == 'BE': continue
                        match, score, index = process.extractOne(player.name, df_vegas['Player'].tolist())
                        if score > 85:
                            vegas_pts = df_vegas[df_vegas['Player'] == match].iloc[0]['Vegas Score']
                            espn_pts = player.projected_points
                            if espn_pts == 0: espn_pts = 0.1
                            delta = vegas_pts - espn_pts
                            status = "🚀 SMASH (Vegas Higher)" if delta > 3 else "⚠️ TRAP (ESPN High)" if delta < -3 else "⚖️ Fair Value"
                            trust_data.append({"Player": player.name, "Team": player.proTeam, "ESPN Proj": espn_pts, "Vegas Implied": round(vegas_pts, 2), "Delta": round(delta, 2), "Verdict": status})
                if trust_data:
                    st.dataframe(pd.DataFrame(trust_data).sort_values(by="Delta", ascending=False), use_container_width=True, hide_index=True, column_config={"Delta": st.column_config.NumberColumn("Trust Delta", format="%+.1f")})
                else: st.info("No prop lines found yet.")
        else: st.error("Could not fetch odds.")

elif selected_page == P_DEAL:
    st.header("🤝 The AI Dealmaker")
    c1, c2 = st.columns(2)
    with c1: t1 = st.selectbox("Select Team A", [t.team_name for t in league.teams], index=0)
    with c2: t2 = st.selectbox("Select Team B", [t.team_name for t in league.teams], index=1)
    if st.button("🤖 Generate Trade"):
        with luxury_spinner("Analyzing roster deficiencies..."):
            team_a = next(t for t in league.teams if t.team_name == t1)
            team_b = next(t for t in league.teams if t.team_name == t2)
            # Full roster for trade machine
            r_a = [f"{p.name} ({p.position})" for p in team_a.roster]
            r_b = [f"{p.name} ({p.position})" for p in team_b.roster]
            proposal = get_ai_trade_proposal(t1, t2, r_a, r_b)
            st.markdown(f'<div class="luxury-card studio-box"><h3>Proposed Deal</h3>{proposal}</div>', unsafe_allow_html=True)

elif selected_page == P_DARK:
    st.header("🕵️ The Dark Pool (Waiver Wire)")
    if "dark_pool_data" not in st.session_state:
        if st.button("🔭 Scan Free Agents"):
            with luxury_spinner("Scouting the wire..."):
                df_pool = scan_dark_pool()
                st.session_state["dark_pool_data"] = df_pool
                if not df_pool.empty:
                    p_str = ", ".join([f"{r['Name']} ({r['Position']}, {r['Avg Pts']:.1f})" for i, r in df_pool.iterrows()])
                    st.session_state["scout_rpt"] = get_ai_scouting_report(p_str)
                else:
                    st.session_state["scout_rpt"] = "No viable assets found."
                st.rerun()
    else:
        if "scout_rpt" in st.session_state: st.markdown(f'<div class="luxury-card studio-box"><h3>📝 Scout\'s Notebook</h3>{st.session_state["scout_rpt"]}</div>', unsafe_allow_html=True)
        if not st.session_state["dark_pool_data"].empty:
            st.dataframe(st.session_state["dark_pool_data"], use_container_width=True, hide_index=True, column_config={"Avg Pts": st.column_config.NumberColumn(format="%.1f"), "Total Pts": st.column_config.NumberColumn(format="%.1f")})
        else:
            st.warning("⚠️ No players found.")
        if st.button("🔄 Rescan"): 
            del st.session_state["dark_pool_data"]
            if "scout_rpt" in st.session_state: del st.session_state["scout_rpt"]
            st.rerun()

elif selected_page == P_TROPHY:
    if "awards" not in st.session_state:
        if st.button("🏅 Unveil Awards"):
            with luxury_spinner("Engraving trophies..."):
                st.session_state["awards"] = calculate_season_awards(current_week)
                st.session_state["season_comm"] = get_season_retrospective(st.session_state['awards']['MVP']['Name'], st.session_state['awards']['Best Manager']['Team'])
                st.rerun()
    else:
        awards = st.session_state["awards"]
        if "season_comm" in st.session_state:
             st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ State of the League</h3>{st.session_state["season_comm"]}</div>', unsafe_allow_html=True)
        st.divider(); st.header("Season Awards")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="luxury-card award-card"><h3>👑 MVP</h3></div>', unsafe_allow_html=True)
            if awards['MVP']:
                p = awards['MVP']
                st.image(f"https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{p['ID']}.png&w=350&h=254", width=150)
                st.metric(label=p['Name'], value=f"{p['Points']:.1f} pts")
        with c2:
            st.markdown('<div class="luxury-card award-card"><h3>🐋 The Whale</h3></div>', unsafe_allow_html=True)
            mgr = awards['Best Manager']
            st.image(mgr['Logo'], width=100)
            st.metric(label=mgr['Team'], value=f"{mgr['Points']:.1f} pts")
        st.divider()
        c3, c4, c5 = st.columns(3)
        with c3:
            st.markdown("#### 💔 Heartbreaker"); hb = awards['Heartbreaker']
            st.metric(label=f"{hb['Loser']} lost by", value=f"{hb['Margin']:.2f} pts")
        with c4:
            st.markdown("#### 🔥 The Streak"); stk = awards['Streak']
            st.metric(label=stk['Team'], value=f"{stk['Length']} Games")
        with c5:
            st.markdown("#### 💤 Asleep at Wheel"); slp = awards['Sleeper']
            st.metric(label=slp['Team'], value=f"{slp['Count']} Players")
            
elif selected_page == P_VAULT:
    st.header("⏳ The Dynasty Vault (All-Time History)")
    st.caption(f"Tracking league history from {START_YEAR} to Present.")
    if "dynasty_leaderboard" not in st.session_state:
        if st.button("🔓 Unlock The Vault"):
            with luxury_spinner(f"Traveling back to {START_YEAR}..."):
                df_raw = get_dynasty_data(year, START_YEAR)
                st.session_state["dynasty_raw"] = df_raw
                st.session_state["dynasty_leaderboard"] = process_dynasty_leaderboard(df_raw)
                st.rerun()
    else:
        st.subheader("🏛️ All-Time Leaderboard")
        df_lead = st.session_state["dynasty_leaderboard"]
        st.dataframe(df_lead, use_container_width=True, hide_index=True, column_config={"Manager": st.column_config.TextColumn("Manager", width="medium"), "Win %": st.column_config.ProgressColumn("Win %", format="%.1f%%", min_value=0, max_value=100), "Champ": st.column_config.NumberColumn("🏆 Rings"), "Playoffs": st.column_config.NumberColumn("🎟️ Playoff Apps"), "Points For": st.column_config.NumberColumn("Total Pts", format="%.0f")})
        st.subheader("📉 Empire History")
        df_chart = st.session_state["dynasty_raw"]
        fig = px.line(df_chart, x="Year", y="Wins", color="Manager", markers=True, title="The Rise and Fall of Empires")
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aaba", xaxis=dict(tickmode='linear', tick0=START_YEAR, dtick=1))
        st.plotly_chart(fig, use_container_width=True)
else:
    st.error(f"Page Not Found: {selected_page}. Please check page definitions.")
