import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import luxury_utils as utils

# ==============================================================================
# 1. SETUP & CONFIGURATION
# ==============================================================================
st.set_page_config(page_title="Luxury League Dashboard", page_icon="💎", layout="wide")
utils.inject_luxury_css()
START_YEAR = 2021 

# ==============================================================================
# 2. LEAGUE CONNECTION
# ==============================================================================
try:
    LEAGUE_ID = st.secrets["league_id"]
    SWID = st.secrets["swid"]
    ESPN_S2 = st.secrets["espn_s2"]
    OPENAI_KEY = st.secrets.get("openai_key")
    ODDS_API_KEY = st.secrets.get("odds_api_key")
    YEAR = 2025
    league = utils.get_league(LEAGUE_ID, YEAR, ESPN_S2, SWID)
except Exception as e:
    st.error(f"🔒 Connection Error: {e}")
    st.stop()

# ==============================================================================
# 3. SIDEBAR NAVIGATION
# ==============================================================================
st.sidebar.title("🥂 The Concierge")
current_week = league.current_week
if current_week == 0: current_week = 1

selected_week = st.sidebar.slider("Select Week", 1, current_week, current_week)
st.sidebar.markdown("---")

P_LEDGER, P_HIERARCHY, P_AUDIT, P_HEDGE, P_IPO, P_LAB, P_FORECAST, P_MULTI, P_NEXT, P_PROP, P_DEAL, P_DARK, P_TROPHY, P_VAULT = "📜 The Ledger", "📈 The Hierarchy", "🔎 The Audit", "💎 The Hedge Fund", "📊 The IPO Audit", "🧬 The Lab", "🔮 The Forecast", "🌌 The Multiverse", "🚀 Next Week", "📊 The Prop Desk", "🤝 The Dealmaker", "🕵️ The Dark Pool", "🏆 Trophy Room", "⏳ The Vault"
page_options = [P_LEDGER, P_HIERARCHY, P_AUDIT, P_HEDGE, P_IPO, P_LAB, P_FORECAST, P_MULTI, P_NEXT, P_PROP, P_DEAL, P_DARK, P_TROPHY, P_VAULT]
selected_page = st.sidebar.radio("Navigation", page_options, label_visibility="collapsed")

if st.sidebar.button("📄 Generate PDF"):
    with utils.luxury_spinner("Compiling Intelligence Report..."):
        if "recap" not in st.session_state: st.session_state["recap"] = "Analysis Generated."
        awards = utils.calculate_season_awards(league, current_week)
        pdf = utils.PDF()
        pdf.add_page()
        pdf.chapter_title(f"WEEK {selected_week} BRIEFING")
        pdf.chapter_body(st.session_state.get("recap", "No Data").replace("*", ""))
        pdf.chapter_title("AWARDS")
        if awards['MVP']: pdf.chapter_body(f"MVP: {awards['MVP']['Name']}")
        html = utils.create_download_link(pdf.output(dest="S").encode("latin-1"), "Report.pdf")
        st.sidebar.markdown(html, unsafe_allow_html=True)

# ==============================================================================
# 4. DATA PIPELINE
# ==============================================================================
if 'box_scores' not in st.session_state or st.session_state.get('week') != selected_week:
    with utils.luxury_spinner(f"Accessing Week {selected_week} Data..."):
        st.session_state['box_scores'] = league.box_scores(week=selected_week)
        st.session_state['week'] = selected_week
    st.rerun()

box_scores = st.session_state['box_scores']
matchup_data, efficiency_data, all_active_players, bench_highlights = [], [], [], []

