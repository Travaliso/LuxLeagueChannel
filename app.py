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
# 1. CONFIGURATION
# ------------------------------------------------------------------
st.set_page_config(page_title="Luxury League", page_icon="🥂", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    h1, h2, h3 {
        background: -webkit-linear-gradient(45deg, #FFD700, #FDB931);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 800 !important;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        color: #FFD700 !important;
    }
    .studio-box {
        background-color: #1e2130;
        border-left: 5px solid #FFD700;
        padding: 20px;
        border-radius: 5px;
        margin-bottom: 20px;
        color: #e0e0e0;
    }
    /* Gold Border Card for Awards */
    .award-card {
        border: 1px solid #FFD700;
        background-color: #1a1c24;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 10px;
    }
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

# --- A. Historical Analytics (Hedge Fund) ---
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

# --- B. Season Awards Engine (Trophy Room) ---
@st.cache_data(ttl=3600)
def calculate_season_awards(current_week):
    # Trackers
    player_points = {} 
    team_bench_points = {t.team_name: 0 for t in league.teams}
    
    # New Award Trackers
    single_game_high = {"Team": "", "Score": 0, "Week": 0}
    biggest_blowout = {"Winner": "", "Loser": "", "Margin": 0, "Week": 0}
    heartbreaker = {"Winner": "", "Loser": "", "Margin": 999, "Week": 0} # Smallest loss
    
    # Streak Tracking
    current_streaks = {t.team_name: 0 for t in league.teams}
    max_streaks = {t.team_name: 0 for t in league.teams}
    
    # Asleep at the Wheel (0 points in starting lineup)
    asleep_count = {t.team_name: 0 for t in league.teams}
    
    for w in range(1, current_week + 1):
        box = league.box_scores(week=w)
        for game in box:
            h_name = game.home_team.team_name
            a_name = game.away_team.team_name
            
            # 1. Margins & Streaks
            margin = abs(game.home_score - game.away_score)
            
            # Determine Winner/Loser
            if game.home_score > game.away_score:
                winner, loser = h_name, a_name
            else:
                winner, loser = a_name, h_name
                
            # Update Streaks
            current_streaks[winner] += 1
            current_streaks[loser] = 0 # Reset loser streak
            if current_streaks[winner] > max_streaks[winner]:
                max_streaks[winner] = current_streaks[winner]
            
            # Check Blowout
            if margin > biggest_blowout["Margin"]:
                biggest_blowout = {"Winner": winner, "Loser": loser, "Margin": margin, "Week": w}
                
            # Check Heartbreaker (Smallest Margin)
            if margin < heartbreaker["Margin"]:
                heartbreaker = {"Winner": winner, "Loser": loser, "Margin": margin, "Week": w}
            
            # Check Max Score
            if game.home_score > single_game_high["Score"]:
                single_game_high = {"Team": h_name, "Score": game.home_score, "Week": w}
            if game.away_score > single_game_high["Score"]:
                single_game_high = {"Team": a_name, "Score": game.away_score, "Week": w}
                
            # 2. Player Stats (MVP & Asleep at Wheel)
            def process_roster(lineup, team_name):
                for p in lineup:
                    # MVP Tracking
                    if p.playerId not in player_points:
                        player_points[p.playerId] = {"Name": p.name, "Points": 0, "Owner": team_name, "ID": p.playerId}
                    player_points[p.playerId]["Points"] += p.points
                    
                    # Bench Points
                    if p.slot_position == 'BE':
                        team_bench_points[team_name] += p.points
                    else:
                        # Asleep at Wheel Check (Started with 0 points - Proxy for Bye/Inactive/Dud)
                        if p.points == 0:
                            asleep_count[team_name] += 1

            process_roster(game.home_lineup, h_name)
            process_roster(game.away_lineup, a_name)
            
    # Finalize Winners
    sorted_players = sorted(player_points.values(), key=lambda x: x['Points'], reverse=True)
    mvp = sorted_players[0] if sorted_players else None
    
    sorted_bench = sorted(team_bench_points.items(), key=lambda x: x[1], reverse=True)
    bench_king = sorted_bench[0] if sorted_bench else None
    
    sorted_teams = sorted(league.teams, key=lambda x: x.points_for, reverse=True)
    best_manager = sorted_teams[0]
    
    # Sort Streaks
    longest_streak_team = max(max_streaks, key=max_streaks.get)
    longest_streak_val = max_streaks[longest_streak_team]
    
    # Sort Sleepers
    sleepiest_team = max(asleep_count, key=asleep_count.get)
    sleepiest_val = asleep_count[sleepiest_team]
    
    return {
        "MVP": mvp,
        "Bench King": bench_king,
        "Single Game": single_game_high,
        "Blowout": biggest_blowout,
        "Heartbreaker": heartbreaker,
        "Streak": {"Team": longest_streak_team, "Length": longest_streak_val},
        "Sleeper": {"Team": sleepiest_team, "Count": sleepiest_val},
        "Best Manager": {"Team": best_manager.team_name, "Points": best_manager.points_for, "Logo": best_manager.logo_url}
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
    avg_league_power = sum(team_power.values()) / len(team_power)
    schedule_difficulty = {t.team_id: [] for t in league.teams}
    
    if current_w <= reg_season_end:
        for w in range(current_w, reg_season_end + 1):
            future_box = league.box_scores(week=w)
            for game in future_box:
                h, a = game.home_team, game.away_team
                schedule_difficulty[h.team_id].append(team_power[a.team_id])
                schedule_difficulty[a.team_id].append(team_power[h.team_id])
    
    results = {t.team_name: 0 for t in league.teams}
    
    for i in range(simulations):
        sim_standings = {k: v.copy() for k, v in team_data.items()}
        if current_w <= reg_season_end:
             for w in range(current_w, reg_season_end + 1):
                 for tid, stats in sim_standings.items():
                     power = team_power[tid]
                     performance = np.random.normal(power, 15)
                     if performance > 115: sim_standings[tid]["wins"] += 1

        sorted_teams = sorted(sim_standings.values(), key=lambda x: (x["wins"], x["points"]), reverse=True)
        top_teams = [t["name"] for t in sorted_teams[:num_playoff_teams]]
        for name in top_teams: results[name] += 1

    final_output = []
    for team in league.teams:
        tid = team.team_id
        odds = (results[team.team_name] / simulations) * 100
        opponents_scores = schedule_difficulty[tid]
        avg_opp_strength = sum(opponents_scores) / len(opponents_scores) if opponents_scores else avg_league_power
        my_power = team_power[tid]
        diff = my_power - avg_opp_strength
        
        if odds > 99: reason = "🔒 Locked."
        elif odds > 80: reason = "🚀 High Prob."
        elif odds > 40: reason = "⚖️ Bubble."
        elif odds > 5: reason = "🙏 Miracle."
        else: reason = "💀 Dead."
            
        final_output.append({"Team": team.team_name, "Playoff Odds": odds, "Note": reason})
        
    return pd.DataFrame(final_output).sort_values(by="Playoff Odds", ascending=False)

# ------------------------------------------------------------------
# 4. INITIAL LOADING
# ------------------------------------------------------------------
st.sidebar.title("🥂 The Concierge")
current_week = league.current_week - 1
if current_week == 0: current_week = 1
selected_week = st.sidebar.slider("Select Week", 1, current_week, current_week)

if 'box_scores' not in st.session_state or st.session_state.get('week') != selected_week:
    if lottie_loading: st_lottie(lottie_loading, height=200, key="loading")
    st.session_state['box_scores'] = league.box_scores(week=selected_week)
    st.session_state['week'] = selected_week
    st.rerun()

box_scores = st.session_state['box_scores']

# ------------------------------------------------------------------
# 5. DATA PROCESSING
# ------------------------------------------------------------------
matchup_data = []
efficiency_data = [] 
all_active_players = []
bench_highlights = []

for game in box_scores:
    home = game.home_team
    away = game.away_team
    
    def get_roster_data(lineup, team_name):
        starters, bench = [], []
        p_start, p_bench = 0, 0
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
    
    matchup_data.append({
        "Home": home.team_name, "Home Score": game.home_score, "Home Logo": home.logo_url, "Home Roster": h_r,
        "Away": away.team_name, "Away Score": game.away_score, "Away Logo": away.logo_url, "Away Roster": a_r
    })
    
    efficiency_data.append({"Team": home.team_name, "Starters": h_s, "Bench": h_b, "Total Potential": h_s + h_b})
    efficiency_data.append({"Team": away.team_name, "Starters": a_s, "Bench": a_b, "Total Potential": a_s + a_b})

df_eff = pd.DataFrame(efficiency_data).sort_values(by="Total Potential", ascending=False)
df_players = pd.DataFrame(all_active_players).sort_values(by="Points", ascending=False).head(5)
df_bench_stars = pd.DataFrame(bench_highlights).sort_values(by="Score", ascending=False).head(5)

# ------------------------------------------------------------------
# 6. AI NARRATIVE
# ------------------------------------------------------------------
def get_ai_recap():
    if not openai_key: return "⚠️ Add 'openai_key' to secrets."
    top_scorer = df_eff.iloc[0]['Team']
    bench_king = df_eff.sort_values(by="Bench", ascending=False).iloc[0]['Team']
    prompt = f"Write a 2-paragraph fantasy recap for Week {selected_week}. Highlight Powerhouse: {top_scorer}. Inefficient Manager: {bench_king}. Style: Wall Street Report."
    try:
        client = OpenAI(api_key=openai_key)
        return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=400).choices[0].message.content
    except: return "Analyst Offline."

# ------------------------------------------------------------------
# 7. DASHBOARD UI
# ------------------------------------------------------------------
st.title(f"🏛️ Luxury League: Week {selected_week}")

if "recap" not in st.session_state:
    with st.spinner("🎙️ Analyst is reviewing portfolios..."): st.session_state["recap"] = get_ai_recap()
st.markdown(f'<div class="studio-box"><h3>🎙️ The Studio Report</h3>{st.session_state["recap"]}</div>', unsafe_allow_html=True)

st.markdown("### 🌟 The Week's Elite")
cols = st.columns(5)
for i, (idx, p) in enumerate(df_players.iterrows()):
    with cols[i]:
        st.image(f"https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{p['ID']}.png&w=350&h=254")
        st.caption(f"{p['Name']} ({p['Points']})")

# TABS
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📜 The Ledger", "📈 The Hierarchy", "🔎 The Audit", "💎 The Hedge Fund", "🔮 The Forecast", "🚀 Next Week", "🏆 Trophy Room"])

with tab1:
    st.subheader("Weekly Matchups")
    for m in matchup_data:
        st.markdown(f"""
        <div style="background-color: #1a1c24; padding: 15px; border-radius: 10px; margin-bottom: 5px; border: 1px solid #333;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="text-align: center; width: 40%;">
                    <img src="{m['Home Logo']}" width="50" style="border-radius: 50%;">
                    <div style="font-weight: bold; color: white;">{m['Home']}</div>
                    <div style="font-size: 20px; color: #FFD700;">{m['Home Score']}</div>
                </div>
                <div style="color: #666; font-size: 12px;">VS</div>
                <div style="text-align: center; width: 40%;">
                    <img src="{m['Away Logo']}" width="50" style="border-radius: 50%;">
                    <div style="font-weight: bold; color: white;">{m['Away']}</div>
                    <div style="font-size: 20px; color: #FFD700;">{m['Away Score']}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        with st.expander(f"📉 View Lineups"):
            max_len = max(len(m['Home Roster']), len(m['Away Roster']))
            df_matchup = pd.DataFrame({
                f"{m['Home']}": [p['Name'] for p in m['Home Roster']] + [''] * (max_len - len(m['Home Roster'])),
                f"{m['Home']} Pts": [p['Score'] for p in m['Home Roster']] + [0] * (max_len - len(m['Home Roster'])),
                "Pos": [p['Pos'] for p in m['Home Roster']] + [''] * (max_len - len(m['Home Roster'])),
                f"{m['Away']} Pts": [p['Score'] for p in m['Away Roster']] + [0] * (max_len - len(m['Away Roster'])),
                f"{m['Away']}": [p['Name'] for p in m['Away Roster']] + [''] * (max_len - len(m['Away Roster'])),
            })
            st.dataframe(df_matchup, use_container_width=True, hide_index=True, column_config={
                f"{m['Home']} Pts": st.column_config.NumberColumn(format="%.1f"),
                f"{m['Away']} Pts": st.column_config.NumberColumn(format="%.1f"),
            })

with tab2:
    st.subheader("Power Rankings")
    st.bar_chart(df_eff.set_index("Team")["Total Potential"], color="#FFD700")

with tab3:
    st.subheader("Efficiency Audit")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_eff["Team"], y=df_eff["Starters"], name='Starters', marker_color='#FFD700'))
    fig.add_trace(go.Bar(x=df_eff["Team"], y=df_eff["Bench"], name='Bench Waste', marker_color='#333333'))
    fig.update_layout(barmode='stack', plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white", title="Total Potential")
    st.plotly_chart(fig, use_container_width=True)
    if not df_bench_stars.empty:
        st.markdown("#### 🚨 'Should Have Started'")
        st.dataframe(df_bench_stars, use_container_width=True, hide_index=True)

with tab4:
    st.subheader("💎 The Hedge Fund")
    if "df_advanced" not in st.session_state:
        st.info("⚠️ Accessing historical market data requires intensive calculation.")
        if st.button("🚀 Analyze Market Data"):
            with st.spinner("Compiling Assets..."):
                st.session_state["df_advanced"] = calculate_heavy_analytics(current_week)
                st.rerun()
    else:
        df_advanced = st.session_state["df_advanced"]
        fig = px.scatter(df_advanced, x="Power Score", y="Wins", text="Team", size="Points For", color="Luck Rating",
                         color_continuous_scale=["#FF4B4B", "#333333", "#00FF00"], title="Luck Matrix")
        fig.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white")
        st.plotly_chart(fig, use_container_width=True)

with tab5:
    st.subheader("🔮 The Crystal Ball")
    if "playoff_odds" not in st.session_state:
        if st.button("🎲 Run Simulation"):
            if lottie_forecast: st_lottie(lottie_forecast, height=200)
            with st.spinner("Crunching probabilities..."):
                st.session_state["playoff_odds"] = run_monte_carlo_simulation()
                st.rerun()
    else:
        df_odds = st.session_state["playoff_odds"]
        st.dataframe(df_odds, use_container_width=True, hide_index=True, column_config={
            "Playoff Odds": st.column_config.ProgressColumn("Prob", format="%.1f%%", min_value=0, max_value=100)})
        if st.button("🔄 Re-Simulate"): del st.session_state["playoff_odds"]; st.rerun()

with tab6:
    st.subheader("🚀 Next Week")
    try:
        next_week = league.current_week
        next_box_scores = league.box_scores(week=next_week)
        for game in next_box_scores:
            h_proj, a_proj = game.home_projected, game.away_projected
            if h_proj == 0: h_proj = 100
            if a_proj == 0: a_proj = 100
            spread = abs(h_proj - a_proj)
            fav = game.home_team.team_name if h_proj > a_proj else game.away_team.team_name
            with st.container():
                c1, c2, c3 = st.columns([2, 1, 2])
                with c1: st.markdown(f"**{game.home_team.team_name}**"); st.markdown(f"Proj: {h_proj:.1f}")
                with c2: st.caption(f"Fav: {fav} (+{spread:.1f})")
                with c3: st.markdown(f"**{game.away_team.team_name}**"); st.markdown(f"Proj: {a_proj:.1f}")
                st.divider()
    except: st.info("Projections unavailable.")

with tab7:
    st.subheader("🏆 The Trophy Room")
    if "awards" not in st.session_state:
        if st.button("🏅 Unveil Yearly Awards"):
            if lottie_trophy: st_lottie(lottie_trophy, height=200)
            with st.spinner("Engraving trophies..."):
                st.session_state["awards"] = calculate_season_awards(current_week)
                st.rerun()
    else:
        awards = st.session_state["awards"]
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="award-card"><h3>👑 MVP (Best Player)</h3></div>', unsafe_allow_html=True)
            if awards['MVP']:
                p = awards['MVP']
                st.image(f"https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{p['ID']}.png&w=350&h=254", width=150)
                st.metric(label=p['Name'], value=f"{p['Points']:.1f} pts", delta="Season Total")
        with c2:
            st.markdown('<div class="award-card"><h3>🐋 The Whale (Best Mgr)</h3></div>', unsafe_allow_html=True)
            mgr = awards['Best Manager']
            st.image(mgr['Logo'], width=100)
            st.metric(label=mgr['Team'], value=f"{mgr['Points']:.1f} pts", delta="Total Points For")

        st.divider()
        c3, c4, c5 = st.columns(3)
        with c3:
            st.markdown("#### 💔 Heartbreaker")
            st.caption("Smallest Margin of Defeat")
            hb = awards['Heartbreaker']
            st.metric(label=f"{hb['Loser']} lost by", value=f"{hb['Margin']:.2f} pts", delta=f"Week {hb['Week']}")
        with c4:
            st.markdown("#### 🔥 The Streak")
            st.caption("Longest Win Streak")
            stk = awards['Streak']
            st.metric(label=stk['Team'], value=f"{stk['Length']} Games", delta="Undefeated Run")
        with c5:
            st.markdown("#### 💤 Asleep at Wheel")
            st.caption("Starters with 0.0 Pts (Byes/Injuries)")
            slp = awards['Sleeper']
            st.metric(label=slp['Team'], value=f"{slp['Count']} Players", delta="Wasted Starts")
