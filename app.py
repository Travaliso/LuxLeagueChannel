import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_lottie import st_lottie
from thefuzz import process
import logic
import ui
import intelligence

# ------------------------------------------------------------------
# 1. SETUP & INIT
# ------------------------------------------------------------------
st.set_page_config(page_title="Luxury League Dashboard", page_icon="💎", layout="wide")
ui.inject_luxury_css()

# Constants
START_YEAR = 2021

# Load Secrets
try:
    LEAGUE_ID = st.secrets["league_id"]
    SWID = st.secrets["swid"]
    ESPN_S2 = st.secrets["espn_s2"]
    OPENAI_KEY = st.secrets.get("openai_key")
    ODDS_API_KEY = st.secrets.get("odds_api_key")
    YEAR = 2025
    
    league = logic.get_league(LEAGUE_ID, YEAR, ESPN_S2, SWID)
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.stop()

# Load Assets
lotties = {
    'loading': ui.load_lottieurl("https://lottie.host/5a882010-89b6-45bc-8a4d-06886982f8d8/WfK7bXoGqj.json"),
    'forecast': ui.load_lottieurl("https://lottie.host/936c69f6-0b89-4b68-b80c-0390f777c5d7/C0Z2y3S0bM.json"),
    'trophy': ui.load_lottieurl("https://lottie.host/362e7839-2425-4c75-871d-534b82d02c84/hL9w4jR9aF.json"),
    'trade': ui.load_lottieurl("https://lottie.host/e65893a7-e54e-4f0b-9366-0749024f2b1d/z2Xg6c4h5r.json"),
    'wire': ui.load_lottieurl("https://lottie.host/4e532997-5b65-4f4c-8b2b-077555627798/7Q9j7Z9g9z.json"),
    'lab': ui.load_lottieurl("https://lottie.host/49907932-975d-453d-b8f1-2d6408468123/bF2y8T8k7s.json")
}

# ------------------------------------------------------------------
# 2. SIDEBAR & NAVIGATION
# ------------------------------------------------------------------
st.sidebar.title("🥂 The Concierge")
current_week = league.current_week - 1
if current_week == 0: current_week = 1
selected_week = st.sidebar.slider("Select Week", 1, current_week, current_week)
st.sidebar.markdown("---")

P_LEDGER, P_HIERARCHY, P_AUDIT, P_HEDGE, P_LAB, P_FORECAST, P_NEXT, P_PROP, P_DEAL, P_DARK, P_TROPHY, P_VAULT = "📜 The Ledger", "📈 The Hierarchy", "🔎 The Audit", "💎 The Hedge Fund", "🧬 The Lab", "🔮 The Forecast", "🚀 Next Week", "📊 The Prop Desk", "🤝 The Dealmaker", "🕵️ The Dark Pool", "🏆 Trophy Room", "⏳ The Vault"
page_options = [P_LEDGER, P_HIERARCHY, P_AUDIT, P_HEDGE, P_LAB, P_FORECAST, P_NEXT, P_PROP, P_DEAL, P_DARK, P_TROPHY, P_VAULT]
selected_page = st.sidebar.radio("Navigation", page_options, label_visibility="collapsed")

st.sidebar.markdown("---")
if st.sidebar.button("📄 Generate PDF Report"):
    with ui.luxury_spinner("Compiling Intelligence Report..."):
        if "recap" not in st.session_state: st.session_state["recap"] = "Analysis Generated."
        if "awards" not in st.session_state: st.session_state["awards"] = logic.calculate_season_awards(league, current_week)
        if "playoff_odds" not in st.session_state: st.session_state["playoff_odds"] = logic.run_monte_carlo_simulation(league)
        
        pdf = ui.PDF()
        pdf.add_page()
        pdf.chapter_title(f"WEEK {selected_week} EXECUTIVE BRIEFING")
        pdf.chapter_body(st.session_state["recap"].replace("*", "").replace("#", ""))
        awards = st.session_state["awards"]
        pdf.chapter_title("THE TROPHY ROOM")
        if awards['MVP']: pdf.chapter_body(f"MVP: {awards['MVP']['Name']} ({awards['MVP']['Points']:.1f} pts)")
        
        html = ui.create_download_link(pdf.output(dest="S").encode("latin-1"), f"Luxury_League_Week_{selected_week}.pdf")
        st.sidebar.markdown(html, unsafe_allow_html=True)

