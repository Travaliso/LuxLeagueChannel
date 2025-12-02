import streamlit as st
from espn_api.football import League
import pandas as pd

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
