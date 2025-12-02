import streamlit as st
from espn_api.football import League
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI
from streamlit_lottie import st_lottie
import requests

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
    </style>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------------
# 2. CONNECTION
# ------------------------------------------------------------------
def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200: return None
        return r.json()
    except: return None

# Faster loading animation
lottie_loading = load_lottieurl("https://lottie.host/5a882010-89b6-45bc-8a4d-06886982f8d8/WfK7bXoGqj.json")

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
# 3. HEAVY MATH (Lazy Function)
# ------------------------------------------------------------------
@st.cache_data(ttl=3600)
def calculate_heavy_analytics(current_week):
    # This is the slow function that loops through history
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
            "Team": team.team_name,
            "Wins": team.wins,
            "Points For": team.points_for,
            "Power Score": power_score,
            "Luck Rating": luck_rating,
            "True Win %": true_win_pct
        })
    return pd.DataFrame(data_rows)

# ------------------------------------------------------------------
# 4. INITIAL LOADING (Fast)
# ------------------------------------------------------------------
st.sidebar.title("🥂 The Concierge")
current_week = league.current_week - 1
if current_week == 0: current_week = 1
selected_week = st.sidebar.slider("Select Week", 1, current_week, current_week)

# Show splash screen ONLY if we haven't loaded the BASIC data yet
if 'box_scores' not in st.session_state or st.session_state.get('week') != selected_week:
    if lottie_loading:
        st_lottie(lottie_loading, height=200, key="loading")
    
    # Fast Load: Just this week's scores
    box_scores = league.box_scores(week=selected_week)
    st.session_state['box_scores'] = box_scores
    st.session_state['week'] = selected_week
    st.rerun()

box_scores = st.session_state['box_scores']

# ------------------------------------------------------------------
# 5. DATA PROCESSING (Fast Loop)
# ------------------------------------------------------------------
matchup_data = []
efficiency_data = [] 
all_active_players = []
bench_highlights = []

for game in box_scores:
    home = game.home_team
    away = game.away_team
    
    def get_roster_data(lineup, team_name):
        starters = []
        bench = []
        points_starter = 0
        points_bench = 0
        for p in lineup:
            player_info = {"Name": p.name, "Score": p.points, "Pos": p.slot_position}
            if p.slot_position == 'BE':
                bench.append(player_info)
                points_bench += p.points
                if p.points > 15: bench_highlights.append({"Team": team_name, "Player": p.name, "Score": p.points})
            else:
                starters.append(player_info)
                points_starter += p.points
                all_active_players.append({"Name": p.name, "Points": p.points, "Team": team_name, "ID": p.playerId})
        return starters, bench, points_starter, points_bench

    h_roster, h_bench_roster, h_start_pts, h_bench_pts = get_roster_data(game.home_lineup, home.team_name)
    a_roster, a_bench_roster, a_start_pts, a_bench_pts = get_roster_data(game.away_lineup, away.team_name)
    
    matchup_data.append({
        "Home": home.team_name, "Home Score": game.home_score, "Home Logo": home.logo_url, "Home Roster": h_roster,
        "Away": away.team_name, "Away Score": game.away_score, "Away Logo": away.logo_url, "Away Roster": a_roster
    })
    
    efficiency_data.append({"Team": home.team_name, "Starters": h_start_pts, "Bench": h_bench_pts, "Total Potential": h_start_pts + h_bench_pts})
    efficiency_data.append({"Team": away.team_name, "Starters": a_start_pts, "Bench": a_bench_pts, "Total Potential": a_start_pts + a_bench_pts})

df_eff = pd.DataFrame(efficiency_data).sort_values(by="Total Potential", ascending=False)
df_players = pd.DataFrame(all_active_players).sort_values(by="Points", ascending=False).head(5)
df_bench_stars = pd.DataFrame(bench_highlights).sort_values(by="Score", ascending=False).head(5)

# ------------------------------------------------------------------
# 6. AI NARRATIVE (On Demand)
# ------------------------------------------------------------------
def get_ai_recap():
    if not openai_key: return "⚠️ Add 'openai_key' to secrets."
    top_scorer = df_eff.iloc[0]['Team']
    bench_king = df_eff.sort_values(by="Bench", ascending=False).iloc[0]['Team']
    prompt = f"Write a 2-paragraph fantasy recap for Week {selected_week}. Highlight Powerhouse: {top_scorer}, Inefficient Manager: {bench_king}. Style: Wall Street Report."
    try:
        client = OpenAI(api_key=openai_key)
        return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=400).choices[0].message.content
    except: return "Analyst Offline."

