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

# CONSTANTS
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
    
    # Connect using the Utility file
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

# Page Constants
P_LEDGER = "📜 The Ledger"
P_HIERARCHY = "📈 The Hierarchy"
P_AUDIT = "🔎 The Audit"
P_HEDGE = "💎 The Hedge Fund"
P_IPO = "📊 The IPO Audit"
P_LAB = "🧬 The Lab"
P_FORECAST = "🔮 The Forecast"
P_MULTI = "🌌 The Multiverse"
P_NEXT = "🚀 Next Week"
P_PROP = "📊 The Prop Desk"
P_DEAL = "🤝 The Dealmaker"
P_DARK = "🕵️ The Dark Pool"
P_TROPHY = "🏆 Trophy Room"
P_VAULT = "⏳ The Vault"

page_options = [P_LEDGER, P_HIERARCHY, P_AUDIT, P_HEDGE, P_IPO, P_LAB, P_FORECAST, P_MULTI, P_NEXT, P_PROP, P_DEAL, P_DARK, P_TROPHY, P_VAULT]
selected_page = st.sidebar.radio("Navigation", page_options, label_visibility="collapsed")

# PDF Generation Button
st.sidebar.markdown("---")
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
# 4. DATA PIPELINE (DEPENDS ON SELECTED_WEEK)
# ==============================================================================
if 'box_scores' not in st.session_state or st.session_state.get('week') != selected_week:
    with utils.luxury_spinner(f"Accessing Week {selected_week} Data..."):
        st.session_state['box_scores'] = league.box_scores(week=selected_week)
        st.session_state['week'] = selected_week
    st.rerun()

box_scores = st.session_state['box_scores']

# --- DATA COLLECTION LOOP ---
matchup_data = []
efficiency_data = []
all_active_players = [] 
bench_highlights = []

for game in box_scores:
    home, away = game.home_team, game.away_team
    
    def get_roster_data(lineup, team_name):
        starters, bench = [], []
        for p in lineup:
            # Collect basic info
            info = {"Name": p.name, "Score": p.points, "Pos": p.slot_position}
            
            # Check status for "Active" list (Weekly Elite)
            status = getattr(p, 'injuryStatus', 'ACTIVE')
            status_str = str(status).upper().replace("_", " ") if status else "ACTIVE"
            is_injured = any(k in status_str for k in ['OUT', 'IR', 'RESERVE', 'SUSPENDED'])
            
            if p.slot_position == 'BE':
                bench.append(info)
                if p.points > 15: 
                    bench_highlights.append({"Team": team_name, "Player": p.name, "Score": p.points})
            else:
                starters.append(info)
                # Add to Elite List candidates if not injured
                if not is_injured: 
                    all_active_players.append({
                        "Name": p.name, 
                        "Points": p.points, 
                        "Team": team_name, 
                        "ID": p.playerId
                    })
        return starters, bench

    h_r, h_br = get_roster_data(game.home_lineup, home.team_name)
    a_r, a_br = get_roster_data(game.away_lineup, away.team_name)
    
    # Matchup Data (Ledger)
    matchup_data.append({
        "Home": home.team_name, "Home Score": game.home_score, "Home Logo": utils.get_logo(home), "Home Roster": h_r,
        "Away": away.team_name, "Away Score": game.away_score, "Away Logo": utils.get_logo(away), "Away Roster": a_r
    })
    
    # Efficiency Data (Hierarchy)
    h_p = sum(p['Score'] for p in h_r) + sum(p['Score'] for p in h_br)
    a_p = sum(p['Score'] for p in a_r) + sum(p['Score'] for p in a_br)
    efficiency_data.append({"Team": home.team_name, "Total Potential": h_p, "Starters": sum(p['Score'] for p in h_r), "Bench": sum(p['Score'] for p in h_br)})
    efficiency_data.append({"Team": away.team_name, "Total Potential": a_p, "Starters": sum(p['Score'] for p in a_r), "Bench": sum(p['Score'] for p in a_br)})