for game in box_scores:
    def get_roster_data(lineup, team_name):
        starters, bench = [], []
        for p in lineup:
            info = {"Name": p.name, "Score": p.points, "Pos": p.slot_position}
            status = getattr(p, 'injuryStatus', 'ACTIVE')
            is_injured = any(k in str(status).upper() for k in ['OUT', 'IR', 'RESERVE', 'SUSPENDED'])
            if p.slot_position == 'BE':
                bench.append(info)
                if p.points > 15: bench_highlights.append({"Team": team_name, "Player": p.name, "Score": p.points})
            else:
                starters.append(info)
                if not is_injured: all_active_players.append({"Name": p.name, "Points": p.points, "Team": team_name, "ID": p.playerId})
        return starters, bench

    h_r, h_br = get_roster_data(game.home_lineup, game.home_team.team_name)
    a_r, a_br = get_roster_data(game.away_lineup, game.away_team.team_name)
    
    matchup_data.append({"Home": game.home_team.team_name, "Home Score": game.home_score, "Home Logo": utils.get_logo(game.home_team), "Home Roster": h_r, "Away": game.away_team.team_name, "Away Score": game.away_score, "Away Logo": utils.get_logo(game.away_team), "Away Roster": a_r})
    
    h_p = sum(p['Score'] for p in h_r) + sum(p['Score'] for p in h_br)
    a_p = sum(p['Score'] for p in a_r) + sum(p['Score'] for p in a_br)
    efficiency_data.append({"Team": game.home_team.team_name, "Total Potential": h_p, "Starters": sum(p['Score'] for p in h_r), "Bench": sum(p['Score'] for p in h_br)})
    efficiency_data.append({"Team": game.away_team.team_name, "Total Potential": a_p, "Starters": sum(p['Score'] for p in a_r), "Bench": sum(p['Score'] for p in a_br)})

if efficiency_data: df_eff = pd.DataFrame(efficiency_data).sort_values(by="Total Potential", ascending=False)
else: df_eff = pd.DataFrame(columns=["Team", "Total Potential"])
if all_active_players: df_players = pd.DataFrame(all_active_players).sort_values(by="Points", ascending=False).head(5)
else: df_players = pd.DataFrame(columns=["Name", "Points", "Team", "ID"])
if bench_highlights: df_bench_stars = pd.DataFrame(bench_highlights).sort_values(by="Score", ascending=False).head(5)
else: df_bench_stars = pd.DataFrame(columns=["Team", "Player", "Score"])

# ==============================================================================
# 5. DASHBOARD UI
# ==============================================================================
st.title(f"🏛️ Luxury League Protocol: Week {selected_week}")

st.markdown("### 🌟 Weekly Elite")
h1, h2, h3 = st.columns(3)
if not df_players.empty:
    if len(df_players) >= 1: utils.render_hero_card(h1, df_players.iloc[0])
    if len(df_players) >= 2: utils.render_hero_card(h2, df_players.iloc[1])
    if len(df_players) >= 3: utils.render_hero_card(h3, df_players.iloc[2])
else: st.info("No player data available for this week yet.")
st.markdown("---")

if selected_page == P_LEDGER:
    st.header("📜 The Ledger")
    if "recap" not in st.session_state:
        with utils.luxury_spinner("Analyst is reviewing portfolios..."): 
            top_team = df_eff.iloc[0]['Team'] if not df_eff.empty else "League"
            st.session_state["recap"] = utils.get_weekly_recap(OPENAI_KEY, selected_week, top_team)
    st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ The Studio Report</h3>{st.session_state["recap"]}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    for i, m in enumerate(matchup_data):
        with c1 if i % 2 == 0 else c2:
            st.markdown(f"""<div class="luxury-card" style="padding: 15px;"><div style="display: flex; justify-content: space-between; align-items: center;"><div style="text-align: center; width: 40%;"><img src="{m['Home Logo']}" width="50" style="border-radius: 50%; border: 2px solid #00C9FF;"><div style="font-weight: bold; color: white;">{m['Home']}</div><div style="font-size: 20px; color: #00C9FF;">{m['Home Score']}</div></div><div style="color: #a0aaba; font-size: 10px;">VS</div><div style="text-align: center; width: 40%;"><img src="{m['Away Logo']}" width="50" style="border-radius: 50%; border: 2px solid #0072ff;"><div style="font-weight: bold; color: white;">{m['Away']}</div><div style="font-size: 20px; color: #00C9FF;">{m['Away Score']}</div></div></div></div>""", unsafe_allow_html=True)
            with st.expander(f"📉 View Lineups"):
                if m['Home Roster']: st.dataframe(pd.DataFrame(m['Home Roster']), use_container_width=True, hide_index=True)

