import streamlit as st
from espn_api.football import League
import pandas as pd
import streamlit as st
from espn_api.football import League
import pandas as pd

# ------------------------------------------------------------------
# 1. SETUP & CONFIGURATION
# ------------------------------------------------------------------
st.set_page_config(page_title="Luxury League", page_icon="🥂", layout="wide")

# Custom CSS for the "Luxury" Aesthetic (Gold & Black)
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background-color: #0e1117;
    }
    /* Titles and Headers - Gold Gradient */
    h1, h2, h3 {
        background: -webkit-linear-gradient(45deg, #FFD700, #FDB931);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 800 !important;
    }
    /* Metrics - Make them pop */
    div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
        color: #FFD700 !important;
    }
    /* Cards/Containers */
    .stDataFrame {
        border: 1px solid #333;
        border-radius: 10px;
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
    year = 2025
    league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
except Exception as e:
    st.error("🔒 Security Clearance Failed. Check Secrets.")
    st.stop()

# ------------------------------------------------------------------
# 3. SIDEBAR CONTROLS
# ------------------------------------------------------------------
st.sidebar.title("🥂 The Concierge")
current_week = league.current_week - 1
if current_week == 0: current_week = 1

# Let user select the week (Defaults to latest)
selected_week = st.sidebar.slider("Select Week", 1, current_week, current_week)

# ------------------------------------------------------------------
# 4. DATA PROCESSING (ADVANCED)
# ------------------------------------------------------------------
box_scores = league.box_scores(week=selected_week)

# Lists to hold data
score_data = []
all_active_players = [] # We will store every player who started

high_score = 0
high_score_team = ""
min_margin = 999
close_game = ""

for game in box_scores:
    # 1. Team Scoring Logic
    home_score = game.home_score
    away_score = game.away_score
    
    if home_score > high_score: 
        high_score = home_score
        high_score_team = game.home_team.team_name
    if away_score > high_score: 
        high_score = away_score
        high_score_team = game.away_team.team_name
        
    margin = abs(home_score - away_score)
    if margin < min_margin:
        min_margin = margin
        close_game = f"{game.home_team.team_name} vs {game.away_team.team_name}"

    score_data.append({
        "Home Team": game.home_team.team_name,
        "Score": f"{home_score} - {away_score}",
        "Away Team": game.away_team.team_name,
        "Winner": "Home" if home_score > away_score else "Away"
    })

    # 2. Player Level Logic (The New Part)
    # We loop through every player on the Home and Away rosters
    for player in game.home_lineup:
        if player.slot_position != 'BE': # Ignore Bench players for Top Performers
            all_active_players.append({
                "Name": player.name,
                "Points": player.points,
                "Team": game.home_team.team_name,
                "Position": player.position,
                "ProTeam": player.proTeam,
                "PlayerID": player.playerId # We need this for the headshot
            })
            
    for player in game.away_lineup:
        if player.slot_position != 'BE':
            all_active_players.append({
                "Name": player.name,
                "Points": player.points,
                "Team": game.away_team.team_name,
                "Position": player.position,
                "ProTeam": player.proTeam,
                "PlayerID": player.playerId
            })

# Sort players by points to get the MVP list
df_players = pd.DataFrame(all_active_players)
top_performers = df_players.sort_values(by="Points", ascending=False).head(5)

# ------------------------------------------------------------------
# 5. THE DASHBOARD UI (UPDATED)
# ------------------------------------------------------------------

st.title(f"🏛️ Luxury League: Week {selected_week}")

# --- NEW SECTION: THE HALL OF FAME (Top Players) ---
st.markdown("### 🌟 The Week's Elite")
cols = st.columns(5) # Create 5 columns for the Top 5 players

# Loop through the top 5 players and display them like trading cards
for i, (index, player) in enumerate(top_performers.iterrows()):
    with cols[i]:
        # ESPN Headshot URL Construction
        headshot_url = f"https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{player['PlayerID']}.png&w=350&h=254"
        
        st.image(headshot_url)
        st.markdown(f"**{player['Name']}**")
        st.caption(f"{player['Points']} pts")
        st.caption(f"Owner: {player['Team']}")

st.divider()

# --- EXISTING METRICS ---
c1, c2, c3 = st.columns(3)
c1.metric("💰 Highest Earner", f"{high_score}", high_score_team)
c2.metric("🗡️ Closest Call", f"{min_margin:.2f}", "Margin of Victory")
c3.metric("📅 Fiscal Period", f"Week {selected_week}", "Completed")

# ... (Keep your Tabs code from the previous step below here) ...

# ------------------------------------------------------------------
# 5. THE DASHBOARD UI
# ------------------------------------------------------------------

st.title(f"🏛️ Luxury League: Week {selected_week}")
st.markdown("### *The Executive Summary*")

# Top Metrics
c1, c2, c3 = st.columns(3)
c1.metric("💰 Highest Earner", f"{high_score}", high_score_team)
c2.metric("🗡️ Closest Call", f"{min_margin:.2f}", "Margin of Victory")
c3.metric("📅 Fiscal Period", f"Week {selected_week}", "Completed")

st.markdown("---")

# TABS for cleaner organization
tab1, tab2, tab3 = st.tabs(["📜 The Ledger", "📈 The Hierarchy", "📊 The Audit"])

with tab1:
    st.subheader("Weekly Transactions")
    df_scores = pd.DataFrame(score_data)
    st.dataframe(
        df_scores, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Score": st.column_config.TextColumn("Final Score", help="Official box score"),
            "Winner": st.column_config.TextColumn("Victor", width="small")
        }
    )

