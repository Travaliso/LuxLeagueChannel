import streamlit as st
from espn_api.football import League
import pandas as pd
from openai import OpenAI

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
    
    .studio-box {
        background-color: #1e2130;
        border-left: 5px solid #FFD700;
        padding: 20px;
        border-radius: 5px;
        margin-bottom: 20px;
        font-family: 'Georgia', serif;
        color: #e0e0e0;
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
    openai_key = st.secrets.get("openai_key")
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
# 4. DATA PROCESSING
# ------------------------------------------------------------------
box_scores = league.box_scores(week=selected_week)

# Data Containers
score_data = [] # For the simple table
matchup_details = [] # For the deep dive charts
all_active_players = [] 
bench_data = []

# Award Trackers
highest_score_loser = {"score": -1, "team": "N/A"}
lowest_score_winner = {"score": 999, "team": "N/A"}
biggest_bench_warmer = {"points": -1, "team": "N/A"}

for game in box_scores:
    # --- Basic Info ---
    home_team = game.home_team.team_name
    away_team = game.away_team.team_name
    home_score = game.home_score
    away_score = game.away_score
    
    # --- Winner/Loser Logic ---
    if home_score > away_score:
        winner, winner_score = home_team, home_score
        loser, loser_score = away_team, away_score
    else:
        winner, winner_score = away_team, away_score
        loser, loser_score = home_team, home_score

    # Award Checks
    if loser_score > highest_score_loser["score"]:
        highest_score_loser = {"score": loser_score, "team": loser}
    if winner_score < lowest_score_winner["score"]:
        lowest_score_winner = {"score": winner_score, "team": winner}
        
    score_data.append({
        "Home Logo": game.home_team.logo_url, 
        "Home Team": home_team,
        "Score": f"{home_score} - {away_score}",
        "Away Team": away_team,
        "Away Logo": game.away_team.logo_url,
        "Winner": "Home" if home_score > away_score else "Away"
    })

    # --- Helper: Process Lineup & Calculate Position Totals ---
    def process_lineup_and_positions(lineup, team_name):
        team_bench_points = 0
        # Initialize position breakdown
        pos_breakdown = {"QB": 0, "RB": 0, "WR": 0, "TE": 0, "FLEX": 0, "D/ST": 0, "K": 0}
        
        for player in lineup:
            slot = player.slot_position
            
            if slot == 'BE':
                team_bench_points += player.points
            else:
                # Add to total active players list
                all_active_players.append({
                    "Name": player.name, "Points": player.points,
                    "Team": team_name, "PlayerID": player.playerId
                })
                
                # Add to position breakdown
                if slot in pos_breakdown:
                    pos_breakdown[slot] += player.points
                elif "RB" in slot or "WR" in slot: # Catch RB/WR slots if named differently
                     pos_breakdown["FLEX"] += player.points
                     
        return team_bench_points, pos_breakdown

    # Process Home
    home_bench, home_pos = process_lineup_and_positions(game.home_lineup, home_team)
    bench_data.append({"Team": home_team, "Unrealized Gains": home_bench})
    
    # Process Away
    away_bench, away_pos = process_lineup_and_positions(game.away_lineup, away_team)
    bench_data.append({"Team": away_team, "Unrealized Gains": away_bench})

    # Save detailed data for the Deep Dive Chart
    # We transform the dicts into a list of rows for the dataframe
    matchup_pos_data = []
    for pos, pts in home_pos.items():
        matchup_pos_data.append({"Position": pos, "Points": pts, "Team": home_team})
    for pos, pts in away_pos.items():
        matchup_pos_data.append({"Position": pos, "Points": pts, "Team": away_team})
        
    matchup_details.append({
        "Home": home_team, "Away": away_team,
        "Home Score": home_score, "Away Score": away_score,
        "Data": matchup_pos_data
    })

# --- Final Calculations ---
df_bench = pd.DataFrame(bench_data).sort_values(by="Unrealized Gains", ascending=False)
if not df_bench.empty:
    biggest_bench_warmer = {"team": df_bench.iloc[0]["Team"], "points": df_bench.iloc[0]["Unrealized Gains"]}

top_performers = pd.DataFrame(all_active_players).sort_values(by="Points", ascending=False).head(5)

power_rankings = league.power_rankings(week=selected_week)
rank_data = [{"Rank": i+1, "Team": t[1].team_name, "Power Score": float(t[0])} for i, t in enumerate(power_rankings)]
df_rank = pd.DataFrame(rank_data)

# ------------------------------------------------------------------
# 5. AI ENGINE
# ------------------------------------------------------------------
def get_ai_recap(week, tragic_hero, bandit, bench_king, top_player, rank_1):
    if not openai_key: return "⚠️ Please add 'openai_key' to secrets."
    
    client = OpenAI(api_key=openai_key)
    prompt = f"""
    You are a high-energy, sophisticated sportscaster for 'Luxury League'.
    User's Team: "14 Jettas".
    Write a 2-paragraph 'Breaking News' segment for Week {week}.
    
    DATA:
    - Tragic Hero (Good score, lost): {tragic_hero['team']} ({tragic_hero['score']} pts)
    - Lucky Bandit (Bad score, won): {bandit['team']} ({bandit['score']} pts)
    - Efficiency Fail (Bench pts): {bench_king['team']} ({bench_king['points']} pts wasted)
    - MVP: {top_player}
    - #1 Rank: {rank_1}
    
    STYLE: Financial metaphors (ROI, liquidity, assets). Mock the Efficiency Fail.
    """
    try:
        response = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=500)
        return response.choices[0].message.content
    except Exception as e: return f"Analyst Offline: {e}"