# ------------------------------------------------------------------
# 7. DASHBOARD UI
# ------------------------------------------------------------------
st.title(f"🏛️ Luxury League: Week {selected_week}")

# AI Box
if "recap" not in st.session_state:
    with st.spinner("🎙️ Analyst is reviewing portfolios..."): st.session_state["recap"] = get_ai_recap()
st.markdown(f'<div class="studio-box"><h3>🎙️ The Studio Report</h3>{st.session_state["recap"]}</div>', unsafe_allow_html=True)

# Top Players
st.markdown("### 🌟 The Week's Elite")
cols = st.columns(5)
for i, (idx, p) in enumerate(df_players.iterrows()):
    with cols[i]:
        st.image(f"https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{p['ID']}.png&w=350&h=254")
        st.caption(f"{p['Name']} ({p['Points']})")

# TABS
tab1, tab2, tab3, tab4 = st.tabs(["📜 The Ledger", "📈 The Hierarchy", "🔎 The Audit", "💎 The Hedge Fund"])

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
        
        with st.expander(f"📉 View Lineups: {m['Home']} vs {m['Away']}"):
            max_len = max(len(m['Home Roster']), len(m['Away Roster']))
            df_matchup = pd.DataFrame({
                f"{m['Home']} Player": [p['Name'] for p in m['Home Roster']] + [''] * (max_len - len(m['Home Roster'])),
                f"{m['Home']} Pts": [p['Score'] for p in m['Home Roster']] + [0] * (max_len - len(m['Home Roster'])),
                "Pos": [p['Pos'] for p in m['Home Roster']] + [''] * (max_len - len(m['Home Roster'])),
                f"{m['Away']} Pts": [p['Score'] for p in m['Away Roster']] + [0] * (max_len - len(m['Away Roster'])),
                f"{m['Away']} Player": [p['Name'] for p in m['Away Roster']] + [''] * (max_len - len(m['Away Roster'])),
            })
            st.dataframe(df_matchup, use_container_width=True, hide_index=True, column_config={
                f"{m['Home']} Pts": st.column_config.NumberColumn(format="%.1f"),
                f"{m['Away']} Pts": st.column_config.NumberColumn(format="%.1f"),
            })

with tab2:
    st.subheader("Power Rankings (Current Week)")
    # Simple, fast bar chart based on Total Potential Points for this week
    st.bar_chart(df_eff.set_index("Team")["Total Potential"], color="#FFD700")

with tab3:
    st.subheader("Manager Efficiency Audit")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_eff["Team"], y=df_eff["Starters"], name='Starters', marker_color='#FFD700'))
    fig.add_trace(go.Bar(x=df_eff["Team"], y=df_eff["Bench"], name='Bench Waste', marker_color='#333333'))
    fig.update_layout(barmode='stack', plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white", title="Total Potential Points")
    st.plotly_chart(fig, use_container_width=True)
    if not df_bench_stars.empty:
        st.markdown("#### 🚨 The 'Should Have Started' List")
        st.dataframe(df_bench_stars, use_container_width=True, hide_index=True, column_config={"Score": st.column_config.NumberColumn(format="%.1f pts")})

with tab4:
    st.subheader("💎 The Hedge Fund")
    st.caption("Advanced Market Analytics (Requires Historical Calculation)")
    
    # LAZY LOADING BUTTON
    if "df_advanced" not in st.session_state:
        st.info("⚠️ Accessing historical market data requires intensive calculation.")
        if st.button("🚀 Analyze Market Data (Run Simulation)"):
            with st.spinner("Compiling Year-to-Date Assets..."):
                # Run the heavy math NOW
                df_advanced = calculate_heavy_analytics(current_week)
                st.session_state["df_advanced"] = df_advanced
                st.rerun()
    else:
        # Show the Charts (Data is loaded)
        df_advanced = st.session_state["df_advanced"]
        
        st.markdown("#### 🎯 The Luck Matrix (Skill vs Luck)")
        fig = px.scatter(df_advanced, x="Power Score", y="Wins", text="Team", size="Points For", color="Luck Rating",
                         color_continuous_scale=["#FF4B4B", "#333333", "#00FF00"], title="Luck Matrix: True Skill vs Actual Record")
        fig.update_traces(textposition='top center', marker=dict(line=dict(width=1, color='DarkSlateGrey')))
        fig.update_layout(plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white")
        st.plotly_chart(fig, use_container_width=True)
        
        if st.button("🔄 Refresh Market Data"):
            del st.session_state["df_advanced"]
            st.rerun()