with tab2:
    st.subheader("Power Rankings")
    st.caption("Calculated based on margin of victory and strength of schedule.")
    
    # specialized chart
    st.bar_chart(
        df_rank.set_index("Team")["Power Score"],
        color="#FFD700" # Gold bars
    )

with tab3:
    st.subheader("League Standings (The 1%)")
    
    standings_data = []
    for team in league.teams:
        standings_data.append({
            "Team": team.team_name,
            "Wins": team.wins,
            "Losses": team.losses,
            "Points For": team.points_for,
            "PF/G": round(team.points_for / selected_week, 1)
        })
    
    df_standings = pd.DataFrame(standings_data).sort_values(by="Points For", ascending=False)
    st.dataframe(df_standings, use_container_width=True, hide_index=True)
st.title("🏈 Fantasy League Recap")

try:
    # Load secrets
    league_id = st.secrets["league_id"]
    swid = st.secrets["swid"]
    espn_s2 = st.secrets["espn_s2"]
    
    # ---------------------------------------------------------
    # NEW CODE STARTS HERE
    # ---------------------------------------------------------

    # 1. Connect to League (Updated to 2025)
    year = 2025 
    league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
    
    # 2. Figure out which week to show
    # If the current week hasn't happened yet, look at the previous week
    week_num = league.current_week - 1
    if week_num == 0:
        week_num = 1 # Fallback for preseason
    
    st.header(f"📺 Luxury League Recap: Week {week_num}")

    # 3. Get the Box Scores
    box_scores = league.box_scores(week=week_num)
    
    # 4. Calculate Key Stats (The "SportsCenter" Highlights)
    high_score = 0
    high_score_team = ""
    closest_margin = 999
    closest_game = ""
    
    score_data = []

    for game in box_scores:
        # Calculate margins and high scores
        home_score = game.home_score
        away_score = game.away_score
        
        # Check for high scorer
        if home_score > high_score:
            high_score = home_score
            high_score_team = game.home_team.team_name
        if away_score > high_score:
            high_score = away_score
            high_score_team = game.away_team.team_name
            
        # Check for closest game
        margin = abs(home_score - away_score)
        if margin < closest_margin:
            closest_margin = margin
            closest_game = f"{game.home_team.team_name} vs {game.away_team.team_name}"

        # Save data for the table
        score_data.append({
            "Home Team": game.home_team.team_name,
            "Score": f"{home_score} - {away_score}",
            "Away Team": game.away_team.team_name,
            "Winner": "Home" if home_score > away_score else "Away"
        })

    # 5. Display "The Ticker" (Metrics)
    col1, col2, col3 = st.columns(3)
    col1.metric("🔥 High Score", f"{high_score} pts", high_score_team)
    col2.metric("🔪 Nail-Biter", f"{closest_margin:.2f} pts", closest_game)
    col3.metric("🏆 Playoff Chances", "Updating...", "See below")

    st.divider()

    # 6. The Scoreboard
    st.subheader(f"Week {week_num} Scoreboard")
    df = pd.DataFrame(score_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error("Connection failed.")
    st.code(e)