# --- SAFE DATAFRAME CREATION ---
if efficiency_data:
    df_eff = pd.DataFrame(efficiency_data).sort_values(by="Total Potential", ascending=False)
else:
    df_eff = pd.DataFrame(columns=["Team", "Total Potential", "Starters", "Bench"])

if all_active_players:
    df_players = pd.DataFrame(all_active_players).sort_values(by="Points", ascending=False).head(5)
else:
    df_players = pd.DataFrame(columns=["Name", "Points", "Team", "ID"])

if bench_highlights:
    df_bench_stars = pd.DataFrame(bench_highlights).sort_values(by="Score", ascending=False).head(5)
else:
    df_bench_stars = pd.DataFrame(columns=["Team", "Player", "Score"])

# ==============================================================================
# 5. DASHBOARD UI ROUTER
# ==============================================================================
st.title(f"🏛️ Luxury League Protocol: Week {selected_week}")

# --- HERO ROW ---
st.markdown("### 🌟 Weekly Elite")
h1, h2, h3 = st.columns(3)
if not df_players.empty:
    top_3 = df_players.head(3).reset_index(drop=True)
    if len(top_3) >= 1: utils.render_hero_card(h1, top_3.iloc[0])
    if len(top_3) >= 2: utils.render_hero_card(h2, top_3.iloc[1])
    if len(top_3) >= 3: utils.render_hero_card(h3, top_3.iloc[2])
else:
    st.info("No player data available for this week yet.")
st.markdown("---")

# --- PAGE ROUTING ---

if selected_page == P_LEDGER:
    st.header("📜 The Ledger")
    st.caption("Where the receipts are kept and the scores are settled.")
    if "recap" not in st.session_state:
        with utils.luxury_spinner("Analyst is reviewing portfolios..."): 
            # Ensure we have data before asking AI
            top_team = df_eff.iloc[0]['Team'] if not df_eff.empty else "League"
            st.session_state["recap"] = utils.get_weekly_recap(OPENAI_KEY, selected_week, top_team)
    st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ The Studio Report</h3>{st.session_state["recap"]}</div>', unsafe_allow_html=True)
    
    st.markdown("#### Weekly Transactions")
    c1, c2 = st.columns(2)
    for i, m in enumerate(matchup_data):
        with c1 if i % 2 == 0 else c2:
            st.markdown(f"""<div class="luxury-card" style="padding: 15px;"><div style="display: flex; justify-content: space-between; align-items: center;"><div style="text-align: center; width: 40%;"><img src="{m['Home Logo']}" width="50" style="border-radius: 50%; border: 2px solid #00C9FF;"><div style="font-weight: bold; color: white;">{m['Home']}</div><div style="font-size: 20px; color: #00C9FF;">{m['Home Score']}</div></div><div style="color: #a0aaba; font-size: 10px;">VS</div><div style="text-align: center; width: 40%;"><img src="{m['Away Logo']}" width="50" style="border-radius: 50%; border: 2px solid #0072ff;"><div style="font-weight: bold; color: white;">{m['Away']}</div><div style="font-size: 20px; color: #00C9FF;">{m['Away Score']}</div></div></div></div>""", unsafe_allow_html=True)
            with st.expander(f"📉 View Lineups"):
                if m['Home Roster']:
                    df_m = pd.DataFrame(m['Home Roster'])
                    st.dataframe(df_m, use_container_width=True, hide_index=True)

