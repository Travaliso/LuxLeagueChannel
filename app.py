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
# 7. DASHBOARD UI
# ------------------------------------------------------------------
st.title(f"🏛️ Luxury League Protocol: Week {selected_week}")

col_main, col_players = st.columns([2, 1])
with col_players:
    st.markdown("### 🌟 Weekly Elite")
    for i, (idx, p) in enumerate(df_players.head(3).iterrows()):
         st.markdown(f"""
            <div style="display: flex; align-items: center; background: #151922; border-radius: 8px; padding: 5px; margin-bottom: 5px; border: 1px solid #333;">
                <img src="https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{p['ID']}.png&w=60&h=44" style="border-radius: 5px; margin-right: 10px;">
                <div>
                    <div style="color: #00C9FF; font-weight: bold; font-size: 14px;">{p['Name']}</div>
                    <div style="color: #fff; font-size: 12px;">{p['Points']} pts</div>
                </div>
            </div>""", unsafe_allow_html=True)

if selected_page == P_LEDGER:
    if "recap" not in st.session_state:
        with st.spinner("🎙️ Analyst is reviewing portfolios..."): st.session_state["recap"] = get_weekly_recap()
    with col_main:
        st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ The Studio Report</h3>{st.session_state["recap"]}</div>', unsafe_allow_html=True)
    st.divider(); st.header("Weekly Transactions")
    for m in matchup_data:
        st.markdown(f"""<div class="luxury-card"><div style="display: flex; justify-content: space-between; align-items: center;"><div style="text-align: center; width: 40%;"><img src="{m['Home Logo']}" width="60" style="border-radius: 50%; border: 2px solid #00C9FF; padding: 2px;"><div style="font-weight: bold; color: white; margin-top: 5px;">{m['Home']}</div><div style="font-size: 24px; color: #00C9FF; text-shadow: 0 0 10px rgba(0,201,255,0.5);">{m['Home Score']}</div></div><div style="color: #a0aaba; font-size: 14px; font-weight: bold;">VS</div><div style="text-align: center; width: 40%;"><img src="{m['Away Logo']}" width="60" style="border-radius: 50%; border: 2px solid #0072ff; padding: 2px;"><div style="font-weight: bold; color: white; margin-top: 5px;">{m['Away']}</div><div style="font-size: 24px; color: #00C9FF; text-shadow: 0 0 10px rgba(0,201,255,0.5);">{m['Away Score']}</div></div></div></div>""", unsafe_allow_html=True)
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
    if "rankings_commentary" not in st.session_state:
        with st.spinner("Analyzing hierarchy..."): st.session_state["rankings_commentary"] = get_rankings_commentary()
    with col_main: st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ Pundit\'s Take</h3>{st.session_state["rankings_commentary"]}</div>', unsafe_allow_html=True)
    st.divider(); st.header("Power Rankings"); st.bar_chart(df_eff.set_index("Team")["Total Potential"], color="#00C9FF")

