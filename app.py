import streamlit as st
from espn_api.football import League
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from openai import OpenAI

# ------------------------------------------------------------------
# 1. CONFIGURATION & STYLE
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
# 2. CONNECTION & CACHING
# ------------------------------------------------------------------
try:
    # Load secrets safely
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
# 3. ADVANCED CALCULATIONS (Efficiency & Luck)
# ------------------------------------------------------------------
@st.cache_data(ttl=3600)
def calculate_advanced_stats(current_week):
    data_rows = []
    
    # We need historical data for the scatter plot
    for team in league.teams:
        # 1. Power Score (ESPN's internal calculation)
        # Note: We take the most recent available rank/score
        power_score = team.wins * 20 + team.points_for * 0.5 # Simple custom power formula if API fails
        
        # 2. Luck Calculation (True Record)
        true_wins = 0
        total_matchups = 0
        
        # Loop through history to find "True Wins"
        # (This is expensive, so we just estimate using PF for speed if needed)
        # But here is the real way:
        for w in range(1, current_week + 1):
            box = league.box_scores(week=w)
            # Find this team's score
            my_score = next((g.home_score if g.home_team == team else g.away_score 
                             for g in box if g.home_team == team or g.away_team == team), 0)
            
            # Compare vs entire league
            all_scores = [g.home_score for g in box] + [g.away_score for g in box]
            wins_this_week = sum(1 for s in all_scores if my_score > s)
            true_wins += wins_this_week
            total_matchups += (len(league.teams) - 1)

        true_win_pct = true_wins / total_matchups if total_matchups > 0 else 0
        actual_win_pct = team.wins / (team.wins + team.losses + 0.001)
        
        # Luck = Difference between Actual and Theoretical
        luck_rating = (actual_win_pct - true_win_pct) * 10
        
        data_rows.append({
            "Team": team.team_name,
            "Logo": team.logo_url,
            "Wins": team.wins,
            "Points For": team.points_for,
            "Power Score": round(team.points_for / current_week, 1), # Using PPG as "Power" for clarity
            "Luck Rating": luck_rating,
            "True Win %": true_win_pct
        })
        
    return pd.DataFrame(data_rows)

# ------------------------------------------------------------------
# 4. CURRENT WEEK DATA PROCESSING
# ------------------------------------------------------------------
st.sidebar.title("🥂 The Concierge")
current_week = league.current_week - 1
if current_week == 0: current_week = 1
selected_week = st.sidebar.slider("Select Week", 1, current_week, current_week)

box_scores = league.box_scores(week=selected_week)

# Containers
matchup_data = []
efficiency_data = [] # For the new "Audit" chart
all_active_players = []

# Loop
for game in box_scores:
    home = game.home_team
    away = game.away_team
    
    # 1. Store Matchup
    matchup_data.append({
        "Home": home.team_name, "Home Score": game.home_score, "Home Logo": home.logo_url,
        "Away": away.team_name, "Away Score": game.away_score, "Away Logo": away.logo_url
    })
    
    # 2. Efficiency Calculation (Starter vs Bench)
    def get_split(lineup, team_name):
        starters = 0
        bench = 0
        for p in lineup:
            if p.slot_position == 'BE': bench += p.points
            else: 
                starters += p.points
                all_active_players.append({"Name": p.name, "Points": p.points, "Team": team_name, "ID": p.playerId})
        return starters, bench

    h_start, h_bench = get_split(game.home_lineup, home.team_name)
    a_start, a_bench = get_split(game.away_lineup, away.team_name)
    
    efficiency_data.append({"Team": home.team_name, "Starters": h_start, "Bench": h_bench, "Total Potential": h_start + h_bench})
    efficiency_data.append({"Team": away.team_name, "Starters": a_start, "Bench": a_bench, "Total Potential": a_start + a_bench})

# DataFrames
df_eff = pd.DataFrame(efficiency_data).sort_values(by="Total Potential", ascending=False)
df_advanced = calculate_advanced_stats(current_week)
df_players = pd.DataFrame(all_active_players).sort_values(by="Points", ascending=False).head(5)

