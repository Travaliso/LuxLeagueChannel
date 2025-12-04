import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import luxury_utils as utils

# ==============================================================================
# 1. SETUP & CONFIGURATION
# ==============================================================================
st.set_page_config(page_title="Luxury League", page_icon="💎", layout="wide")
utils.inject_luxury_css()

# ==============================================================================
# 2. LEAGUE CONNECTION
# ==============================================================================
try:
    LEAGUE_ID = st.secrets["league_id"]
    SWID = st.secrets["swid"]
    ESPN_S2 = st.secrets["espn_s2"]
    OPENAI_KEY = st.secrets.get("openai_key")
    YEAR = 2025
    
    league = utils.get_league(LEAGUE_ID, YEAR, ESPN_S2, SWID)
except Exception as e:
    st.error(f"🔒 Connection Error: {e}")
    st.stop()

# ==============================================================================
# 3. SIDEBAR NAVIGATION
# ==============================================================================
st.sidebar.title("🥂 The Concierge")
current_week = league.current_week - 1
if current_week == 0: current_week = 1
selected_week = st.sidebar.slider("Select Week", 1, current_week, current_week)
st.sidebar.markdown("---")

P_LEDGER = "📜 The Ledger"
P_HIERARCHY = "📈 The Hierarchy"
P_FORECAST = "🔮 The Forecast"
P_MULTI = "🌌 The Multiverse"

page_options = [P_LEDGER, P_HIERARCHY, P_FORECAST, P_MULTI]
selected_page = st.sidebar.radio("Navigation", page_options, label_visibility="collapsed")

# ==============================================================================
# 4. DATA PIPELINE
# ==============================================================================
if 'box_scores' not in st.session_state or st.session_state.get('week') != selected_week:
    with utils.luxury_spinner(f"Accessing Week {selected_week} Data..."):
        st.session_state['box_scores'] = league.box_scores(week=selected_week)
        st.session_state['week'] = selected_week
    st.rerun()

box_scores = st.session_state['box_scores']

# Calculate simple efficiency for displays
efficiency_data = []
for game in box_scores:
    # Simplified data gathering to prevent errors
    efficiency_data.append({"Team": game.home_team.team_name, "Score": game.home_score})
    efficiency_data.append({"Team": game.away_team.team_name, "Score": game.away_score})
df_eff = pd.DataFrame(efficiency_data).sort_values(by="Score", ascending=False)

# ==============================================================================
# 5. DASHBOARD UI
# ==============================================================================
st.title(f"🏛️ Luxury League: Week {selected_week}")

if selected_page == P_LEDGER:
    st.header("Weekly Matchups")
    for game in box_scores:
        st.markdown(f"""
        <div class="luxury-card">
            <div style="display: flex; justify-content: space-between; align-items: center; text-align: center;">
                <div style="flex: 1;">
                    <div style="font-weight: bold; font-size: 1.1em;">{game.home_team.team_name}</div>
                    <div style="font-size: 1.5em; color: #00C9FF;">{game.home_score}</div>
                </div>
                <div style="font-size: 0.8em; color: #aaa; padding: 0 10px;">VS</div>
                <div style="flex: 1;">
                    <div style="font-weight: bold; font-size: 1.1em;">{game.away_team.team_name}</div>
                    <div style="font-size: 1.5em; color: #00C9FF;">{game.away_score}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

elif selected_page == P_HIERARCHY:
    st.header("Power Rankings")
    if "df_advanced" not in st.session_state:
        st.session_state["df_advanced"] = utils.calculate_heavy_analytics(league, current_week)
    
    df = st.session_state["df_advanced"]
    st.dataframe(
        df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Power Score": st.column_config.NumberColumn(format="%.1f"),
            "Luck Rating": st.column_config.ProgressColumn(min_value=-5, max_value=5, format="%+.1f")
        }
    )

elif selected_page == P_FORECAST:
    st.header("The Crystal Ball")
    if "playoff_odds" not in st.session_state:
        if st.button("🎲 Run Simulation"):
            with utils.luxury_spinner("Simulating Season..."): 
                st.session_state["playoff_odds"] = utils.run_monte_carlo_simulation(league)
                st.rerun()
    else:
        st.dataframe(
            st.session_state["playoff_odds"], 
            use_container_width=True, 
            hide_index=True, 
            column_config={
                "Playoff Odds": st.column_config.ProgressColumn(
                    "Prob", 
                    format="%.1f%%", 
                    min_value=0, 
                    max_value=1
                )
            }
        )

elif selected_page == P_MULTI:
    st.header("🌌 The Multiverse")
    st.info("What needs to happen for you to make the playoffs? Force specific winners below and re-run the odds.")
    
    # 1. Get Baseline Odds if not present
    if "base_odds" not in st.session_state:
        with utils.luxury_spinner("Calculating Baseline..."): 
            st.session_state["base_odds"] = utils.run_monte_carlo_simulation(league)
    
    # 2. Controls
    box = league.box_scores(week=league.current_week)
    forced_winners = []
    
    with st.form("multiverse_form"):
        st.markdown("### 🔮 Pick This Week's Winners")
        # Use columns for desktop, but simple logic for mobile
        for i, g in enumerate(box):
            home_n = g.home_team.team_name
            away_n = g.away_team.team_name
            choice = st.radio(f"{home_n} vs {away_n}", ["Simulate", f"{home_n} Wins", f"{away_n} Wins"], key=f"g{i}", horizontal=True)
            
            if "Simulate" not in choice:
                forced_winners.append(home_n if home_n in choice else away_n)
                
        run_sim = st.form_submit_button("🚀 Update Probabilities", type="primary")

    # 3. Results
    if run_sim:
        with utils.luxury_spinner("Crunching Scenarios..."):
            res = utils.run_multiverse_simulation(league, forced_winners)
            base = st.session_state["base_odds"][["Team", "Playoff Odds"]].rename(columns={"Playoff Odds": "Base"})
            
            # Merge and Calculate Impact
            final = pd.merge(res, base, on="Team", how="outer").fillna(0)
            final["Impact"] = final["New Odds"] - final["Base"]
            st.session_state["multi_res"] = final.sort_values(by="New Odds", ascending=False)

    if "multi_res" in st.session_state:
        st.markdown("### 🎲 Scenario Results")
        # MOBILE FIX: Use dataframe with container width so it scrolls horizontally on phone
        st.dataframe(
            st.session_state["multi_res"], 
            use_container_width=True, 
            hide_index=True, 
            column_config={
                "New Odds": st.column_config.ProgressColumn("New Odds", min_value=0, max_value=1.0, format="%.1f%%"),
                "Base": st.column_config.NumberColumn("Base", format="%.1f%%"),
                "Impact": st.column_config.NumberColumn("Impact", format="%+.1f%%")
            }
        )