# ------------------------------------------------------------------
# 6. DASHBOARD UI
# ------------------------------------------------------------------
st.title(f"🏛️ Luxury League: Week {selected_week}")

# --- AI ANALYSIS ---
if not df_rank.empty and not top_performers.empty:
    if "recap_text" not in st.session_state:
        with st.spinner("🎙️ Studio Analyst is reviewing the game tape..."):
            top_player_str = f"{top_performers.iloc[0]['Name']} ({top_performers.iloc[0]['Points']})"
            st.session_state["recap_text"] = get_ai_recap(selected_week, highest_score_loser, lowest_score_winner, biggest_bench_warmer, top_player_str, df_rank.iloc[0]['Team'])
    
    st.markdown(f'<div class="studio-box"><h3>🎙️ The Studio Report</h3>{st.session_state["recap_text"]}</div>', unsafe_allow_html=True)
    if st.button("🔄 Refresh Analysis"): del st.session_state["recap_text"]; st.rerun()

# --- AWARDS ---
c1, c2, c3 = st.columns(3)
c1.metric("💔 Tragic Hero", f"{highest_score_loser['score']}", f"{highest_score_loser['team']}")
c2.metric("🔫 The Bandit", f"{lowest_score_winner['score']}", f"{lowest_score_winner['team']}")
c3.metric("📉 The Speculator", f"{biggest_bench_warmer['points']}", f"{biggest_bench_warmer['team']}")

st.divider()

# --- TOP PLAYERS ---
st.markdown("### 🌟 The Week's Elite")
cols = st.columns(5)
if not top_performers.empty:
    for i, (index, player) in enumerate(top_performers.iterrows()):
        with cols[i]:
            st.image(f"https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{player['PlayerID']}.png&w=350&h=254")
            st.markdown(f"**{player['Name']}**")
            st.caption(f"{player['Points']} pts")

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📜 The Ledger", "📈 The Hierarchy", "🔎 The Audit"])

with tab1:
    st.subheader("Weekly Matchups (Detailed)")
    # Loop through our detailed matchups instead of just showing one big table
    for match in matchup_details:
        # Create a container for each game
        with st.container():
            # Create a header like "Team A (100) vs Team B (90)"
            match_label = f"{match['Home']} ({match['Home Score']}) vs {match['Away']} ({match['Away Score']})"
            
            # The Expander - Click to open
            with st.expander(f"🏈 {match_label}"):
                # 1. Comparison Chart
                st.caption("Positional Warfare (Points by Position)")
                df_match = pd.DataFrame(match['Data'])
                
                # We use a grouped bar chart
                st.bar_chart(
                    df_match,
                    x="Position",
                    y="Points",
                    color="Team",
                    stack=False # Side by side bars
                )

with tab2:
    if not df_rank.empty:
        try:
            top_team = next(t for t in league.teams if t.team_name == df_rank.iloc[0]["Team"])
            st.image(top_team.logo_url, width=100, caption="Rank #1")
        except: pass
        st.bar_chart(df_rank.set_index("Team")["Power Score"], color="#FFD700")

with tab3:
    st.subheader("Efficiency Audit")
    st.bar_chart(df_bench.set_index("Team"), color="#333333")