# ------------------------------------------------------------------
# 3. DATA PIPELINE
# ------------------------------------------------------------------
if 'box_scores' not in st.session_state or st.session_state.get('week') != selected_week:
    with ui.luxury_spinner(f"Accessing Week {selected_week} Data..."):
        st.session_state['box_scores'] = league.box_scores(week=selected_week)
        st.session_state['week'] = selected_week
    st.rerun()

box_scores = st.session_state['box_scores']
matchup_data, efficiency_data, all_active_players, bench_highlights = [], [], [], []

for game in box_scores:
    home, away = game.home_team, game.away_team
    # Helper for roster parsing
    def get_roster_data(lineup, team_name):
        starters, bench, p_start, p_bench = [], [], 0, 0
        for p in lineup:
            info = {"Name": p.name, "Score": p.points, "Pos": p.slot_position}
            status = getattr(p, 'injuryStatus', 'ACTIVE')
            status_str = str(status).upper().replace("_", " ") if status else "ACTIVE"
            is_injured = any(k in status_str for k in ['OUT', 'IR', 'RESERVE', 'SUSPENDED'])
            
            if p.slot_position == 'BE':
                bench.append(info); p_bench += p.points
                if p.points > 15: bench_highlights.append({"Team": team_name, "Player": p.name, "Score": p.points})
            else:
                starters.append(info); p_start += p.points
                if not is_injured: all_active_players.append({"Name": p.name, "Points": p.points, "Team": team_name, "ID": p.playerId})
        return starters, bench, p_start, p_bench

    h_r, h_br, h_s, h_b = get_roster_data(game.home_lineup, home.team_name)
    a_r, a_br, a_s, a_b = get_roster_data(game.away_lineup, away.team_name)
    matchup_data.append({"Home": home.team_name, "Home Score": game.home_score, "Home Logo": ui.get_logo_url(home), "Home Roster": h_r, "Away": away.team_name, "Away Score": game.away_score, "Away Logo": ui.get_logo_url(away), "Away Roster": a_r})
    efficiency_data.append({"Team": home.team_name, "Starters": h_s, "Bench": h_b, "Total Potential": h_s + h_b})
    efficiency_data.append({"Team": away.team_name, "Starters": a_s, "Bench": a_b, "Total Potential": a_s + a_b})

df_eff = pd.DataFrame(efficiency_data).sort_values(by="Total Potential", ascending=False)
df_players = pd.DataFrame(all_active_players).sort_values(by="Points", ascending=False).head(5)
df_bench_stars = pd.DataFrame(bench_highlights).sort_values(by="Score", ascending=False).head(5)

# ------------------------------------------------------------------
# 4. DASHBOARD UI (ROUTER)
# ------------------------------------------------------------------
st.title(f"🏛️ Luxury League Protocol: Week {selected_week}")

# HERO ROW
st.markdown("### 🌟 Weekly Elite")
h1, h2, h3 = st.columns(3)
top_3 = df_players.head(3).reset_index(drop=True)
if len(top_3) >= 1: ui.render_hero_card(h1, top_3.iloc[0])
if len(top_3) >= 2: ui.render_hero_card(h2, top_3.iloc[1])
if len(top_3) >= 3: ui.render_hero_card(h3, top_3.iloc[2])
st.markdown("---")

