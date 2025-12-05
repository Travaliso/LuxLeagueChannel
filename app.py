import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import luxury_utils as utils

st.set_page_config(page_title="Luxury League Dashboard", page_icon="💎", layout="wide")
utils.inject_luxury_css()

# --- SYSTEM STATUS ---
st.sidebar.title("🥂 The Concierge")
with st.sidebar.expander("System Status", expanded=False):
    oid = st.secrets.get("openai_key")
    ood = st.secrets.get("odds_api_key")
    st.write(f"🤖 AI Agent: {'✅ Online' if oid else '❌ Missing Key'}")
    st.write(f"🎲 Prop Desk: {'✅ Online' if ood else '❌ Missing Key'}")

try:
    LEAGUE_ID = st.secrets["league_id"]
    SWID = st.secrets["swid"]
    ESPN_S2 = st.secrets["espn_s2"]
    OPENAI_KEY = oid
    ODDS_API_KEY = ood
    YEAR = 2025
    league = utils.get_league(LEAGUE_ID, YEAR, ESPN_S2, SWID)
except Exception as e:
    st.error(f"🔒 Connection Error: {e}")
    st.stop()

current_week = league.current_week - 1
if current_week == 0: current_week = 1
selected_week = st.sidebar.slider("Select Week", 1, current_week, current_week)
st.sidebar.markdown("---")

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

if 'box_scores' not in st.session_state or st.session_state.get('week') != selected_week:
    with utils.luxury_spinner(f"Accessing Week {selected_week} Data..."):
        st.session_state['box_scores'] = league.box_scores(week=selected_week)
        st.session_state['week'] = selected_week
    st.rerun()

box_scores = st.session_state['box_scores']
matchup_data, efficiency_data, bench_highlights = [], [], []

for game in box_scores:
    def get_roster_data(lineup, team_name):
        starters, bench = [], []
        for p in lineup:
            info = {"Name": p.name, "Score": p.points, "Pos": p.slot_position}
            if p.slot_position == 'BE':
                bench.append(info)
                if p.points > 15: bench_highlights.append({"Team": team_name, "Player": p.name, "Score": p.points})
            else: starters.append(info)
        return starters, bench

    h_r, h_br = get_roster_data(game.home_lineup, game.home_team.team_name)
    a_r, a_br = get_roster_data(game.away_lineup, game.away_team.team_name)
    
    matchup_data.append({"Home": game.home_team.team_name, "Home Score": game.home_score, "Home Logo": utils.get_logo(game.home_team), "Home Roster": h_r, "Away": game.away_team.team_name, "Away Score": game.away_score, "Away Logo": utils.get_logo(game.away_team), "Away Roster": a_r})
    
    h_p = sum(p['Score'] for p in h_r) + sum(p['Score'] for p in h_br)
    a_p = sum(p['Score'] for p in a_r) + sum(p['Score'] for p in a_br)
    efficiency_data.append({"Team": game.home_team.team_name, "Total Potential": h_p, "Starters": sum(p['Score'] for p in h_r), "Bench": sum(p['Score'] for p in h_br)})
    efficiency_data.append({"Team": game.away_team.team_name, "Total Potential": a_p, "Starters": sum(p['Score'] for p in a_r), "Bench": sum(p['Score'] for p in a_br)})

df_eff = pd.DataFrame(efficiency_data).sort_values(by="Total Potential", ascending=False)
df_bench_stars = pd.DataFrame(bench_highlights).sort_values(by="Score", ascending=False).head(5)

st.title(f"🏛️ Luxury League Protocol: Week {selected_week}")

if selected_page == P_LEDGER:
    st.header("📜 The Ledger")
    st.caption("Where the receipts are kept and the scores are settled.")
    if "recap" not in st.session_state:
        with utils.luxury_spinner("Analyst is reviewing portfolios..."): 
            st.session_state["recap"] = utils.get_weekly_recap(OPENAI_KEY, selected_week, df_eff.iloc[0]['Team'])
    st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ The Studio Report</h3>{st.session_state["recap"]}</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    for i, m in enumerate(matchup_data):
        with c1 if i % 2 == 0 else c2:
            st.markdown(f"""<div class="luxury-card" style="padding: 15px;"><div style="display: flex; justify-content: space-between; align-items: center;"><div style="text-align: center; width: 40%;"><img src="{m['Home Logo']}" width="50" style="border-radius: 50%; border: 2px solid #00C9FF;"><div style="font-weight: bold; color: white;">{m['Home']}</div><div style="font-size: 20px; color: #00C9FF;">{m['Home Score']}</div></div><div style="color: #a0aaba; font-size: 10px;">VS</div><div style="text-align: center; width: 40%;"><img src="{m['Away Logo']}" width="50" style="border-radius: 50%; border: 2px solid #0072ff;"><div style="font-weight: bold; color: white;">{m['Away']}</div><div style="font-size: 20px; color: #00C9FF;">{m['Away Score']}</div></div></div></div>""", unsafe_allow_html=True)
            with st.expander(f"📉 View Lineups"):
                max_len = max(len(m['Home Roster']), len(m['Away Roster']))
                df_m = pd.DataFrame({
                    f"{m['Home']}": [p['Name'] for p in m['Home Roster']] + [''] * (max_len - len(m['Home Roster'])),
                    f"{m['Home']} Pts": [p['Score'] for p in m['Home Roster']] + [0] * (max_len - len(m['Home Roster'])),
                    f"{m['Away']} Pts": [p['Score'] for p in m['Away Roster']] + [0] * (max_len - len(m['Away Roster'])),
                    f"{m['Away']}": [p['Name'] for p in m['Away Roster']] + [''] * (max_len - len(m['Away Roster']))
                })
                st.dataframe(df_m, use_container_width=True, hide_index=True)