elif selected_page == P_HIERARCHY:
    st.header("📈 The Hierarchy")
    st.caption("A ruthless ranking of who is actually good and who is just lucky.")
    if "rank_comm" not in st.session_state:
        with utils.luxury_spinner("Analyzing..."): 
            top = df_eff.iloc[0]['Team'] if not df_eff.empty else "Team A"
            bot = df_eff.iloc[-1]['Team'] if not df_eff.empty else "Team B"
            st.session_state["rank_comm"] = utils.get_rankings_commentary(OPENAI_KEY, top, bot)
    st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ Pundit\'s Take</h3>{st.session_state["rank_comm"]}</div>', unsafe_allow_html=True)
    
    st.subheader("Power Rankings")
    if "df_advanced" not in st.session_state:
        st.session_state["df_advanced"] = utils.calculate_heavy_analytics(league, current_week)
    
    df = st.session_state["df_advanced"]
    cols = st.columns(3)
    for i, row in df.reset_index(drop=True).iterrows():
        utils.render_team_card(cols[i % 3], row, i+1)

elif selected_page == P_AUDIT:
    st.header("🔎 The Audit")
    st.caption("Forensic analysis of your lineup decisions. We see those bench points.")
    fig = go.Figure()
    if not df_eff.empty:
        fig.add_trace(go.Bar(x=df_eff["Team"], y=df_eff["Starters"], name='Starters', marker_color='#00C9FF'))
        fig.add_trace(go.Bar(x=df_eff["Team"], y=df_eff["Bench"], name='Bench Waste', marker_color='rgba(255,255,255,0.1)'))
        fig.update_layout(barmode='stack', plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aaba")
        st.plotly_chart(fig, use_container_width=True)
    if not df_bench_stars.empty: st.dataframe(df_bench_stars, use_container_width=True, hide_index=True)

elif selected_page == P_HEDGE:
    st.header("💎 The Hedge Fund")
    st.caption("Advanced metrics for the sophisticated investor.")
    if "df_advanced" not in st.session_state:
        if st.button("🚀 Analyze Market Data"):
            with utils.luxury_spinner("Compiling Assets..."): st.session_state["df_advanced"] = utils.calculate_heavy_analytics(league, current_week); st.rerun()
    else:
        fig = px.scatter(st.session_state["df_advanced"], x="Power Score", y="Wins", text="Team", size="Points For", color="Luck Rating", color_continuous_scale=["#7209b7", "#4361ee", "#4cc9f0"], title="Luck Matrix", height=600)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aaba")
        st.plotly_chart(fig, use_container_width=True)

elif selected_page == P_IPO:
    st.header("📊 The IPO Audit")
    st.caption("Draft capital ROI. Who was a blue chip and who was a penny stock?")
    if "draft_roi" not in st.session_state:
        if st.button("📠 Run Audit"):
             with utils.luxury_spinner("Auditing draft capital..."):
                 df_roi, prescient = utils.calculate_draft_analysis(league)
                 st.session_state["draft_roi"] = df_roi
                 st.session_state["prescient"] = prescient
                 st.rerun()
    else:
        df_roi, prescient = st.session_state["draft_roi"], st.session_state["prescient"]
        st.markdown(f"""<div class="luxury-card" style="border-left: 4px solid #92FE9D; background: linear-gradient(90deg, rgba(146, 254, 157, 0.1), rgba(17, 25, 40, 0.8)); display: flex; align-items: center;"><div style="flex: 1; text-align: center;"><img src="{prescient['Logo']}" style="width: 90px; border-radius: 50%; border: 3px solid #92FE9D;"></div><div style="flex: 3; padding-left: 20px;"><h3 style="color: #92FE9D; margin: 0;">The Prescient One</h3><div style="font-size: 1.8rem; font-weight: 900; color: white;">{prescient['Team']}</div><div style="color: #a0aaba; font-size: 1.1rem;">Generated <b>{prescient['Points']:.0f} points</b> from waivers while securing <b>{prescient['Wins']} Wins</b>.</div></div></div>""", unsafe_allow_html=True)
        if not df_roi.empty:
            fig = px.scatter(df_roi, x="Pick Overall", y="Points", color="Team", hover_data=["Player", "Round"], title="Draft Pick ROI", height=600)
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aaba", xaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("💎 Penny Stocks")
                st.dataframe(df_roi[df_roi["Round"] >= 8].sort_values(by="Points", ascending=False).head(10)[["Player", "Team", "Round", "Points"]], use_container_width=True, hide_index=True)
            with c2:
                st.subheader("💸 Bad Debt")
                st.dataframe(df_roi[df_roi["Round"] <= 3].sort_values(by="Points", ascending=True).head(10)[["Player", "Team", "Round", "Points"]], use_container_width=True, hide_index=True)
        else: st.info("Draft data unavailable.")

elif selected_page == P_LAB:
    st.header("🧬 The Lab")
    st.caption("Next Gen Stats for the analytically inclined.")
    c1, c2 = st.columns([3, 1])
    with c1: target_team = st.selectbox("Select Test Subject:", [t.team_name for t in league.teams])
    with c2:
         if st.button("🧪 Analyze"):
             with utils.luxury_spinner("Calibrating..."): st.session_state["trigger_lab"] = True; st.rerun()
    
    if st.session_state.get("trigger_lab"):
        roster_obj = next(t for t in league.teams if t.team_name == target_team).roster
        st.session_state["ngs_data"] = utils.analyze_nextgen_metrics_v3(roster_obj, YEAR)
        st.session_state["trigger_lab"] = False; st.rerun()
    
    if "ngs_data" in st.session_state:
        if not st.session_state["ngs_data"].empty:
            cols = st.columns(2)
            for i, row in st.session_state["ngs_data"].iterrows():
                with cols[i % 2]:
                    utils.render_lab_card(cols[i % 2], row)
        else: st.info("No Next Gen data available.")

elif selected_page == P_FORECAST:
    st.header("🔮 The Crystal Ball")
    st.caption("Monte Carlo simulations. 1,000 realities, one winner.")
    if "playoff_odds" not in st.session_state:
        if st.button("🎲 Run Simulation"):
            with utils.luxury_spinner("Simulating..."): st.session_state["playoff_odds"] = utils.run_monte_carlo_simulation(league); st.rerun()
    else:
        st.dataframe(st.session_state["playoff_odds"], use_container_width=True, hide_index=True, column_config={"Playoff Odds": st.column_config.ProgressColumn("Prob", format="%.1f%%", min_value=0, max_value=1.0)})

elif selected_page == P_MULTI:
    st.header("🌌 The Multiverse")
    st.caption("Control the timeline. Force wins and see your odds change.")
    if "base_odds" not in st.session_state:
        with utils.luxury_spinner("Calculating Baseline..."): st.session_state["base_odds"] = utils.run_monte_carlo_simulation(league)
    
    box = league.box_scores(week=league.current_week)
    forced = []
    
    with st.form("multi_form"):
        st.markdown("### 🔮 Pick This Week's Winners")
        for i, g in enumerate(box):
            home_n = g.home_team.team_name
            away_n = g.away_team.team_name
            choice = st.radio(f"{home_n} vs {away_n}", ["Simulate", f"{home_n} Wins", f"{away_n} Wins"], key=f"g{i}", horizontal=True)
            
            if "Simulate" not in choice:
                forced.append(home_n if home_n in choice else away_n)
                
        run_sim = st.form_submit_button("🚀 Run Simulation")
        
    if run_sim:
        with utils.luxury_spinner("Simulating..."):
            res = utils.run_multiverse_simulation(league, forced)
            base = st.session_state["base_odds"][["Team", "Playoff Odds"]].rename(columns={"Playoff Odds": "Base"})
            final = pd.merge(res, base, on="Team")
            final["Impact"] = final["New Odds"] - final["Base"]
            st.session_state["multi_res"] = final.sort_values(by="New Odds", ascending=False)
            
    if "multi_res" in st.session_state:
        st.dataframe(
            st.session_state["multi_res"], 
            use_container_width=True, 
            hide_index=True, 
            column_config={
                "New Odds": st.column_config.ProgressColumn("New Odds", min_value=0, max_value=1.0, format="%.1f%%"),
                "Base": st.column_config.NumberColumn(format="%.1f%%"),
                "Impact": st.column_config.NumberColumn(format="%+.1f%%")
            }
        )

elif selected_page == P_NEXT:
    try:
        st.header("🚀 Next Week")
        st.caption("A look ahead. Set your lines.")
        next_week = league.current_week
        box = league.box_scores(week=next_week)
        games = [{"home": g.home_team.team_name, "away": g.away_team.team_name, "spread": f"{abs(g.home_projected-g.away_projected):.1f}"} for g in box]
        if "next_week_comm" not in st.session_state:
            with utils.luxury_spinner("Checking Vegas..."): st.session_state["next_week_comm"] = utils.get_next_week_preview(OPENAI_KEY, games)
        st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ Vegas Insider</h3>{st.session_state.get("next_week_comm", "Analysis Pending...")}</div>', unsafe_allow_html=True)
        st.subheader("Matchups")
        c1, c2 = st.columns(2)
        for i, g in enumerate(box):
             with c1 if i % 2 == 0 else c2:
                 st.markdown(f"""<div class="luxury-card" style="padding: 15px;"><div style="display:flex; justify-content:space-between; text-align:center;"><div style="flex:2; color:white;"><b>{g.home_team.team_name}</b><br><span style="color:#00C9FF;">{g.home_projected:.1f}</span></div><div style="flex:1; color:#a0aaba; font-size:0.8em;">VS</div><div style="flex:2; color:white;"><b>{g.away_team.team_name}</b><br><span style="color:#92FE9D;">{g.away_projected:.1f}</span></div></div></div>""", unsafe_allow_html=True)
    except: st.info("Projections unavailable.")

elif selected_page == P_PROP:
    st.header("📊 The Prop Desk")
    st.caption("Vegas knows. Find the edge against your projections.")
    
    # --- LEGEND EXPANDER ---
    with st.expander("📘 Legend & Glossary", expanded=False):
        st.markdown("""
        **Key Insights Explained:**
        - **🔥 Barn Burner:** High Vegas Total (>48 pts). Start your fringe players in this shootout.
        - **🗑️ Garbage Time:** Spread > 9.5 pts. Trailing QBs/WRs may feast on soft defenses late.
        - **🚜 Workhorse:** Rushing Prop > 80 yds. High floor volume play.
        - **🎯 Redzone Radar:** TD Probability > 45%. Good bet for a score.
        - **vs #32 Def:** Matchup Rank. #1 is Best (Allows Most Points), #32 is Worst (Lockdown Defense).
        - **Edge:** The difference between Vegas implied points and ESPN projection. Blue is positive edge.
        - **Weather:** ☀️ Clear, 🌧️ Rain (Sloppy), 💨 Wind (Passing Downgrade), ❄️ Snow.
        """)

    if not ODDS_API_KEY: st.warning("Missing Key")
    else:
        # SELF-HEALING CACHE CHECK: If old data (missing "Edge") is found, re-fetch.
        if "vegas" not in st.session_state or "Edge" not in st.session_state["vegas"].columns:
            with utils.luxury_spinner("Calling Vegas..."): 
                # PASS SELECTED WEEK to get accurate weekly projections
                st.session_state["vegas"] = utils.get_vegas_props(ODDS_API_KEY, league, selected_week)
        
        df = st.session_state["vegas"]
        
        if df is not None and not df.empty:
            if "Status" in df.columns: 
                st.warning(f"⚠️ {df.iloc[0]['Status']}")
            else:
                # --- FILTER ROW ---
                c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
                with c1:
                    search_txt = st.text_input("🔍 Find Player", placeholder="Type a name...").lower()
                with c2:
                    pos_filter = st.multiselect("Position", options=sorted(df['Position'].unique()))
                with c3:
                    verdict_filter = st.multiselect("Verdict", options=sorted(df['Verdict'].unique()))
                with c4:
                    team_filter = st.multiselect("Team", options=sorted(df['Team'].astype(str).unique()))
                
                # --- SORT & INSIGHT ROW ---
                c_sort, c_insight, c_space = st.columns([1, 1.5, 1.5])
                with c_sort:
                    sort_order = st.selectbox(
                        "Sort Order", 
                        ["Highest Projection", "💎 Best Edge (Vegas > ESPN)", "🚩 Worst Edge (Vegas < ESPN)"]
                    )
                with c_insight:
                     # Filter out empty insights for the dropdown
                     insight_opts = [x for x in df['Insight'].unique() if x]
                     insight_filter = st.multiselect("🔥 Moneyball Filter", options=insight_opts)

                # Apply Filters
                if search_txt: df = df[df['Player'].str.lower().str.contains(search_txt)]
                if pos_filter: df = df[df['Position'].isin(pos_filter)]
                if verdict_filter: df = df[df['Verdict'].isin(verdict_filter)]
                if team_filter: df = df[df['Team'].isin(team_filter)]
                if insight_filter: df = df[df['Insight'].isin(insight_filter)]
                
                # Apply Sort
                if "Highest Projection" in sort_order:
                    df = df.sort_values(by="Proj Pts", ascending=False)
                elif "Best Edge" in sort_order:
                    df = df.sort_values(by="Edge", ascending=False) # Positive Edge First
                elif "Worst Edge" in sort_order:
                    df = df.sort_values(by="Edge", ascending=True)  # Negative Edge First

                # Render Cards
                if df.empty:
                    st.info("No players match your search.")
                else:
                    cols = st.columns(3)
                    for i, row in df.reset_index(drop=True).iterrows():
                        utils.render_prop_card(cols[i % 3], row)
        else: st.info("No data available.")

elif selected_page == P_DEAL:
    st.header("🤝 The Dealmaker")
    st.caption("Trade analyzer. Fleece your league mates with data.")
    c1, c2 = st.columns(2)
    with c1: t1 = st.selectbox("Team A", [t.team_name for t in league.teams], index=0)
    with c2: t2 = st.selectbox("Team B", [t.team_name for t in league.teams], index=1)
    if st.button("🤖 Analyze"):
        with utils.luxury_spinner("Processing..."):
            ta = next(t for t in league.teams if t.team_name == t1)
            tb = next(t for t in league.teams if t.team_name == t2)
            ra = [f"{p.name} ({p.position})" for p in ta.roster]
            rb = [f"{p.name} ({p.position})" for p in tb.roster]
            st.markdown(f'<div class="luxury-card studio-box"><h3>Proposal</h3>{utils.get_ai_trade_proposal(OPENAI_KEY, t1, t2, ra, rb)}</div>', unsafe_allow_html=True)

elif selected_page == P_DARK:
    st.header("🕵️ The Dark Pool")
    st.caption("The Waiver Wire. Hidden gems and desperate adds.")
    has_data = "dark_pool_data" in st.session_state
    if not has_data:
        if st.button("🔭 Scan Wire"):
             with utils.luxury_spinner("Scouting..."):
                 df = utils.scan_dark_pool(league)
                 st.session_state["dark_pool_data"] = df
                 if not df.empty:
                     p_str = ", ".join([f"{r['Name']} ({r['Position']})" for i, r in df.iterrows()])
                     st.session_state["scout_rpt"] = utils.get_ai_scouting_report(OPENAI_KEY, p_str)
                 st.rerun()
    else:
        if st.button("🔄 Rescan"): del st.session_state["dark_pool_data"]; st.rerun()
        if "scout_rpt" in st.session_state: st.markdown(f'<div class="luxury-card studio-box"><h3>📝 Scout\'s Notebook</h3>{st.session_state["scout_rpt"]}</div>', unsafe_allow_html=True)
        st.dataframe(st.session_state["dark_pool_data"], use_container_width=True)

elif selected_page == P_TROPHY:
    st.header("🏆 Trophy Room")
    st.caption("Glory and shame. The hall of records.")
    if "awards" not in st.session_state:
        if st.button("🏅 Unveil Awards"):
            with utils.luxury_spinner("Engraving..."):
                st.session_state["awards"] = utils.calculate_season_awards(league, current_week)
                aw = st.session_state["awards"]
                st.session_state["season_comm"] = utils.get_season_retrospective(OPENAI_KEY, aw['MVP']['Name'], aw['Best Manager']['Team'])
                st.rerun()
    else:
        aw = st.session_state["awards"]
        if "season_comm" in st.session_state: st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ State of the League</h3>{st.session_state["season_comm"]}</div>', unsafe_allow_html=True)
        st.divider(); st.markdown("<h2 style='text-align: center;'>🏆 THE PODIUM</h2>", unsafe_allow_html=True)
        
        pod = aw.get("Podium", [])
        c_silv, c_gold, c_brnz = st.columns([1, 1.2, 1])
        if len(pod) > 1:
            with c_silv: st.markdown(f"""<div class="podium-step silver"><img src="{utils.get_logo(pod[1])}" style="width:80px; border-radius:50%; border:3px solid #C0C0C0; display:block; margin:0 auto;"><div style="color:white; font-weight:bold; margin-top:10px;">{pod[1].team_name}</div><div style="color:#C0C0C0;">{pod[1].wins}-{pod[1].losses}</div><div class="rank-num">2</div></div>""", unsafe_allow_html=True)
        if len(pod) > 0:
            with c_gold: st.markdown(f"""<div class="podium-step gold"><img src="{utils.get_logo(pod[0])}" style="width:100px; border-radius:50%; border:4px solid #FFD700; display:block; margin:0 auto; box-shadow:0 0 20px rgba(255,215,0,0.6);"><div style="color:white; font-weight:900; font-size:1.4rem; margin-top:15px;">{pod[0].team_name}</div><div style="color:#FFD700;">{pod[0].wins}-{pod[0].losses}</div><div class="rank-num">1</div></div>""", unsafe_allow_html=True)
        if len(pod) > 2:
            with c_brnz: st.markdown(f"""<div class="podium-step bronze"><img src="{utils.get_logo(pod[2])}" style="width:70px; border-radius:50%; border:3px solid #CD7F32; display:block; margin:0 auto;"><div style="color:white; font-weight:bold; margin-top:10px;">{pod[2].team_name}</div><div style="color:#CD7F32;">{pod[2].wins}-{pod[2].losses}</div><div class="rank-num">3</div></div>""", unsafe_allow_html=True)
        
        st.markdown("---")
        def gen_nar(type, team, val):
            if type == "Oracle": return f"Ultimate strategist. {team} hit **{val:.1f}% efficiency**."
            if type == "Sniper": return f"Wire wizard. {team} got **{val:.1f} pts** from free agents."
            if type == "Purple": return f"Survivor. {team} managed **{val} injuries**."
            if type == "Hoarder": return f"Wealth hoarder. {team} left **{val:.1f} pts** on bench."
            if type == "Toilet": return f"Offense stalled. Only **{val:.1f} pts** scored."
            if type == "Blowout": return f"Historic beatdown. Lost by **{val:.1f} pts**."
            return ""

        c1, c2, c3, c4 = st.columns(4)
        ora = aw['Oracle']
        with c1: st.markdown(f"""<div class="luxury-card award-card"><img src="{ora['Logo']}" style="width:60px; border-radius:50%;"><h4 style="color:#00C9FF; margin:0;">The Oracle</h4><div style="font-weight:bold; color:white;">{ora['Team']}</div><div style="color:#a0aaba; font-size:0.8rem;">{ora['Eff']:.1f}% Eff</div><div class="award-blurb">{gen_nar("Oracle", ora['Team'], ora['Eff'])}</div></div>""", unsafe_allow_html=True)
        sni = aw['Sniper']
        with c2: st.markdown(f"""<div class="luxury-card award-card"><img src="{sni['Logo']}" style="width:60px; border-radius:50%;"><h4 style="color:#00C9FF; margin:0;">The Sniper</h4><div style="font-weight:bold; color:white;">{sni['Team']}</div><div style="color:#a0aaba; font-size:0.8rem;">{sni['Pts']:.1f} Pts</div><div class="award-blurb">{gen_nar("Sniper", sni['Team'], sni['Pts'])}</div></div>""", unsafe_allow_html=True)
        pur = aw['Purple']
        with c3: st.markdown(f"""<div class="luxury-card award-card"><img src="{pur['Logo']}" style="width:60px; border-radius:50%;"><h4 style="color:#00C9FF; margin:0;">Purple Heart</h4><div style="font-weight:bold; color:white;">{pur['Team']}</div><div style="color:#a0aaba; font-size:0.8rem;">{pur['Count']} Inj</div><div class="award-blurb">{gen_nar("Purple", pur['Team'], pur['Count'])}</div></div>""", unsafe_allow_html=True)
        hoa = aw['Hoarder']
        with c4: st.markdown(f"""<div class="luxury-card award-card"><img src="{hoa['Logo']}" style="width:60px; border-radius:50%;"><h4 style="color:#00C9FF; margin:0;">The Hoarder</h4><div style="font-weight:bold; color:white;">{hoa['Team']}</div><div style="color:#a0aaba; font-size:0.8rem;">{hoa['Pts']:.1f} Pts</div><div class="award-blurb">{gen_nar("Hoarder", hoa['Team'], hoa['Pts'])}</div></div>""", unsafe_allow_html=True)
        st.markdown("---")
        t1, t2 = st.columns(2)
        toilet = aw['Toilet']
        with t1: st.markdown(f"""<div class="luxury-card shame-card"><img src="{toilet['Logo']}" width="80" style="border-radius:50%; border:3px solid #FF4B4B;"><div><div style="color:#FF4B4B; font-weight:bold;">LOWEST SCORING</div><div style="font-size:1.8rem; font-weight:900; color:white;">{toilet['Team']}</div><div style="color:#aaa;">{toilet['Pts']:.1f} Pts</div><div class="award-blurb" style="color:#FF8888;">{gen_nar("Toilet", toilet['Team'], toilet['Pts'])}</div></div></div>""", unsafe_allow_html=True)
        blowout = aw['Blowout']
        with t2: st.markdown(f"""<div class="luxury-card shame-card"><div style="color:#FF4B4B; font-weight:bold;">💥 BIGGEST BLOWOUT</div><div style="font-size:1.5rem; font-weight:900; color:white; margin:10px 0;">{blowout['Loser']}</div><div style="color:#aaa;">Def. by {blowout['Winner']} (+{blowout['Margin']:.1f})</div><div class="award-blurb" style="color:#FF8888;">{gen_nar("Blowout", blowout['Loser'], blowout['Margin'])}</div></div>""", unsafe_allow_html=True)

elif selected_page == P_VAULT:
    st.header("⏳ The Dynasty Vault")
    if "dynasty_lead" not in st.session_state:
        if st.button("🔓 Unlock Vault"):
            with utils.luxury_spinner("Time Traveling..."):
                df_raw = utils.get_dynasty_data(LEAGUE_ID, ESPN_S2, SWID, YEAR, START_YEAR)
                st.session_state["dynasty_lead"] = utils.process_dynasty_leaderboard(df_raw)
                st.session_state["dynasty_raw"] = df_raw
                st.rerun()
    else:
        st.dataframe(st.session_state["dynasty_lead"], use_container_width=True)
        fig = px.line(st.session_state["dynasty_raw"], x="Year", y="Wins", color="Manager", markers=True)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aaba")
        st.plotly_chart(fig, use_container_width=True)