# --- PAGES ---
if selected_page == P_LEDGER:
    if "recap" not in st.session_state:
        with ui.luxury_spinner("Analyst is reviewing portfolios..."): 
            st.session_state["recap"] = intelligence.get_weekly_recap(OPENAI_KEY, selected_week, df_eff.iloc[0]['Team'])
    st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ The Studio Report</h3>{st.session_state["recap"]}</div>', unsafe_allow_html=True)
    st.header("Weekly Transactions")
    c1, c2 = st.columns(2)
    for i, m in enumerate(matchup_data):
        col = c1 if i % 2 == 0 else c2
        with col:
            st.markdown(f"""<div class="luxury-card" style="padding: 15px; margin-bottom: 10px;"><div style="display: flex; justify-content: space-between; align-items: center;"><div style="text-align: center; width: 40%;"><img src="{m['Home Logo']}" width="50" style="border-radius: 50%; border: 2px solid #00C9FF; padding: 2px;"><div style="font-weight: 700; color: white; font-size: 0.9em; margin-top: 5px;">{m['Home']}</div><div style="font-size: 20px; color: #00C9FF; font-weight: 800;">{m['Home Score']}</div></div><div style="color: #a0aaba; font-size: 10px; font-weight: bold;">VS</div><div style="text-align: center; width: 40%;"><img src="{m['Away Logo']}" width="50" style="border-radius: 50%; border: 2px solid #0072ff; padding: 2px;"><div style="font-weight: 700; color: white; font-size: 0.9em; margin-top: 5px;">{m['Away']}</div><div style="font-size: 20px; color: #00C9FF; font-weight: 800;">{m['Away Score']}</div></div></div></div>""", unsafe_allow_html=True)
            with st.expander(f"📉 View Lineups"):
                # Convert Roster list to DF
                max_len = max(len(m['Home Roster']), len(m['Away Roster']))
                df_m = pd.DataFrame({
                    f"{m['Home']}": [p['Name'] for p in m['Home Roster']] + [''] * (max_len - len(m['Home Roster'])),
                    f"{m['Home']} Pts": [p['Score'] for p in m['Home Roster']] + [0] * (max_len - len(m['Home Roster'])),
                    f"{m['Away']} Pts": [p['Score'] for p in m['Away Roster']] + [0] * (max_len - len(m['Away Roster'])),
                    f"{m['Away']}": [p['Name'] for p in m['Away Roster']] + [''] * (max_len - len(m['Away Roster']))
                })
                st.dataframe(df_m, use_container_width=True, hide_index=True)

elif selected_page == P_HIERARCHY:
    if "rank_comm" not in st.session_state:
        with ui.luxury_spinner("Analyzing hierarchy..."): 
            st.session_state["rank_comm"] = intelligence.get_rankings_commentary(OPENAI_KEY, df_eff.iloc[0]['Team'], df_eff.iloc[-1]['Team'])
    st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ Pundit\'s Take</h3>{st.session_state["rank_comm"]}</div>', unsafe_allow_html=True)
    st.header("Power Rankings")
    st.bar_chart(df_eff.set_index("Team")["Total Potential"], color="#00C9FF")

