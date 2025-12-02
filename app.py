import streamlit as st
from espn_api.football import League
import pandas as pd

# ------------------------------------------------------------------
# 1. SETUP & CONFIGURATION (The "Luxury" Theme)
# ------------------------------------------------------------------
st.set_page_config(page_title="Luxury League", page_icon="🥂", layout="wide")

# Custom CSS for Gold & Black aesthetics
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background-color: #0e1117;
    }
    /* Titles and Headers - Gold Gradient */
    h1, h2, h3, h4 {
        background: -webkit-linear-gradient(45deg, #FFD700, #FDB931);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 800 !important;
    }
    /* Metrics - Make them pop */
    div[data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        color: #FFD700 !important;
    }
    /* Cards/Containers */
    .stDataFrame {
        border: 1px solid #333;
        border-radius: 10px;
    }
    /* Images (Player Headshots & Logos) */
    img {
        border-radius: 10px;
        transition: transform .2s;
    }
    img:hover {
        transform: scale(1.05);
    }
    </style>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------------
# 2. DATA CONNECTION
# ------------------------------------------------------------------
try:
    league_id = st.secrets["league_id"]
    swid = st.secrets["swid"]
    espn_s2 = st.secrets["espn_s2"]
    year = 2025 # Ensure this matches your current league year
    
    league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
except Exception as e:
    st.error("🔒 Security Clearance Failed. Check your secrets.toml file.")
    st.stop()

# ------------------------------------------------------------------
# 3. SIDEBAR CONTROLS
# ------------------------------------------------------------------
st.sidebar.title("🥂 The Concierge")

# Calculate current week (fallback to 1 if preseason)
current_week = league.current_week - 1
if current_week == 0: 
    current_week = 1

# Let user select the week (Defaults to latest completed week)
selected_week = st.sidebar.slider("Select Week", 1, current_week, current_week)

# ------------------------------------------------------------------
# 4. ADVANCED DATA PROCESSING (The Engine)
# ------------------------------------------------------------------
box_scores = league.box_scores(week=selected_week)

# Initialize empty lists to store data
score_data = []
all_active_players = [] 
bench_data = []

# Award Trackers (Initialize with defaults)
highest_score_loser = {"score": -1, "team": "N/A"}
lowest_score_winner = {"score": 999, "team": "N/A"}
biggest_bench_warmer = {"points": -1, "team": "N/A"}

# --- Main Data Loop ---
for game in box_scores:
    # 1. Capture Team Info
    home_team = game.home_team.team_name
    away_team = game.away_team.team_name
    home_score = game.home_score
    away_score = game.away_score
    
    # 2. Determine Winner/Loser for Awards
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
        
    # 3. Build Scoreboard Data (With Logo URLs)
    score_data.append({
        "Home Logo": game.home_team.logo_url, 
        "Home Team": home_team,
        "Score": f"{home_score} - {away_score}",
        "Away Team": away_team,
        "Away Logo": game.away_team.logo_url,
        "Winner": "Home" if home_score > away_score else "Away"
    })

    # 4. Player & Bench Analysis Helper Function
    def process_lineup(lineup, team_name):
        team_bench_points = 0
        for player in lineup:
            if player.slot_position == 'BE':
                team_bench_points += player.points
            else:
                # Store active player for "Top Performers" list
                all_active_players.append({
                    "Name": player.name, 
                    "Points": player.points,
                    "Team": team_name, 
                    "PlayerID": player.playerId
                })
        return team_bench_points

    # Process both lineups
    home_bench = process_lineup(game.home_lineup, home_team)
    bench_data.append({"Team": home_team, "Unrealized Gains": home_bench})
    
    away_bench = process_lineup(game.away_lineup, away_team)
    bench_data.append({"Team": away_team, "Unrealized Gains": away_bench})

# --- Post-Loop Calculations ---

# Award Check: The Speculator (Most Bench Points)
df_bench = pd.DataFrame(bench_data).sort_values(by="Unrealized Gains", ascending=False)
if not df_bench.empty:
    biggest_bench_warmer = {"team": df_bench.iloc[0]["Team"], "points": df_bench.iloc[0]["Unrealized Gains"]}

# Top Players Logic (Sort by points, take top 5)
top_performers = pd.DataFrame(all_active_players).sort_values(by="Points", ascending=False).head(5)

# Power Rankings Logic
power_rankings = league.power_rankings(week=selected_week)
rank_data = [{"Rank": i+1, "Team": t[1].team_name, "Power Score": float(t[0])} for i, t in enumerate(power_rankings)]
df_rank = pd.DataFrame(rank_data)

# ------------------------------------------------------------------
# 5. THE DASHBOARD UI
# ------------------------------------------------------------------
st.title(f"🏛️ Luxury League: Week {selected_week}")

# --- SECTION 1: WEEKLY HONORS (The Badges) ---
st.markdown("### 🎖️ Weekly Honors")
col1, col2, col3 = st.columns(3)
col1.metric("💔 The Tragic Hero", f"{highest_score_loser['score']} pts", f"{highest_score_loser['team']}")
col2.metric("🔫 The Bandit", f"{lowest_score_winner['score']} pts", f"{lowest_score_winner['team']}")
col3.metric("📉 The Speculator", f"{biggest_bench_warmer['points']} pts", f"{biggest_bench_warmer['team']}")

st.divider()

# --- SECTION 2: TOP PLAYERS (With Headshots) ---
st.markdown("### 🌟 The Week's Elite")
cols = st.columns(5)
if not top_performers.empty:
    for i, (index, player) in enumerate(top_performers.iterrows()):
        with cols[i]:
            # Construct ESPN Headshot URL
            headshot = f"https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{player['PlayerID']}.png&w=350&h=254"
            st.image(headshot)
            st.markdown(f"**{player['Name']}**")
            st.caption(f"{player['Points']} pts")

st.divider()

# --- SECTION 3: THE TABS ---
tab1, tab2, tab3 = st.tabs(["📜 The Ledger", "📈 The Hierarchy", "🔎 The Audit"])

# TAB 1: Scoreboard with Team Logos
with tab1:
    st.subheader("Weekly Matchups")
    df_scores = pd.DataFrame(score_data)
    
    st.dataframe(
        df_scores, 
        use_container_width=True, 
        hide_index=True,
        column_order=["Home Logo", "Home Team", "Score", "Away Team", "Away Logo", "Winner"],
        column_config={
            "Home Logo": st.column_config.ImageColumn(" ", width="small"),
            "Away Logo": st.column_config.ImageColumn(" ", width="small"),
            "Score": st.column_config.TextColumn("Final Score", help="Official box score"),
            "Winner": st.column_config.TextColumn("Victor", width="small")
        }
    )

# TAB 2: Power Rankings with #1 Team Logo
with tab2:
    st.subheader("Power Rankings")
    
    if not df_rank.empty:
        # Get #1 Team Info
        top_dog = df_rank.iloc[0]
        try:
            top_team_obj = next(t for t in league.teams if t.team_name == top_dog["Team"])
            top_logo = top_team_obj.logo_url
        except:
            top_logo = "" # Fallback if no logo found

        c1, c2 = st.columns([1, 4])
        with c1:
            if top_logo:
                st.image(top_logo, caption="Current #1")
        with c2:
            st.bar_chart(df_rank.set_index("Team")["Power Score"], color="#FFD700")

# TAB 3: Bench Points Audit
with tab3:
    st.subheader("The Manager Efficiency Audit")
    st.caption("Points left on the bench (Unrealized Gains)")
    st.bar_chart(df_bench.set_index("Team"), color="#333333")
