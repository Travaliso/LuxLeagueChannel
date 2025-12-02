import streamlit as st
from espn_api.football import League
import pandas as pd

# ------------------------------------------------------------------
# 1. SETUP & CONFIGURATION
# ------------------------------------------------------------------
st.set_page_config(page_title="Luxury League", page_icon="🥂", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    h1, h2, h3, h4 {
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
    .stDataFrame { border: 1px solid #333; border-radius: 10px; }
    img { border-radius: 10px; transition: transform .2s; }
    img:hover { transform: scale(1.05); }
    </style>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------------
# 2. DATA CONNECTION
# ------------------------------------------------------------------
try:
    league_id = st.secrets["league_id"]
    swid = st.secrets["swid"]
    espn_s2 = st.secrets["espn_s2"]
    year = 2025
    league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
except Exception:
    st.error("🔒 Security Clearance Failed. Check Secrets.")
    st.stop()

# ------------------------------------------------------------------
# 3. SIDEBAR
# ------------------------------------------------------------------
st.sidebar.title("🥂 The Concierge")
current_week = league.current_week - 1
if current_week == 0: current_week = 1
selected_week = st.sidebar.slider("Select Week", 1, current_week, current_week)

# ------------------------------------------------------------------
# 4. ADVANCED DATA PROCESSING (AWARDS ENGINE)
# ------------------------------------------------------------------
box_scores = league.box_scores(week=selected_week)

score_data = []
all_active_players = []
bench_data = []

# Award Trackers
highest_score_loser = {"score": -1, "team": "N/A"}
lowest_score_winner = {"score": 999, "team": "N/A"}
biggest_bench_warmer = {"points": -1, "team": "N/A"}

for game in box_scores:
    # --- 1. Basic Scores ---
    home_team = game.home_team.team_name
    away_team = game.away_team.team_name
    home_score = game.home_score
    away_score = game.away_score
    
    # Determine Winner/Loser
    if home_score > away_score:
        winner, winner_score = home_team, home_score
        loser, loser_score = away_team, away_score
    else:
        winner, winner_score = away_team, away_score
        loser, loser_score = home_team, home_score

    # Award Check: Tragic Hero (High score loss)
    if loser_score > highest_score_loser["score"]:
        highest_score_loser = {"score": loser_score, "team": loser}

    # Award Check: The Bandit (Low score win)
    if winner_score < lowest_score_winner["score"]:
        lowest_score_winner = {"score": winner_score, "team": winner}
        
    score_data.append({
        "Home Team": home_team, "Score": f"{home_score} - {away_score}",
        "Away Team": away_team, "Winner": "Home" if home_score > away_score else "Away"
    })

    # --- 2. Bench & Player Logic ---
    # Helper function to process a lineup
    def process_lineup(lineup, team_name):
        team_bench_points = 0
        for player in lineup:
            if player.slot_position == 'BE':
                team_bench_points += player.points
            else:
                # Active player logic
                all_active_players.append({
                    "Name": player.name, "Points": player.points,
                    "Team": team_name, "PlayerID": player.playerId
                })
        return team_bench_points

    # Process Home
    home_bench = process_lineup(game.home_lineup, home_team)
    bench_data.append({"Team": home_team, "Unrealized Gains": home_bench})
    
    # Process Away
    away_bench = process_lineup(game.away_lineup, away_team)
    bench_data.append({"Team": away_team, "Unrealized Gains": away_bench})

# Award Check: The Speculator (Most Bench Points)
df_bench = pd.DataFrame(bench_data).sort_values(by="Unrealized Gains", ascending=False)
biggest_bench_warmer = {"team": df_bench.iloc[0]["Team"], "points": df_bench.iloc[0]["Unrealized Gains"]}

# Top Players Logic
top_performers = pd.DataFrame(all_active_players).sort_values(by="Points", ascending=False).head(5)

# Power Rankings Logic
power_rankings = league.power_rankings(week=selected_week)
rank_data = [{"Rank": i+1, "Team": t[1].team_name, "Power Score": float(t[0])} for i, t in enumerate(power_rankings)]
df_rank = pd.DataFrame(rank_data)

# ------------------------------------------------------------------
# 5. THE DASHBOARD UI
# ------------------------------------------------------------------
st.title(f"🏛️ Luxury League: Week {selected_week}")

# --- SUPERLATIVES (NEW) ---
st.markdown("### 🎖️ Weekly Honors")
col1, col2, col3 = st.columns(3)
col1.metric("💔 The Tragic Hero", f"{highest_score_loser['score']} pts", f"{highest_score_loser['team']} (Highest Loss)")
col2.metric("🔫 The Bandit", f"{lowest_score_winner['score']} pts", f"{lowest_score_winner['team']} (Lowest Win)")
col3.metric("📉 The Speculator", f"{biggest_bench_warmer['points']} pts", f"{biggest_bench_warmer['team']} (Most Bench Pts)")

st.divider()

# --- TOP PLAYERS ---
st.markdown("### 🌟 The Week's Elite")
cols = st.columns(5)
for i, (index, player) in enumerate(top_performers.iterrows()):
    with cols[i]:
        headshot = f"https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{player['PlayerID']}.png&w=350&h=254"
        st.image(headshot)
        st.markdown(f"**{player['Name']}**")
        st.caption(f"{player['Points']} pts ({player['Team']})")

st.divider()

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📜 The Ledger", "📈 The Hierarchy", "🔎 The Audit"])

with tab1:
    st.subheader("Weekly Matchups")
    st.dataframe(pd.DataFrame(score_data), use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Power Rankings")
    st.bar_chart(df_rank.set_index("Team")["Power Score"], color="#FFD700")

with tab3:
    st.subheader("The Manager Efficiency Audit")
    st.caption("Who left the most 'Unrealized Gains' (Points) on their bench?")
    
    # Custom Bar Chart for Bench Points
    st.bar_chart(df_bench.set_index("Team"), color="#333333")
    
    st.info(f"💡 Analysis: {biggest_bench_warmer['team']} mismanaged their assets this week, leaving {biggest_bench_warmer['points']} points inactive.")