# ------------------------------------------------------------------
# 5. AI NARRATIVE
# ------------------------------------------------------------------
def get_ai_recap():
    if not openai_key: return "⚠️ Add 'openai_key' to secrets."
    
    # Find superlatives for context
    top_scorer = df_eff.iloc[0]['Team']
    bench_king = df_eff.sort_values(by="Bench", ascending=False).iloc[0]['Team']
    
    prompt = f"""
    Write a 2-paragraph fantasy football recap for Week {selected_week}.
    Focus on:
    1. The "Powerhouse" of the week: {top_scorer} (Highest Potential).
    2. The "Inefficient Manager": {bench_king} (Most points left on bench).
    Style: Wall Street financial report.
    """
    try:
        client = OpenAI(api_key=openai_key)
        return client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=400
        ).choices[0].message.content
    except: return "Analyst is offline."

# ------------------------------------------------------------------
# 6. DASHBOARD UI
# ------------------------------------------------------------------
st.title(f"🏛️ Luxury League: Week {selected_week}")

# AI Box
if "recap" not in st.session_state:
    with st.spinner("🎙️ Analyst is reviewing portfolios..."):
        st.session_state["recap"] = get_ai_recap()
st.markdown(f'<div class="studio-box"><h3>🎙️ The Studio Report</h3>{st.session_state["recap"]}</div>', unsafe_allow_html=True)

# Top Players
st.markdown("### 🌟 The Week's Elite")
cols = st.columns(5)
for i, (idx, p) in enumerate(df_players.iterrows()):
    with cols[i]:
        st.image(f"https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{p['ID']}.png&w=350&h=254")
        st.caption(f"{p['Name']} ({p['Points']})")

# TABS
tab1, tab2, tab3 = st.tabs(["📜 The Ledger", "📈 The Hierarchy", "🔎 The Audit"])

with tab1:
    st.subheader("Weekly Matchups")
    for m in matchup_data:
        # Custom HTML Scoreboard for "Luxury" feel
        st.markdown(f"""
        <div style="background-color: #1a1c24; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #333;">
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

with tab2:
    st.subheader("Power vs. Performance Matrix")
    st.caption("Are you actually good, or just lucky?")
    
    # SCATTER PLOT: Power (PPG) vs Wins
    fig = px.scatter(
        df_advanced, 
        x="Power Score", 
        y="Wins", 
        text="Team", 
        size="Points For",
        color="Luck Rating",
        color_continuous_scale=["#FF4B4B", "#333333", "#00FF00"], # Red (Unlucky) -> Green (Lucky)
        title="The Luck Matrix: Power (PPG) vs Actual Wins"
    )
    fig.update_traces(textposition='top center', marker=dict(line=dict(width=1, color='DarkSlateGrey')))
    fig.update_layout(
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white",
        xaxis_title="Team Power (Avg Points Per Game)",
        yaxis_title="Actual Wins"
    )
    # Add a reference line for "Average"
    fig.add_shape(type="line", x0=df_advanced["Power Score"].min(), y0=df_advanced["Wins"].min(),
                  x1=df_advanced["Power Score"].max(), y1=df_advanced["Wins"].max(),
                  line=dict(color="Gold", width=2, dash="dash"), opacity=0.5)
    
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Manager Efficiency Audit")
    st.caption("Green = Points Scored. Red = Points Wasted on Bench.")
    
    # STACKED BAR CHART
    fig = go.Figure()
    
    # 1. Starters Bar (Green/Gold)
    fig.add_trace(go.Bar(
        x=df_eff["Team"], y=df_eff["Starters"], 
        name='Starters', marker_color='#FFD700'
    ))
    
    # 2. Bench Bar (Red/Grey)
    fig.add_trace(go.Bar(
        x=df_eff["Team"], y=df_eff["Bench"], 
        name='Bench Waste', marker_color='#333333'
    ))
    
    fig.update_layout(
        barmode='stack', 
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="white",
        title="Total Roster Strength (Potential Points)",
        xaxis_title="Manager",
        yaxis_title="Points"
    )
    
    st.plotly_chart(fig, use_container_width=True)