elif selected_page == P_HIERARCHY:
    st.header("📈 The Hierarchy")
    st.caption("A ruthless ranking of who is actually good and who is just lucky.")
    if "rank_comm" not in st.session_state:
        with utils.luxury_spinner("Analyzing..."): st.session_state["rank_comm"] = utils.get_rankings_commentary(OPENAI_KEY, df_eff.iloc[0]['Team'], df_eff.iloc[-1]['Team'])
    st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ Pundit\'s Take</h3>{st.session_state["rank_comm"]}</div>', unsafe_allow_html=True)
    if "df_advanced" not in st.session_state:
        st.session_state["df_advanced"] = utils.calculate_heavy_analytics(league, current_week)
    df = st.session_state["df_advanced"]
    cols = st.columns(3)
    for i, row in df.reset_index(drop=True).iterrows():
        utils.render_team_card(cols[i % 3], row, i+1)

elif selected_page == P_AUDIT:
    st.header("🔎 The Audit")
    st.caption("Forensic analysis of your lineup decisions.")
    fig = go.Figure()
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
    st.caption("Draft capital ROI.")
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
                    st.markdown(f"""<div class="luxury-card" style="border-left: 4px solid #00C9FF; display: flex; align-items: center;"><div style="flex:1;"><h4 style="color:white; margin:0;">{row['Player']}</h4><div style="color:#00C9FF;">{row['Verdict']}</div></div><div style="text-align:right;"><div style="font-size:1.4em; font-weight:bold; color:white;">{row['Value']}</div><div style="color:#92FE9D; font-size:0.8em;">{row['Alpha Stat']}</div></div></div>""", unsafe_allow_html=True)
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
    with st.form("multi"):
        st.markdown("### 🔮 Pick This Week's Winners")
        c1, c2 = st.columns(2)
        for i, g in enumerate(box):
            with c1 if i % 2 == 0 else c2:
                home_win = f"{g.home_team.team_name} Win"
                away_win = f"{g.away_team.team_name} Win"
                c = st.radio(f"{g.home_team.team_name} vs {g.away_team.team_name}", ["Sim", home_win, away_win], key=f"g{i}", horizontal=True)
                if c == home_win: forced.append(g.home_team.team_name)
                elif c == away_win: forced.append(g.away_team.team_name)
        if st.form_submit_button("🚀 Run Simulation"):
            with utils.luxury_spinner("Simulating..."):
                res = utils.run_multiverse_simulation(league, forced)
                base = st.session_state["base_odds"][["Team", "Playoff Odds"]].rename(columns={"Playoff Odds": "Base"})
                final = pd.merge(res, base, on="Team")
                final["Impact"] = final["New Odds"] - final["Base"]
                st.session_state["multi_res"] = final.sort_values(by="New Odds", ascending=False)
    if "multi_res" in st.session_state:
        st.dataframe(st.session_state["multi_res"], use_container_width=True, hide_index=True, column_config={"New Odds": st.column_config.ProgressColumn("Odds", min_value=0, max_value=1.0), "Impact": st.column_config.NumberColumn(format="%+.1f%%")})

elif selected_page == P_NEXT:
    try:
        st.header("🚀 Next Week")
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
    st.caption("Vegas knows. Find the edge against your projections.")
    if not ODDS_API_KEY: st.warning("Missing Key")
    else:
        if "vegas" not in st.session_state or "Edge" not in st.session_state["vegas"].columns:
            with utils.luxury_spinner("Calling Vegas..."): 
                st.session_state["vegas"] = utils.get_vegas_props(ODDS_API_KEY, league, selected_week)
        df = st.session_state["vegas"]
        if df is not None and not df.empty:
            if "Status" in df.columns: st.warning(f"⚠️ {df.iloc[0]['Status']}")
            else:
                c1, c2, c3, c4 = st.columns([1.5, 1, 1, 1])
                with c1: search_txt = st.text_input("🔍 Find Player", placeholder="Type a name...").lower()
                with c2: pos_filter = st.multiselect("Position", options=sorted(df['Position'].unique()))
                with c3: verdict_filter = st.multiselect("Verdict", options=sorted(df['Verdict'].unique()))
                with c4: team_filter = st.multiselect("Team", options=sorted(df['Team'].astype(str).unique()))
                c_sort, _ = st.columns([1, 3])
                with c_sort: sort_order = st.selectbox("Sort Order", ["Highest Projection", "💎 Best Edge (Vegas > ESPN)", "🚩 Worst Edge (Vegas < ESPN)"])

                if search_txt: df = df[df['Player'].str.lower().str.contains(search_txt)]
                if pos_filter: df = df[df['Position'].isin(pos_filter)]
                if verdict_filter: df = df[df['Verdict'].isin(verdict_filter)]
                if team_filter: df = df[df['Team'].isin(team_filter)]
                if "Highest Projection" in sort_order: df = df.sort_values(by="Proj Pts", ascending=False)
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
    st.caption("Dynasty history. The ghosts of seasons past.")
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