elif selected_page == P_AUDIT:
    with col_main: st.header("Efficiency Audit")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_eff["Team"], y=df_eff["Starters"], name='Starters', marker_color='#00C9FF'))
    fig.add_trace(go.Bar(x=df_eff["Team"], y=df_eff["Bench"], name='Bench Waste', marker_color='#2c313a'))
    fig.update_layout(barmode='stack', plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aaba", title="Total Potential")
    st.plotly_chart(fig, use_container_width=True)
    if not df_bench_stars.empty: st.markdown("#### 🚨 'Should Have Started'"); st.dataframe(df_bench_stars, use_container_width=True, hide_index=True)

elif selected_page == P_HEDGE:
    with col_main: st.header("Market Analytics")
    if "df_advanced" not in st.session_state:
        st.info("⚠️ Accessing historical market data requires intensive calculation.")
        if st.button("🚀 Analyze Market Data"):
            with st.spinner("Compiling Assets..."): st.session_state["df_advanced"] = calculate_heavy_analytics(current_week); st.rerun()
    else:
        df_advanced = st.session_state["df_advanced"]
        fig = px.scatter(df_advanced, x="Power Score", y="Wins", text="Team", size="Points For", color="Luck Rating", color_continuous_scale=["#0072ff", "#1a1c24", "#00C9FF"], title="Luck Matrix")
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aaba")
        st.plotly_chart(fig, use_container_width=True)

elif selected_page == P_FORECAST:
    with col_main: st.header("The Crystal Ball")
    if "playoff_odds" not in st.session_state:
        if st.button("🎲 Run Simulation"):
            if lottie_forecast: st_lottie(lottie_forecast, height=200)
            with st.spinner("Crunching probabilities..."): st.session_state["playoff_odds"] = run_monte_carlo_simulation(); st.rerun()
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
            with st.spinner("Checking Vegas lines..."): st.session_state["next_week_commentary"] = get_next_week_preview(games_list)
        with col_main: st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ Vegas Insider</h3>{st.session_state["next_week_commentary"]}</div>', unsafe_allow_html=True)
        st.divider(); st.header("Next Week's Market Preview")
        for game in next_box_scores:
            h_proj, a_proj = game.home_projected, game.away_projected
            if h_proj == 0: h_proj = 100
            if a_proj == 0: a_proj = 100
            spread = abs(h_proj - a_proj)
            fav = game.home_team.team_name if h_proj > a_proj else game.away_team.team_name
            st.markdown(f"""<div class="luxury-card" style="padding: 15px;"><div style="display: flex; justify-content: space-between; align-items: center; text-align: center;"><div style="flex: 2;"><div style="font-weight: bold; font-size: 1.1em;">{game.home_team.team_name}</div><div style="color: #00C9FF;">Proj: {h_proj:.1f}</div></div><div style="flex: 1; color: #a0aaba; font-size: 0.9em;"><div>VS</div><div style="color: #00C9FF;">Fav: {fav} (+{spread:.1f})</div></div><div style="flex: 2;"><div style="font-weight: bold; font-size: 1.1em;">{game.away_team.team_name}</div><div style="color: #00C9FF;">Proj: {a_proj:.1f}</div></div></div></div>""", unsafe_allow_html=True)
    except: st.info("Projections unavailable.")

elif selected_page == P_DEAL:
    st.header("🤝 The AI Dealmaker")
    st.caption("Select two teams to have the AI negotiate a mutually beneficial trade.")
    col_a, col_b = st.columns(2)
    with col_a: team_a_name = st.selectbox("Select Team A", [t.team_name for t in league.teams], index=0)
    with col_b: team_b_name = st.selectbox("Select Team B", [t.team_name for t in league.teams], index=1)
    if st.button("🤖 Generate Trade Proposal"):
        if lottie_trade: st_lottie(lottie_trade, height=200)
        with st.spinner("Analyzing roster deficiencies and surplus..."):
            team_a = next(t for t in league.teams if t.team_name == team_a_name)
            team_b = next(t for t in league.teams if t.team_name == team_b_name)
            roster_a = [f"{p.name} ({p.position})" for p in team_a.roster]
            roster_b = [f"{p.name} ({p.position})" for p in team_b.roster]
            proposal = get_ai_trade_proposal(team_a_name, team_b_name, roster_a, roster_b)
            st.markdown(f'<div class="luxury-card studio-box"><h3>🤝 Proposed Deal</h3>{proposal}</div>', unsafe_allow_html=True)

elif selected_page == P_DARK:
    st.header("🕵️ The Dark Pool (Waiver Wire)")
    st.caption("Scouting available free agents for breakout potential.")
    if "dark_pool_data" not in st.session_state:
        if st.button("🔭 Scan Free Agents"):
            if lottie_wire: st_lottie(lottie_wire, height=200)
            with st.spinner("Scouting the wire..."):
                df_pool = scan_dark_pool()
                st.session_state["dark_pool_data"] = df_pool
                if not df_pool.empty:
                    pool_str = ", ".join([f"{r['Name']} ({r['Position']}, {r['Avg Pts']:.1f} avg)" for i, r in df_pool.iterrows()])
                    st.session_state["scouting_report"] = get_ai_scouting_report(pool_str)
                st.rerun()
    else:
        df_pool = st.session_state["dark_pool_data"]
        if "scouting_report" in st.session_state:
            st.markdown(f'<div class="luxury-card studio-box"><h3>📝 Scout\'s Notebook</h3>{st.session_state["scouting_report"]}</div>', unsafe_allow_html=True)
        if not df_pool.empty:
            st.dataframe(df_pool, use_container_width=True, hide_index=True, column_config={"Avg Pts": st.column_config.NumberColumn(format="%.1f"), "Total Pts": st.column_config.NumberColumn(format="%.1f")})
            if st.button("🔄 Rescan Wire"): del st.session_state["dark_pool_data"]; st.rerun()
        else: st.info("No viable free agents found (or API limit reached).")

elif selected_page == P_TROPHY:
    if "awards" not in st.session_state:
        if st.button("🏅 Unveil Yearly Awards"):
            if lottie_trophy: st_lottie(lottie_trophy, height=200)
            with st.spinner("Engraving trophies..."):
                st.session_state["awards"] = calculate_season_awards(current_week)
                awards = st.session_state["awards"]
                mvp_name = awards['MVP']['Name'] if awards['MVP'] else "N/A"
                best_mgr_name = awards['Best Manager']['Team']
                st.session_state["season_commentary"] = get_season_retrospective(mvp_name, best_mgr_name)
                st.rerun()
    else:
        awards = st.session_state["awards"]
        if "season_commentary" in st.session_state:
             with col_main: st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ State of the League</h3>{st.session_state["season_commentary"]}</div>', unsafe_allow_html=True)
        st.divider(); st.header("Season Awards")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="luxury-card award-card"><h3>👑 MVP (Best Player)</h3></div>', unsafe_allow_html=True)
            if awards['MVP']:
                p = awards['MVP']
                st.image(f"https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{p['ID']}.png&w=350&h=254", width=150)
                st.metric(label=p['Name'], value=f"{p['Points']:.1f} pts", delta="Season Total")
        with c2:
            st.markdown('<div class="luxury-card award-card"><h3>🐋 The Whale (Best Mgr)</h3></div>', unsafe_allow_html=True)
            mgr = awards['Best Manager']
            st.image(mgr['Logo'], width=100)
            st.metric(label=mgr['Team'], value=f"{mgr['Points']:.1f} pts", delta="Total Points For")
        st.divider()
        c3, c4, c5 = st.columns(3)
        with c3:
            st.markdown("#### 💔 Heartbreaker"); st.caption("Smallest Margin of Defeat"); hb = awards['Heartbreaker']
            st.metric(label=f"{hb['Loser']} lost by", value=f"{hb['Margin']:.2f} pts", delta=f"Week {hb['Week']}")
        with c4:
            st.markdown("#### 🔥 The Streak"); st.caption("Longest Win Streak"); stk = awards['Streak']
            st.metric(label=stk['Team'], value=f"{stk['Length']} Games", delta="Undefeated Run")
        with c5:
            st.markdown("#### 💤 Asleep at Wheel"); st.caption("Starters with 0.0 Pts"); slp = awards['Sleeper']
            st.metric(label=slp['Team'], value=f"{slp['Count']} Players", delta="Wasted Starts")
else:
    st.error("Page Not Found. Please check logic.")
