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

# ------------------------------------------------------------------
# 1. CONFIGURATION & NEON LUXURY CSS
# ------------------------------------------------------------------
st.set_page_config(page_title="Luxury League Dashboard", page_icon="🏈", layout="wide")

st.markdown("""
    <style>
    /* MAIN BACKGROUND */
    .stApp { background-color: #080a10; }

    /* NEON GRADIENT HEADINGS */
    h1, h2, h3, h4 {
        background: linear-gradient(90deg, #00C9FF, #0072ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 800 !important;
        letter-spacing: 1px;
    }

    /* METRIC NUMBERS */
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
        color: #00C9FF !important;
        text-shadow: 0 0 10px rgba(0, 201, 255, 0.3);
    }
    div[data-testid="stMetricLabel"] { color: #a0aaba !important; }

    /* LUXURY CARD STYLING */
    .luxury-card {
        background: linear-gradient(145deg, #151922, #1a1c24);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 15px;
        border: 1px solid rgba(0, 201, 255, 0.1);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    }
    .award-card { border-left: 4px solid #00C9FF; }
    .studio-box { border-left: 4px solid #0072ff; }

    /* SIDEBAR NAVIGATION */
    section[data-testid="stSidebar"] { background-color: #0e1117; border-right: 1px solid #333; }
    div[data-testid="stRadio"] > label { color: #a0aaba !important; font-weight: bold; }
    div[role="radiogroup"] label { padding: 10px; border-radius: 8px; transition: background-color 0.3s; }
    div[role="radiogroup"] label:hover { background-color: rgba(0, 201, 255, 0.1); color: #00C9FF !important; }
    
    /* DATAFRAME */
    div[data-testid="stDataFrame"] { background-color: #151922; border-radius: 12px; padding: 10px; }
    </style>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------------
# 2. CONNECTION & SETUP
# ------------------------------------------------------------------
def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200: return None
        return r.json()
    except: return None

lottie_loading = load_lottieurl("https://lottie.host/5a882010-89b6-45bc-8a4d-06886982f8d8/WfK7bXoGqj.json")
lottie_forecast = load_lottieurl("https://lottie.host/936c69f6-0b89-4b68-b80c-0390f777c5d7/C0Z2y3S0bM.json")
lottie_trophy = load_lottieurl("https://lottie.host/362e7839-2425-4c75-871d-534b82d02c84/hL9w4jR9aF.json")
lottie_trade = load_lottieurl("https://lottie.host/e65893a7-e54e-4f0b-9366-0749024f2b1d/z2Xg6c4h5r.json")
lottie_wire = load_lottieurl("https://lottie.host/4e532997-5b65-4f4c-8b2b-077555627798/7Q9j7Z9g9z.json")

try:
    league_id = st.secrets["league_id"]
    swid = st.secrets["swid"]
    espn_s2 = st.secrets["espn_s2"]
    openai_key = st.secrets.get("openai_key")
    year = 2025

    @st.cache_resource
    def get_league():
        return League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)

    league = get_league()

except Exception as e:
    st.error(f"🔒 Connection Error: {e}")
    st.stop()

# ------------------------------------------------------------------
# 3. ANALYTICS ENGINES
# ------------------------------------------------------------------

# --- A. Historical Analytics ---
@st.cache_data(ttl=3600)
def calculate_heavy_analytics(current_week):
    data_rows = []
    for team in league.teams:
        power_score = round(team.points_for / current_week, 1)
        true_wins = 0
        total_matchups = 0
        for w in range(1, current_week + 1):
            box = league.box_scores(week=w)
            my_score = next((g.home_score if g.home_team == team else g.away_score 
                             for g in box if g.home_team == team or g.away_team == team), 0)
            all_scores = [g.home_score for g in box] + [g.away_score for g in box]
            wins_this_week = sum(1 for s in all_scores if my_score > s)
            true_wins += wins_this_week
            total_matchups += (len(league.teams) - 1)

        true_win_pct = true_wins / total_matchups if total_matchups > 0 else 0
        actual_win_pct = team.wins / (team.wins + team.losses + 0.001)
        luck_rating = (actual_win_pct - true_win_pct) * 10
        
        data_rows.append({
            "Team": team.team_name, "Wins": team.wins, "Points For": team.points_for,
            "Power Score": power_score, "Luck Rating": luck_rating, "True Win %": true_win_pct
        })
    return pd.DataFrame(data_rows)

# --- B. Season Awards Engine ---
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

# --- C. Monte Carlo Simulator ---
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
        if odds > 99: reason = "🔒 Locked."
        elif odds > 80: reason = "🚀 High Prob."
        elif odds > 40: reason = "⚖️ Bubble."
        elif odds > 5: reason = "🙏 Miracle."
        else: reason = "💀 Dead."
        final_output.append({"Team": team.team_name, "Playoff Odds": odds, "Note": reason})
        
    return pd.DataFrame(final_output).sort_values(by="Playoff Odds", ascending=False)

# --- D. Dark Pool (Robust Scanner) ---
@st.cache_data(ttl=3600)
def scan_dark_pool(limit=15):
    free_agents = league.free_agents(size=50)
    pool_data = []
    for player in free_agents:
        try:
            # Fallback logic: Use Total Points OR Projected if Total is missing
            total = player.total_points if player.total_points > 0 else player.projected_total_points
            avg_pts = total / league.current_week if league.current_week > 0 else 0
            
            if avg_pts > 3: # Lower threshold to ensure we catch players
                pool_data.append({
                    "Name": player.name, "Position": player.position, "Team": player.proTeam,
                    "Avg Pts": avg_pts, "Total Pts": total, "ID": player.playerId
                })
        except: continue
            
    df = pd.DataFrame(pool_data)
    if not df.empty: df = df.sort_values(by="Avg Pts", ascending=False).head(limit)
    return df

# ------------------------------------------------------------------
# 4. SIDEBAR NAVIGATION (FIXED MAPPING)
# ------------------------------------------------------------------
st.sidebar.title("🥂 The Concierge")
current_week = league.current_week - 1
if current_week == 0: current_week = 1
selected_week = st.sidebar.slider("Select Week", 1, current_week, current_week)
st.sidebar.markdown("---")

# PAGE DEFINITIONS (Ensures logic matches UI exactly)
P_LEDGER = "📜 The Ledger"
P_HIERARCHY = "📈 The Hierarchy"
P_AUDIT = "🔎 The Audit"
P_HEDGE = "💎 The Hedge Fund"
P_FORECAST = "🔮 The Forecast"
P_NEXT = "🚀 Next Week"
P_DEAL = "🤝 The Dealmaker"
P_DARK = "🕵️ The Dark Pool"
P_TROPHY = "🏆 Trophy Room"

page_options = [P_LEDGER, P_HIERARCHY, P_AUDIT, P_HEDGE, P_FORECAST, P_NEXT, P_DEAL, P_DARK, P_TROPHY]
selected_page = st.sidebar.radio("Navigation", page_options, label_visibility="collapsed")

# ------------------------------------------------------------------
# 5. DATA LOADING & PROCESSING
# ------------------------------------------------------------------
if 'box_scores' not in st.session_state or st.session_state.get('week') != selected_week:
    if lottie_loading: st_lottie(lottie_loading, height=200, key="loading")
    st.session_state['box_scores'] = league.box_scores(week=selected_week)
    st.session_state['week'] = selected_week
    st.rerun()

box_scores = st.session_state['box_scores']
matchup_data = []
efficiency_data = [] 
all_active_players = []
bench_highlights = []

for game in box_scores:
    home, away = game.home_team, game.away_team
    def get_roster_data(lineup, team_name):
        starters, bench, p_start, p_bench = [], [], 0, 0
        for p in lineup:
            info = {"Name": p.name, "Score": p.points, "Pos": p.slot_position}
            if p.slot_position == 'BE':
                bench.append(info); p_bench += p.points
                if p.points > 15: bench_highlights.append({"Team": team_name, "Player": p.name, "Score": p.points})
            else:
                starters.append(info); p_start += p.points
                all_active_players.append({"Name": p.name, "Points": p.points, "Team": team_name, "ID": p.playerId})
        return starters, bench, p_start, p_bench

    h_r, h_br, h_s, h_b = get_roster_data(game.home_lineup, home.team_name)
    a_r, a_br, a_s, a_b = get_roster_data(game.away_lineup, away.team_name)
    matchup_data.append({"Home": home.team_name, "Home Score": game.home_score, "Home Logo": home.logo_url, "Home Roster": h_r, "Away": away.team_name, "Away Score": game.away_score, "Away Logo": away.logo_url, "Away Roster": a_r})
    efficiency_data.append({"Team": home.team_name, "Starters": h_s, "Bench": h_b, "Total Potential": h_s + h_b})
    efficiency_data.append({"Team": away.team_name, "Starters": a_s, "Bench": a_b, "Total Potential": a_s + a_b})

df_eff = pd.DataFrame(efficiency_data).sort_values(by="Total Potential", ascending=False)
df_players = pd.DataFrame(all_active_players).sort_values(by="Points", ascending=False).head(5)
df_bench_stars = pd.DataFrame(bench_highlights).sort_values(by="Score", ascending=False).head(5)

# ------------------------------------------------------------------
# 6. AI HELPERS
# ------------------------------------------------------------------
def get_openai_client():
    if not openai_key: return None
    return OpenAI(api_key=openai_key)

def get_weekly_recap():
    client = get_openai_client()
    if not client: return "⚠️ Add 'openai_key' to secrets."
    top_scorer = df_eff.iloc[0]['Team']
    prompt = f"Write a DETAILED, 5-10 sentence fantasy recap for Week {selected_week}. Highlight the Powerhouse: {top_scorer}. Go into detail about the matchups. Style: Wall Street Report. Do not be brief."
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=800).choices[0].message.content
    except: return "Analyst Offline."

def get_rankings_commentary():
    client = get_openai_client()
    if not client: return "⚠️ Analyst Offline."
    top = df_eff.iloc[0]['Team']
    bottom = df_eff.iloc[-1]['Team']
    prompt = f"Write a 5-8 sentence commentary on the Power Rankings. Praise the #1 team {top} and ruthlessly mock the last place team {bottom}. Analyze why the bottom team is failing. Style: Stephen A. Smith / Hot Take."
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=600).choices[0].message.content
    except: return "Analyst Offline."

def get_next_week_preview(games_list):
    client = get_openai_client()
    if not client: return "⚠️ Analyst Offline."
    matchups_str = ", ".join([f"{g['home']} vs {g['away']} (Spread: {g['spread']})" for g in games_list])
    prompt = f"Act as a Vegas Sports Bookie. Provide a DETAILED breakdown (5-10 sentences) of next week's matchups: {matchups_str}. Pick one 'Lock of the Week' and one 'Upset Alert' and explain WHY with data."
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=800).choices[0].message.content
    except: return "Analyst Offline."

def get_season_retrospective(mvp, best_mgr):
    client = get_openai_client()
    if not client: return "⚠️ Analyst Offline."
    prompt = f"Write a comprehensive 'State of the Union' address (8-12 sentences) for the Fantasy League. MVP is {mvp}. Best Manager is {best_mgr}. Reflect on the season's glory, the tragedies, and the future. Style: Presidential / Epic."
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=1000).choices[0].message.content
    except: return "Analyst Offline."

def get_ai_trade_proposal(team_a, team_b, roster_a, roster_b):
    client = get_openai_client()
    if not client: return "⚠️ Analyst Offline."
    prompt = f"""
    Act as a high-stakes Trade Broker. Analyze these two rosters and propose a fair, win-win trade.
    
    Team A ({team_a}): {', '.join(roster_a)}
    Team B ({team_b}): {', '.join(roster_b)}
    
    Identify surplus/needs for both. Suggest a specific player-for-player swap. Explain the 'Why' for both sides.
    Style: Jerry Maguire / Wolf of Wall Street.
    """
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=600).choices[0].message.content
    except: return "Analyst Offline."

def get_ai_scouting_report(free_agents_str):
    client = get_openai_client()
    if not client: return "⚠️ Analyst Offline."
    prompt = f"""
    You are an elite NFL Talent Scout. Here is a list of available free agents (The Dark Pool):
    {free_agents_str}
    
    Identify 3 "Must Add" players.
    For each, provide a 1-sentence "Scouting Report" on why they are a hidden gem (e.g. recent volume, injury opportunity).
    Style: Scouting Notebook (Gritty, technical).
    """
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=500).choices[0].message.content
    except: return "Analyst Offline."

# ------------------------------------------------------------------
# 7. DASHBOARD