elif selected_page == P_HIERARCHY:
    st.header("📈 The Hierarchy")
    if "rank_comm" not in st.session_state:
        with utils.luxury_spinner("Analyzing..."): 
            top = df_eff.iloc[0]['Team'] if not df_eff.empty else "Team A"
            bot = df_eff.iloc[-1]['Team'] if not df_eff.empty else "Team B"
            st.session_state["rank_comm"] = utils.get_rankings_commentary(OPENAI_KEY, top, bot)
    st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ Pundit\'s Take</h3>{st.session_state["rank_comm"]}</div>', unsafe_allow_html=True)
    if "df_advanced" not in st.session_state: st.session_state["df_advanced"] = utils.calculate_heavy_analytics(league, current_week)
    cols = st.columns(3)
    for i, row in st.session_state["df_advanced"].reset_index(drop=True).iterrows(): utils.render_team_card(cols[i % 3], row, i+1)

elif selected_page == P_AUDIT:
    st.header("🔎 The Audit")
    fig = go.Figure()
    if not df_eff.empty:
        fig.add_trace(go.Bar(x=df_eff["Team"], y=df_eff["Starters"], name='Starters', marker_color='#00C9FF'))
        fig.add_trace(go.Bar(x=df_eff["Team"], y=df_eff["Bench"], name='Bench Waste', marker_color='rgba(255,255,255,0.1)'))
        fig.update_layout(barmode='stack', plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aaba")
        st.plotly_chart(fig, use_container_width=True)
    if not df_bench_stars.empty: st.dataframe(df_bench_stars, use_container_width=True, hide_index=True)

elif selected_page == P_HEDGE:
    st.header("💎 The Hedge Fund")
    if "df_advanced" not in st.session_state:
        if st.button("🚀 Analyze Market Data"):
            with utils.luxury_spinner("Compiling Assets..."): st.session_state["df_advanced"] = utils.calculate_heavy_analytics(league, current_week); st.rerun()
    else:
        fig = px.scatter(st.session_state["df_advanced"], x="Power Score", y="Wins", text="Team", size="Points For", color="Luck Rating", color_continuous_scale=["#7209b7", "#4361ee", "#4cc9f0"])
        st.plotly_chart(fig, use_container_width=True)

elif selected_page == P_IPO:
    st.header("📊 The IPO Audit")
    if "draft_roi" not in st.session_state:
        if st.button("📠 Run Audit"):
             with utils.luxury_spinner("Auditing..."):
                 df_roi, prescient = utils.calculate_draft_analysis(league)
                 st.session_state["draft_roi"] = df_roi; st.session_state["prescient"] = prescient; st.rerun()
    else:
        df_roi, prescient = st.session_state["draft_roi"], st.session_state["prescient"]
        if prescient: st.markdown(f"**Best Manager:** {prescient['Team']}")
        if not df_roi.empty:
            fig = px.scatter(df_roi, x="Pick Overall", y="Points", color="Team", hover_data=["Player", "Round"], title="Draft Pick ROI")
            st.plotly_chart(fig, use_container_width=True)

elif selected_page == P_LAB:
    st.header("🧬 The Lab")
    c1, c2 = st.columns([3, 1])
    with c1: target_team = st.selectbox("Select Test Subject:", [t.team_name for t in league.teams])
    with c2:
         if st.button("🧪 Analyze"):
             with utils.luxury_spinner("Calibrating..."): st.session_state["trigger_lab"] = True; st.rerun()
    if st.session_state.get("trigger_lab"):
        roster_obj = next(t for t in league.teams if t.team_name == target_team).roster
        st.session_state["ngs_data"] = utils.analyze_nextgen_metrics_v3(roster_obj, YEAR)
        st.session_state["trigger_lab"] = False; st.rerun()
    if "ngs_data" in st.session_state and not st.session_state["ngs_data"].empty:
        cols = st.columns(2)
        for i, row in st.session_state["ngs_data"].iterrows():
            with cols[i % 2]: utils.render_lab_card(cols[i % 2], row)
    elif "ngs_data" in st.session_state: st.info("No Next Gen data available.")

elif selected_page == P_FORECAST:
    st.header("🔮 The Crystal Ball")
    if "playoff_odds" not in st.session_state:
        if st.button("🎲 Run Simulation"): st.session_state["playoff_odds"] = utils.run_monte_carlo_simulation(league); st.rerun()
    else: st.dataframe(st.session_state["playoff_odds"], use_container_width=True)

elif selected_page == P_MULTI:
    st.header("🌌 The Multiverse")
    if "base_odds" not in st.session_state: st.session_state["base_odds"] = utils.run_monte_carlo_simulation(league)
    forced = []
    with st.form("multi"):
        for i, g in enumerate(league.box_scores(week=league.current_week)):
            c = st.radio(f"{g.home_team.team_name} vs {g.away_team.team_name}", ["Sim", "Home Win", "Away Win"], key=f"g{i}", horizontal=True)
            if "Home" in c: forced.append(g.home_team.team_name)
            elif "Away" in c: forced.append(g.away_team.team_name)
        if st.form_submit_button("🚀 Run"):
            res = utils.run_multiverse_simulation(league, forced)
            st.session_state["multi_res"] = res
            st.rerun()
    if "multi_res" in st.session_state: st.dataframe(st.session_state["multi_res"], use_container_width=True)

elif selected_page == P_NEXT:
    st.header("🚀 Next Week")
    try:
        next_week = league.current_week
        box = league.box_scores(week=next_week)
        games = [{"home": g.home_team.team_name, "away": g.away_team.team_name, "spread": f"{abs(g.home_projected-g.away_projected):.1f}"} for g in box]
        if "next_week_comm" not in st.session_state:
            with utils.luxury_spinner("Checking Vegas..."): st.session_state["next_week_comm"] = utils.get_next_week_preview(OPENAI_KEY, games)
        st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ Vegas Insider</h3>{st.session_state["next_week_comm"]}</div>', unsafe_allow_html=True)
        st.subheader("Matchups")
        c1, c2 = st.columns(2)
        for i, g in enumerate(box):
             with c1 if i % 2 == 0 else c2:
                 st.markdown(f"""<div class="luxury-card" style="padding: 15px;"><div style="display:flex; justify-content:space-between; text-align:center;"><div style="flex:2; color:white;"><b>{g.home_team.team_name}</b><br><span style="color:#00C9FF;">{g.home_projected:.1f}</span></div><div style="flex:1; color:#a0aaba; font-size:0.8em;">VS</div><div style="flex:2; color:white;"><b>{g.away_team.team_name}</b><br><span style="color:#92FE9D;">{g.away_projected:.1f}</span></div></div></div>""", unsafe_allow_html=True)
    except: st.info("Projections unavailable.")

elif selected_page == P_PROP:
    st.header("📊 The Prop Desk")
    with st.expander("📘 Legend & Glossary", expanded=False):
        st.markdown("""
        - **🔥 Barn Burner:** High Vegas Total (>48 pts).
        - **🗑️ Garbage Time:** Spread > 9.5 pts.
        - **🚜 Workhorse:** Rushing Prop > 80 yds.
        - **🎯 Redzone Radar:** TD Probability > 45%.
        - **vs #32 Def:** Matchup Rank (1=Best, 32=Worst).
        - **Edge:** Vegas Implied - ESPN Projection.
        """)

    if not ODDS_API_KEY: st.warning("Missing Key")
    else:
        if "vegas" not in st.session_state or "Edge" not in st.session_state["vegas"].columns:
            with utils.luxury_spinner("Calling Vegas..."): 
                st.session_state["vegas"] = utils.get_vegas_props(ODDS_API_KEY, league, selected_week)
        
        df = st.session_state["vegas"]
        if df is not None and not df.empty:
            if "Status" in df.columns: st.warning(f"⚠️ {df.iloc[0]['Status']}")
            else:
                # --- NEW FILTER LAYOUT ---
                c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
                with c1: search_txt = st.text_input("🔍 Find Player", placeholder="Type a name...").lower()
                with c2: pos_filter = st.multiselect("Position", options=sorted(df['Position'].unique()))
                with c3: verdict_filter = st.multiselect("Verdict", options=sorted(df['Verdict'].unique()))
                with c4: team_filter = st.multiselect("Team", options=sorted(df['Team'].astype(str).unique()))
                
                # SEPARATE MONEYBALL DROPDOWN
                c_sort, c_insight, c_space = st.columns([1, 1.5, 1.5])
                with c_sort:
                    sort_order = st.selectbox("Sort Order", ["Highest Projection", "💎 Best Edge", "🚩 Worst Edge"])
                with c_insight:
                     insight_opts = [x for x in df['Insight'].unique() if x]
                     insight_filter = st.multiselect("🔥 Moneyball Filter", options=insight_opts)

                # APPLY FILTERS
                if search_txt: df = df[df['Player'].str.lower().str.contains(search_txt)]
                if pos_filter: df = df[df['Position'].isin(pos_filter)]
                if verdict_filter: df = df[df['Verdict'].isin(verdict_filter)]
                if team_filter: df = df[df['Team'].isin(team_filter)]
                if insight_filter: df = df[df['Insight'].isin(insight_filter)]
                
                if "Highest" in sort_order: df = df.sort_values(by="Proj Pts", ascending=False)
                elif "Best Edge" in sort_order: df = df.sort_values(by="Edge", ascending=False)
                elif "Worst Edge" in sort_order: df = df.sort_values(by="Edge", ascending=True)

                if df.empty: st.info("No players match your search.")
                else:
                    cols = st.columns(3)
                    for i, row in df.reset_index(drop=True).iterrows():
                        utils.render_prop_card(cols[i % 3], row)
        else: st.info("No data available.")

elif selected_page == P_DEAL:
    st.header("🤝 The Dealmaker")
    c1, c2 = st.columns(2)
    with c1: t1 = st.selectbox("Team A", [t.team_name for t in league.teams], index=0)
    with c2: t2 = st.selectbox("Team B", [t.team_name for t in league.teams], index=1)
    if st.button("🤖 Analyze"):
        ta = next(t for t in league.teams if t.team_name == t1)
        tb = next(t for t in league.teams if t.team_name == t2)
        st.markdown(utils.get_ai_trade_proposal(OPENAI_KEY, t1, t2, str(ta.roster), str(tb.roster)))

elif selected_page == P_DARK:
    st.header("🕵️ The Dark Pool")
    if st.button("🔭 Scan Wire"):
        df = utils.scan_dark_pool(league)
        st.session_state["dark_pool_data"] = df
        st.session_state["scout_rpt"] = utils.get_ai_scouting_report(OPENAI_KEY, str(df.head(5)))
        st.rerun()
    if "dark_pool_data" in st.session_state:
        st.markdown(st.session_state.get("scout_rpt", ""))
        st.dataframe(st.session_state["dark_pool_data"], use_container_width=True)

elif selected_page == P_TROPHY:
    st.header("🏆 Trophy Room")
    if "awards" not in st.session_state:
        if st.button("🏅 Unveil Awards"):
            st.session_state["awards"] = utils.calculate_season_awards(league, current_week)
            st.rerun()
    else: st.json(st.session_state["awards"])

elif selected_page == P_VAULT:
    st.header("⏳ The Dynasty Vault")
    if st.button("🔓 Unlock Vault"):
        df = utils.get_dynasty_data(LEAGUE_ID, ESPN_S2, SWID, YEAR, START_YEAR)
        st.dataframe(df)