elif selected_page == P_AUDIT:
    st.header("Efficiency Audit")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_eff["Team"], y=df_eff["Starters"], name='Starters', marker_color='#00C9FF'))
    fig.add_trace(go.Bar(x=df_eff["Team"], y=df_eff["Bench"], name='Bench Waste', marker_color='rgba(255, 255, 255, 0.1)'))
    fig.update_layout(barmode='stack', plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aaba", title="Total Potential", height=500)
    st.plotly_chart(fig, use_container_width=True)
    if not df_bench_stars.empty: st.markdown("#### 🚨 'Should Have Started'"); st.dataframe(df_bench_stars, use_container_width=True, hide_index=True)

elif selected_page == P_HEDGE:
    st.header("Market Analytics")
    if "df_advanced" not in st.session_state:
        if st.button("🚀 Analyze Market Data"):
            with ui.luxury_spinner("Compiling Assets..."): st.session_state["df_advanced"] = logic.calculate_heavy_analytics(league, current_week); st.rerun()
    else:
        fig = px.scatter(st.session_state["df_advanced"], x="Power Score", y="Wins", text="Team", size="Points For", color="Luck Rating", color_continuous_scale=["#7209b7", "#4361ee", "#4cc9f0"], title="Luck Matrix", height=600)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aaba")
        fig.update_traces(marker=dict(size=15, line=dict(width=2, color='White')), textposition='top center')
        st.plotly_chart(fig, use_container_width=True)

elif selected_page == P_LAB:
    c1, c2 = st.columns([3, 1])
    with c1: st.header("🧬 The Lab (Next Gen Biometrics)")
    with c2:
         if st.button("🧪 Analyze Roster"):
             with ui.luxury_spinner("Calibrating Satellites..."): st.session_state["trigger_lab"] = True; st.rerun()
    with st.expander("🔎 Biometric Legend", expanded=False): st.info("WOPR: Weighted Opp. | CPOE: Completion % Over Exp | RYOE: Rush Yards Over Exp")
    
    target_team = st.selectbox("Select Test Subject:", [t.team_name for t in league.teams])
    if st.session_state.get("trigger_lab"):
        roster_obj = next(t for t in league.teams if t.team_name == target_team).roster
        st.session_state["ngs_data"] = logic.analyze_nextgen_metrics_v3(roster_obj, YEAR)
        st.session_state["trigger_lab"] = False
        st.rerun()
    if "ngs_data" in st.session_state:
        if not st.session_state["ngs_data"].empty:
            cols = st.columns(2)
            for i, row in st.session_state["ngs_data"].iterrows():
                with cols[i % 2]:
                    st.markdown(f"""<div class="luxury-card" style="border-left: 4px solid #00C9FF; display: flex; align-items: center;"><div style="flex:1;"><h4 style="color:white; margin:0;">{row['Player']}</h4><div style="color:#00C9FF;">{row['Verdict']}</div></div><div style="text-align:right;"><div style="font-size:1.4em; font-weight:bold; color:white;">{row['Value']}</div><div style="color:#92FE9D; font-size:0.8em;">{row['Alpha Stat']}</div></div></div>""", unsafe_allow_html=True)
        else: st.info("No Next Gen data available.")

elif selected_page == P_FORECAST:
    st.header("The Crystal Ball")
    if "playoff_odds" not in st.session_state:
        if st.button("🎲 Run Simulation"):
            with ui.luxury_spinner("Running Monte Carlo simulations..."): st.session_state["playoff_odds"] = logic.run_monte_carlo_simulation(league); st.rerun()
    else:
        st.dataframe(st.session_state["playoff_odds"], use_container_width=True, hide_index=True, column_config={"Playoff Odds": st.column_config.ProgressColumn("Prob", format="%.1f%%", min_value=0, max_value=100)})
        if st.button("🔄 Re-Simulate"): del st.session_state["playoff_odds"]; st.rerun()

elif selected_page == P_NEXT:
    try:
        next_week = league.current_week
        box = league.box_scores(week=next_week)
        games = [{"home": g.home_team.team_name, "away": g.away_team.team_name, "spread": f"{abs(g.home_projected-g.away_projected):.1f}"} for g in box]
        if "next_week_comm" not in st.session_state:
            with ui.luxury_spinner("Checking Vegas lines..."): st.session_state["next_week_comm"] = intelligence.get_next_week_preview(OPENAI_KEY, games)
        st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ Vegas Insider</h3>{st.session_state["next_week_comm"]}</div>', unsafe_allow_html=True)
        st.header("Matchups")
        c1, c2 = st.columns(2)
        for i, g in enumerate(box):
             with c1 if i % 2 == 0 else c2:
                 st.markdown(f"""<div class="luxury-card" style="padding: 15px;"><div style="display:flex; justify-content:space-between; text-align:center;"><div style="flex:2; color:white;"><b>{g.home_team.team_name}</b><br><span style="color:#00C9FF;">{g.home_projected:.1f}</span></div><div style="flex:1; color:#a0aaba; font-size:0.8em;">VS</div><div style="flex:2; color:white;"><b>{g.away_team.team_name}</b><br><span style="color:#92FE9D;">{g.away_projected:.1f}</span></div></div></div>""", unsafe_allow_html=True)
    except: st.info("Projections unavailable.")

elif selected_page == P_PROP:
    st.header("📊 The Prop Desk")
    if not ODDS_API_KEY: st.warning("Missing Odds API Key")
    else:
        if "vegas_data" not in st.session_state:
            with ui.luxury_spinner("Calling Vegas..."): st.session_state["vegas_data"] = logic.get_vegas_props(ODDS_API_KEY)
        df_v = st.session_state["vegas_data"]
        if df_v is not None and not df_v.empty:
             if "Status" in df_v.columns: st.warning("📉 Market Closed (Tuesday/Wednesday).")
             else:
                 # Display logic here (Match fuzzy names)
                 st.dataframe(df_v) # Placeholder for full matching logic
        else: st.error("Could not fetch odds.")

elif selected_page == P_DEAL:
    st.header("🤝 The AI Dealmaker")
    c1, c2 = st.columns(2)
    with c1: t1 = st.selectbox("Select Team A", [t.team_name for t in league.teams], index=0)
    with c2: t2 = st.selectbox("Select Team B", [t.team_name for t in league.teams], index=1)
    if st.button("🤖 Generate Trade"):
        with ui.luxury_spinner("Analyzing..."):
            ta = next(t for t in league.teams if t.team_name == t1)
            tb = next(t for t in league.teams if t.team_name == t2)
            ra = [f"{p.name} ({p.position})" for p in ta.roster]
            rb = [f"{p.name} ({p.position})" for p in tb.roster]
            prop = intelligence.get_ai_trade_proposal(OPENAI_KEY, t1, t2, ra, rb)
            st.markdown(f'<div class="luxury-card studio-box"><h3>Proposed Deal</h3>{prop}</div>', unsafe_allow_html=True)

elif selected_page == P_DARK:
    st.header("🕵️ The Dark Pool")
    has_data = "dark_pool_data" in st.session_state
    if not has_data:
        if st.button("🔭 Scan Wire"):
             with ui.luxury_spinner("Scouting..."):
                 df_pool = logic.scan_dark_pool(league)
                 st.session_state["dark_pool_data"] = df_pool
                 if not df_pool.empty:
                     p_str = ", ".join([f"{r['Name']} ({r['Position']})" for i, r in df_pool.iterrows()])
                     st.session_state["scout_rpt"] = intelligence.get_ai_scouting_report(OPENAI_KEY, p_str)
                 st.rerun()
    else:
        if st.button("🔄 Rescan"): del st.session_state["dark_pool_data"]; st.rerun()
        if "scout_rpt" in st.session_state: st.markdown(f'<div class="luxury-card studio-box"><h3>📝 Scout\'s Notebook</h3>{st.session_state["scout_rpt"]}</div>', unsafe_allow_html=True)
        st.dataframe(st.session_state["dark_pool_data"], use_container_width=True)

elif selected_page == P_TROPHY:
    if "awards" not in st.session_state:
        if st.button("🏅 Unveil Awards"):
            with ui.luxury_spinner("Engraving..."):
                st.session_state["awards"] = logic.calculate_season_awards(league, current_week)
                aw = st.session_state["awards"]
                st.session_state["season_comm"] = intelligence.get_season_retrospective(OPENAI_KEY, aw['MVP']['Name'], aw['Best Manager']['Team'])
                st.rerun()
    else:
        aw = st.session_state["awards"]
        if "season_comm" in st.session_state: st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ State of the League</h3>{st.session_state["season_comm"]}</div>', unsafe_allow_html=True)
        st.divider()
        # Podium rendering... (Use previous code for full HTML podium)
        st.write("🏆 Podium Loaded (See previous code for full HTML)")
        
elif selected_page == P_VAULT:
    st.header("⏳ The Dynasty Vault")
    if "dynasty_lead" not in st.session_state:
        if st.button("🔓 Unlock Vault"):
            with ui.luxury_spinner("Time Traveling..."):
                df_raw = logic.get_dynasty_data(LEAGUE_ID, ESPN_S2, SWID, YEAR, START_YEAR)
                st.session_state["dynasty_lead"] = logic.process_dynasty_leaderboard(df_raw)
                st.session_state["dynasty_raw"] = df_raw
                st.rerun()
    else:
        st.dataframe(st.session_state["dynasty_lead"], use_container_width=True)
        fig = px.line(st.session_state["dynasty_raw"], x="Year", y="Wins", color="Manager", markers=True)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aaba")
        st.plotly_chart(fig, use_container_width=True)
