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
    
    /* Studio Analysis Box */
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
    openai_key = st.secrets.get("openai_key") # Safe get in case not set
    year = 2025
    
    league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
except Exception:
    st.error("🔒 Security Clearance Failed. Check Secrets.")
    st.stop()

# ------------------------------------------------------------------
# 3. SIDEBAR & FILTERS
# ------------------------------------------------------------------
st.sidebar.title("🥂 The Concierge")
current_week = league.current_week - 1
if current_week == 0: current_week = 1
selected_week = st.sidebar.slider("Select Week", 1, current_week, current_week)

# ------------------------------------------------------------------
# 4. DATA PROCESSING
# ------------------------------------------------------------------
box_scores = league.box_scores(week=selected_week)

score_data = []
all_active_players = [] 
bench_data = []

highest_score_loser = {"score": -1, "team": "N/A"}
lowest_score_winner = {"score": 999, "team": "N/A"}
biggest_bench_warmer = {"points": -1, "team": "N/A"}

# Matchup Loop
for game in box_scores:
    home_team = game.home_team.team_name
    away_team = game.away_team.team_name
    home_score = game.home_score
    away_score = game.away_score
    
    if home_score > away_score:
        winner, winner_score = home_team, home_score
        loser, loser_score = away_team, away_score
    else:
        winner, winner_score = away_team, away_score
        loser, loser_score = home_team, home_score

    # Award Tracking
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

    # Bench/Player Helper
    def process_lineup(lineup, team_name):
        team_bench_points = 0
        for player in lineup:
            if player.slot_position == 'BE':
                team_bench_points += player.points
            else:
                all_active_players.append({
                    "Name": player.name, "Points": player.points,
                    "Team": team_name, "PlayerID": player.playerId
                })
        return team_bench_points

    home_bench = process_lineup(game.home_lineup, home_team)
    bench_data.append({"Team": home_team, "Unrealized Gains": home_bench})
    away_bench = process_lineup(game.away_lineup, away_team)
    bench_data.append({"Team": away_team, "Unrealized Gains": away_bench})

# Final Calculations
df_bench = pd.DataFrame(bench_data).sort_values(by="Unrealized Gains", ascending=False)
if not df_bench.empty:
    biggest_bench_warmer = {"team": df_bench.iloc[0]["Team"], "points": df_bench.iloc[0]["Unrealized Gains"]}

top_performers = pd.DataFrame(all_active_players).sort_values(by="Points", ascending=False).head(5)

power_rankings = league.power_rankings(week=selected_week)
rank_data = [{"Rank": i+1, "Team": t[1].team_name, "Power Score": float(t[0])} for i, t in enumerate(power_rankings)]
df_rank = pd.DataFrame(rank_data)

# ------------------------------------------------------------------
# 5. AI NARRATIVE ENGINE
# ------------------------------------------------------------------
def get_ai_recap(week, tragic_hero, bandit, bench_king, top_player, rank_1):
    if not openai_key:
        return "⚠️ Please add 'openai_key' to your secrets.toml to enable AI Studio Analysis."
    
    client = OpenAI(api_key=openai_key)
    
    # The Prompt Engineering
    prompt = f"""
    You are a high-energy, slightly arrogant, sophisticated sportscaster for a high-end fantasy league called 'Luxury League'.
    Write a 3-sentence 'Breaking News' ticker update for Week {week}.
    
    Here is the data:
    - The Tragic Hero (Good score but lost): {tragic_hero['team']} ({tragic_hero['score']} pts)
    - The Lucky Bandit (Bad score but won): {bandit['team']} ({bandit['score']} pts)
    - Worst Manager (Left points on bench): {bench_king['team']} ({bench_king['points']} pts wasted)
    - League MVP: {top_player}
    - Current King of the Hill (Rank #1): {rank_1}
    
    Style: Use financial metaphors (assets, liquidity, dividends) mixed with sports trash talk. Be ruthless but classy.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Cost effective model
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI Analyst is on coffee break. (Error: {e})"

# ------------------------------------------------------------------
# 6. DASHBOARD UI
# ------------------------------------------------------------------
st.title(f"🏛️ Luxury League: Week {selected_week}")

# --- AI ANALYSIS SECTION ---
# Only run this if we have data to feed it
if not df_rank.empty and not top_performers.empty:
    top_player_name = f"{top_performers.iloc[0]['Name']} ({top_performers.iloc[0]['Points']})"
    rank_1_team = df_rank.iloc[0]['Team']
    
    # We use session state so it doesn't re-generate every time you click a tab
    if "recap_text" not in st.session_state:
        with st.spinner("🎙️ Studio Analyst is reviewing the game tape..."):
            st.session_state["recap_text"] = get_ai_recap(
                selected_week, highest_score_loser, lowest_score_winner, 
                biggest_bench_warmer, top_player_name, rank_1_team
            )

    st.markdown(f"""
    <div class="studio-box">
        <h3>🎙️ The Studio Report</h3>
        {st.session_state["recap_text"]}
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 Refresh Analysis"):
        del st.session_state["recap_text"]
        st.rerun()

# --- AWARDS ---
col1, col2, col3 = st.columns(3)
col1.metric("💔 Tragic Hero", f"{highest_score_loser['score']}", f"{highest_score_loser['team']}")
col2.metric("🔫 The Bandit", f"{lowest_score_winner['score']}", f"{lowest_score_winner['team']}")
col3.metric("📉 The Speculator", f"{biggest_bench_warmer['points']}", f"{biggest_bench_warmer['team']}")

st.divider()

# --- TOP PLAYERS ---
st.markdown("### 🌟 The Week's Elite")
cols = st.columns(5)
if not top_performers.empty:
    for i, (index, player) in enumerate(top_performers.iterrows()):
        with cols[i]:
            headshot = f"https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{player['PlayerID']}.png&w=350&h=254"
            st.image(headshot)
            st.markdown(f"**{player['Name']}**")
            st.caption(f"{player['Points']} pts")

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📜 The Ledger", "📈 The Hierarchy", "🔎 The Audit"])

with tab1:
    st.dataframe(
        pd.DataFrame(score_data), use_container_width=True, hide_index=True,
        column_order=["Home Logo", "Home Team", "Score", "Away Team", "Away Logo", "Winner"],
        column_config={
            "Home Logo": st.column_config.ImageColumn(" ", width="small"),
            "Away Logo": st.column_config.ImageColumn(" ", width="small"),
            "Score": st.column_config.TextColumn("Final Score", help="Official box score"),
            "Winner": st.column_config.TextColumn("Victor", width="small")
        }
    )

with tab2:
    if not df_rank.empty:
        top_dog = df_rank.iloc[0]
        try:
            top_team_obj = next(t for t in league.teams if t.team_name == top_dog["Team"])
            top_logo = top_team_obj.logo_url
        except: top_logo = ""
        
        c1, c2 = st.columns([1, 4])
        with c1:
            if top_logo: st.image(top_logo, caption="Current #1")
        with c2:
            st.bar_chart(df_rank.set_index("Team")["Power Score"], color="#FFD700")

with tab3:
    st.subheader("The Manager Efficiency Audit")
    st.caption("Points left on the bench (Unrealized Gains)")
    st.bar_chart(df_bench.set_index("Team"), color="#333333")
