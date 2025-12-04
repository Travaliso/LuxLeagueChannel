import streamlit as st
from luxury_utils import *
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# ------------------------------------------------------------------
# 1. SETUP
# ------------------------------------------------------------------
st.set_page_config(page_title="Luxury League Dashboard", page_icon="💎", layout="wide")
inject_luxury_css()

# CONSTANTS
START_YEAR = 2021 

# ------------------------------------------------------------------
# 2. CONNECTION
# ------------------------------------------------------------------
try:
    league_id = st.secrets["league_id"]
    swid = st.secrets["swid"]
    espn_s2 = st.secrets["espn_s2"]
    openai_key = st.secrets.get("openai_key")
    odds_api_key = st.secrets.get("odds_api_key")
    year = 2025

    @st.cache_resource
    def connect_to_league():
        return League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)

    league = connect_to_league()
except Exception as e:
    st.error(f"🔒 Connection Error: {e}")
    st.stop()

# ------------------------------------------------------------------
# 3. SIDEBAR NAVIGATION
# ------------------------------------------------------------------
st.sidebar.title("🥂 The Concierge")
current_week = league.current_week - 1
if current_week == 0: current_week = 1
selected_week = st.sidebar.slider("Select Week", 1, current_week, current_week)
st.sidebar.markdown("---")

# DEFINING ALL PAGES
P_LEDGER = "📜 The Ledger"
P_HIERARCHY = "📈 The Hierarchy"
P_AUDIT = "🔎 The Audit"
P_HEDGE = "💎 The Hedge Fund"
P_IPO = "📊 The IPO Audit"        # <--- NEW
P_LAB = "🧬 The Lab"
P_FORECAST = "🔮 The Forecast"
P_MULTI = "🌌 The Multiverse"     # <--- NEW
P_NEXT = "🚀 Next Week"
P_PROP = "📊 The Prop Desk"
P_DEAL = "🤝 The Dealmaker"
P_DARK = "🕵️ The Dark Pool"
P_TROPHY = "🏆 Trophy Room"
P_VAULT = "⏳ The Vault"

page_options = [P_LEDGER, P_HIERARCHY, P_AUDIT, P_HEDGE, P_IPO, P_LAB, P_FORECAST, P_MULTI, P_NEXT, P_PROP, P_DEAL, P_DARK, P_TROPHY, P_VAULT]
selected_page = st.sidebar.radio("Navigation", page_options, label_visibility="collapsed")

st.sidebar.markdown("---")
if st.sidebar.button("📄 Generate PDF Report"):
    with luxury_spinner("Compiling Intelligence Report..."):
        if "recap" not in st.session_state: st.session_state["recap"] = "Analysis Generated for PDF."
        if "awards" not in st.session_state: st.session_state["awards"] = calculate_season_awards(league, current_week)
        if "playoff_odds" not in st.session_state: st.session_state["playoff_odds"] = run_monte_carlo_simulation(league)

        pdf = PDF()
        pdf.add_page()
        pdf.chapter_title(f"WEEK {selected_week} EXECUTIVE BRIEFING")
        pdf.chapter_body(st.session_state["recap"].replace("*", "").replace("#", ""))
        
        awards = st.session_state["awards"]
        pdf.chapter_title("THE TROPHY ROOM")
        if awards['MVP']: pdf.chapter_body(f"MVP: {awards['MVP']['Name']} ({awards['MVP']['Points']:.1f} pts)")
        if awards['Best Manager']: pdf.chapter_body(f"The Whale: {awards['Best Manager']['Team']} ({awards['Best Manager']['Points']:.1f} pts)")
        
        if "playoff_odds" in st.session_state:
            pdf.chapter_title("PLAYOFF PROJECTIONS")
            df_odds = st.session_state["playoff_odds"]
            if df_odds is not None and not df_odds.empty:
                for i, row in df_odds.head(5).iterrows(): pdf.chapter_body(f"{row['Team']}: {row['Playoff Odds']:.1f}%")

        html = create_download_link(pdf.output(dest="S").encode("latin-1"), f"Luxury_League_Week_{selected_week}.pdf")
        st.sidebar.markdown(html, unsafe_allow_html=True)

# ------------------------------------------------------------------
# 4. DATA PROCESSING
# ------------------------------------------------------------------
if 'box_scores' not in st.session_state or st.session_state.get('week') != selected_week:
    with luxury_spinner(f"Accessing Week {selected_week} Data..."):
        st.session_state['box_scores'] = league.box_scores(week=selected_week)
        st.session_state['week'] = selected_week
    st.rerun()

box_scores = st.session_state['box_scores']
matchup_data, efficiency_data, all_active_players, bench_highlights = [], [], [], []

for game in box_scores:
    home, away = game.home_team, game.away_team
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
    matchup_data.append({"Home": home.team_name, "Home Score": game.home_score, "Home Logo": get_logo(home), "Home Roster": h_r, "Away": away.team_name, "Away Score": game.away_score, "Away Logo": get_logo(away), "Away Roster": a_r})
    efficiency_data.append({"Team": home.team_name, "Starters": h_s, "Bench": h_b, "Total Potential": h_s + h_b})
    efficiency_data.append({"Team": away.team_name, "Starters": a_s, "Bench": a_b, "Total Potential": a_s + a_b})

df_eff = pd.DataFrame(efficiency_data).sort_values(by="Total Potential", ascending=False)
df_players = pd.DataFrame(all_active_players).sort_values(by="Points", ascending=False).head(5)
df_bench_stars = pd.DataFrame(bench_highlights).sort_values(by="Score", ascending=False).head(5)

# ------------------------------------------------------------------
# 5. DASHBOARD UI
# ------------------------------------------------------------------
st.title(f"🏛️ Luxury League Protocol: Week {selected_week}")
st.markdown("### 🌟 Weekly Elite")
h1, h2, h3 = st.columns(3)
top_3 = df_players.head(3).reset_index(drop=True)
if len(top_3) >= 1: render_hero_card(h1, top_3.iloc[0])
if len(top_3) >= 2: render_hero_card(h2, top_3.iloc[1])
if len(top_3) >= 3: render_hero_card(h3, top_3.iloc[2])
st.markdown("---")

# --- PAGES ---
if selected_page == P_LEDGER:
    if "recap" not in st.session_state:
        with luxury_spinner("Analyst is reviewing portfolios..."): 
            st.session_state["recap"] = get_weekly_recap(openai_key, selected_week, df_eff.iloc[0]['Team'])
    st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ The Studio Report</h3>{st.session_state["recap"]}</div>', unsafe_allow_html=True)
    st.header("Weekly Transactions")
    c1, c2 = st.columns(2)
    for i, m in enumerate(matchup_data):
        col = c1 if i % 2 == 0 else c2
        with col:
            st.markdown(f"""<div class="luxury-card" style="padding: 15px; margin-bottom: 10px;"><div style="display: flex; justify-content: space-between; align-items: center;"><div style="text-align: center; width: 40%;"><img src="{m['Home Logo']}" width="50" style="border-radius: 50%; border: 2px solid #00C9FF; padding: 2px;"><div style="font-weight: 700; color: white; font-size: 0.9em; margin-top: 5px;">{m['Home']}</div><div style="font-size: 20px; color: #00C9FF; font-weight: 800;">{m['Home Score']}</div></div><div style="color: #a0aaba; font-size: 10px; font-weight: bold;">VS</div><div style="text-align: center; width: 40%;"><img src="{m['Away Logo']}" width="50" style="border-radius: 50%; border: 2px solid #0072ff; padding: 2px;"><div style="font-weight: 700; color: white; font-size: 0.9em; margin-top: 5px;">{m['Away']}</div><div style="font-size: 20px; color: #00C9FF; font-weight: 800;">{m['Away Score']}</div></div></div></div>""", unsafe_allow_html=True)
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
    if "rank_comm" not in st.session_state:
        with luxury_spinner("Analyzing hierarchy..."): 
            st.session_state["rank_comm"] = get_rankings_commentary(openai_key, df_eff.iloc[0]['Team'], df_eff.iloc[-1]['Team'])
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
            with luxury_spinner("Compiling Assets..."): st.session_state["df_advanced"] = calculate_heavy_analytics(league, current_week); st.rerun()
    else:
        fig = px.scatter(st.session_state["df_advanced"], x="Power Score", y="Wins", text="Team", size="Points For", color="Luck Rating", color_continuous_scale=["#7209b7", "#4361ee", "#4cc9f0"], title="Luck Matrix", height=600)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aaba")
        fig.update_traces(marker=dict(size=15, line=dict(width=2, color='White')), textposition='top center')
        st.plotly_chart(fig, use_container_width=True)

elif selected_page == P_IPO:
    st.header("📊 The IPO Audit")
    st.caption("ROI Analysis on Draft Capital vs. Actual Returns.")
    if "draft_roi" not in st.session_state:
        if st.button("📠 Run Audit"):
             with luxury_spinner("Auditing draft capital..."):
                 df_roi, prescient_data = calculate_draft_analysis(league)
                 st.session_state["draft_roi"] = df_roi
                 st.session_state["prescient"] = prescient_data
                 st.rerun()
    else:
        df_roi = st.session_state["draft_roi"]
        prescient = st.session_state["prescient"]
        st.markdown(f"""<div class="luxury-card" style="border-left: 4px solid #92FE9D; background: linear-gradient(90deg, rgba(146, 254, 157, 0.1), rgba(17, 25, 40, 0.8)); display: flex; align-items: center;"><div style="flex: 1; text-align: center;"><img src="{prescient['Logo']}" style="width: 90px; border-radius: 50%; border: 3px solid #92FE9D; box-shadow: 0 0 20px rgba(146, 254, 157, 0.4);"></div><div style="flex: 3; padding-left: 20px;"><h3 style="color: #92FE9D; margin: 0; text-transform: uppercase; letter-spacing: 2px;">👁️ The Prescient One</h3><div style="font-size: 1.8rem; font-weight: 900; color: white;">{prescient['Team']}</div><div style="color: #a0aaba; font-size: 1.1rem;">Generated <b>{prescient['Points']:.0f} points</b> from non-drafted assets while securing <b>{prescient['Wins']} Wins</b>.</div><div style="color: #92FE9D; font-size: 0.9rem; margin-top: 5px;">"Highest impact from the Waiver Wire among contenders."</div></div></div>""", unsafe_allow_html=True)
        st.divider()
        if not df_roi.empty:
            fig = px.scatter(df_roi, x="Pick Overall", y="Points", color="Team", hover_data=["Player", "Round", "Position"], title="Draft Pick ROI", height=600, color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aaba", xaxis=dict(autorange="reversed", title="Draft Pick (Lower is Higher Cost)"), yaxis=dict(title="Total Points (Return)"), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            fig.update_traces(marker=dict(size=12, line=dict(width=1, color='White'), opacity=0.8))
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
    c1, c2 = st.columns([3, 1])
    with c1: st.header("🧬 The Lab (Next Gen Biometrics)")
    with c2:
         if st.button("🧪 Analyze Roster"):
             with luxury_spinner("Calibrating Satellites..."): st.session_state["trigger_lab"] = True; st.rerun()
    with st.expander("🔎 Biometric Legend", expanded=False): st.info("WOPR: Weighted Opp. | CPOE: Completion % Over Exp | RYOE: Rush Yards Over Exp")
    
    target_team = st.selectbox("Select Test Subject:", [t.team_name for t in league.teams])
    if st.session_state.get("trigger_lab"):
        roster_obj = next(t for t in league.teams if t.team_name == target_team).roster
        st.session_state["ngs_data"] = analyze_nextgen_metrics_v3(roster_obj, year)
        st.session_state["trigger_lab"] = False; st.rerun()
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
            with luxury_spinner("Running Monte Carlo simulations..."): st.session_state["playoff_odds"] = run_monte_carlo_simulation(league); st.rerun()
    else:
        st.dataframe(st.session_state["playoff_odds"], use_container_width=True, hide_index=True, column_config={"Playoff Odds": st.column_config.ProgressColumn("Prob", format="%.1f%%", min_value=0, max_value=100)})
        if st.button("🔄 Re-Simulate"): del st.session_state["playoff_odds"]; st.rerun()

elif selected_page == P_MULTI:
    st.header("🌌 The Multiverse")
    st.caption("Force specific outcomes to see how they impact your playoff odds.")
    
    if "base_odds" not in st.session_state:
        with luxury_spinner("Calculating Baseline Reality..."): st.session_state["base_odds"] = run_monte_carlo_simulation(league)
    
    next_week = league.current_week
    box_scores = league.box_scores(week=next_week)
    
    forced_winners = []
    st.markdown(f"### 🎛️ Week {next_week} Control Panel")
    with st.form("multiverse_form"):
        c1, c2 = st.columns(2)
        for i, game in enumerate(box_scores):
            col = c1 if i % 2 == 0 else c2
            with col:
                st.markdown(f"**{game.home_team.team_name}** vs **{game.away_team.team_name}**")
                choice = st.radio("Result:", ["Simulate", f"{game.home_team.team_name} Win", f"{game.away_team.team_name} Win"], key=f"game_{i}", label_visibility="collapsed", horizontal=True)
                if "Home" in str(choice) or game.home_team.team_name in str(choice): forced_winners.append(game.home_team.team_name)
                elif "Away" in str(choice) or game.away_team.team_name in str(choice): forced_winners.append(game.away_team.team_name)
        st.markdown("---")
        run_scenario = st.form_submit_button("🔮 Enter The Multiverse")

    if run_scenario:
        with luxury_spinner("Simulating Alternate Timeline..."):
            df_scenario = run_multiverse_simulation(league, forced_winners_list=forced_winners)
            df_base = st.session_state["base_odds"][["Team", "Playoff Odds"]].rename(columns={"Playoff Odds": "Base Odds"})
            df_final = pd.merge(df_scenario, df_base, on="Team")
            df_final["Impact"] = df_final["New Odds"] - df_final["Base Odds"]
            st.session_state["scenario_results"] = df_final.sort_values(by="New Odds", ascending=False)
            
    if "scenario_results" in st.session_state:
        st.divider(); st.subheader("🧬 Timeline Results")
        st.dataframe(st.session_state["scenario_results"], use_container_width=True, hide_index=True, column_order=["Team", "Base Odds", "New Odds", "Impact"], column_config={"Base Odds": st.column_config.NumberColumn(format="%.1f%%"), "New Odds": st.column_config.ProgressColumn("Scenario Odds", format="%.1f%%", min_value=0, max_value=100), "Impact": st.column_config.NumberColumn("Impact", format="%+.1f%%")})

elif selected_page == P_NEXT:
    try:
        next_week = league.current_week
        box = league.box_scores(week=next_week)
        games = [{"home": g.home_team.team_name, "away": g.away_team.team_name, "spread": f"{abs(g.home_projected-g.away_projected):.1f}"} for g in box]
        if "next_week_comm" not in st.session_state:
            with luxury_spinner("Checking Vegas lines..."): st.session_state["next_week_commentary"] = get_next_week_preview(openai_key, games)
        st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ Vegas Insider</h3>{st.session_state["next_week_commentary"]}</div>', unsafe_allow_html=True)
        st.header("Matchups")
        c1, c2 = st.columns(2)
        for i, g in enumerate(box):
             with c1 if i % 2 == 0 else c2:
                 st.markdown(f"""<div class="luxury-card" style="padding: 15px;"><div style="display:flex; justify-content:space-between; text-align:center;"><div style="flex:2; color:white;"><b>{g.home_team.team_name}</b><br><span style="color:#00C9FF;">{g.home_projected:.1f}</span></div><div style="flex:1; color:#a0aaba; font-size:0.8em;">VS</div><div style="flex:2; color:white;"><b>{g.away_team.team_name}</b><br><span style="color:#92FE9D;">{g.away_projected:.1f}</span></div></div></div>""", unsafe_allow_html=True)
    except: st.info("Projections unavailable.")

elif selected_page == P_PROP:
    st.header("📊 The Prop Desk")
    if not odds_api_key: st.warning("Missing Odds API Key")
    else:
        if "vegas_data" not in st.session_state:
            with luxury_spinner("Calling Vegas..."): st.session_state["vegas_data"] = get_vegas_props(odds_api_key)
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
        with luxury_spinner("Analyzing..."):
            ta = next(t for t in league.teams if t.team_name == t1)
            tb = next(t for t in league.teams if t.team_name == t2)
            ra = [f"{p.name} ({p.position})" for p in ta.roster]
            rb = [f"{p.name} ({p.position})" for p in tb.roster]
            prop = get_ai_trade_proposal(openai_key, t1, t2, ra, rb)
            st.markdown(f'<div class="luxury-card studio-box"><h3>Proposed Deal</h3>{prop}</div>', unsafe_allow_html=True)

elif selected_page == P_DARK:
    st.header("🕵️ The Dark Pool")
    has_data = "dark_pool_data" in st.session_state
    if not has_data:
        if st.button("🔭 Scan Wire"):
             with luxury_spinner("Scouting..."):
                 df_pool = scan_dark_pool(league)
                 st.session_state["dark_pool_data"] = df_pool
                 if not df_pool.empty:
                     p_str = ", ".join([f"{r['Name']} ({r['Position']})" for i, r in df_pool.iterrows()])
                     st.session_state["scout_rpt"] = get_ai_scouting_report(openai_key, p_str)
                 st.rerun()
    else:
        if st.button("🔄 Rescan"): del st.session_state["dark_pool_data"]; st.rerun()
        if "scout_rpt" in st.session_state: st.markdown(f'<div class="luxury-card studio-box"><h3>📝 Scout\'s Notebook</h3>{st.session_state["scout_rpt"]}</div>', unsafe_allow_html=True)
        st.dataframe(st.session_state["dark_pool_data"], use_container_width=True)

elif selected_page == P_TROPHY:
    if "awards" not in st.session_state:
        if st.button("🏅 Unveil Awards"):
            with luxury_spinner("Engraving..."):
                st.session_state["awards"] = calculate_season_awards(league, current_week)
                aw = st.session_state["awards"]
                st.session_state["season_comm"] = get_season_retrospective(openai_key, aw['MVP']['Name'], aw['Best Manager']['Team'])
                st.rerun()
    else:
        aw = st.session_state["awards"]
        if "season_comm" in st.session_state: st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ State of the League</h3>{st.session_state["season_comm"]}</div>', unsafe_allow_html=True)
        st.divider()
        
        # NARRATIVE GENERATOR
        def generate_narrative(award_type, team_name, value, extra=""):
            if award_type == "Oracle": return f"The ultimate strategist. {team_name} achieved a staggering **{value:.1f}% efficiency rating**."
            elif award_type == "Sniper": return f"Leagues are won on the wire. {team_name} extracted **{value:.1f} points** from free agents."
            elif award_type == "Purple": return f"A season defined by grit. {team_name} managed **{value} injury designations**."
            elif award_type == "Hoarder": return f"An embarrassment of riches. {team_name} left **{value:.1f} points** on the bench."
            elif award_type == "Toilet": return f"The offense couldn't launch. Scoring only **{value:.1f} total points**."
            elif award_type == "Blowout": return f"A historic beatdown. {team_name} lost by **{value:.1f} points** in Week {extra}."
            return ""

        # PODIUM
        st.markdown("<h2 style='text-align: center;'>🏆 THE PODIUM</h2>", unsafe_allow_html=True)
        pod = aw.get("Podium", [])
        c_silv, c_gold, c_brnz = st.columns([1, 1.2, 1])
        if len(pod) > 1:
            with c_silv: st.markdown(f"""<div class="podium-step silver"><img src="{get_logo(pod[1])}" style="width:80px; border-radius:50%; border:3px solid #C0C0C0; display:block; margin:0 auto;"><div style="color:white; font-weight:bold; margin-top:10px;">{pod[1].team_name}</div><div style="color:#C0C0C0;">{pod[1].wins}-{pod[1].losses}</div><div class="rank-num">2</div></div>""", unsafe_allow_html=True)
        if len(pod) > 0:
            with c_gold: st.markdown(f"""<div class="podium-step gold"><img src="{get_logo(pod[0])}" style="width:100px; border-radius:50%; border:4px solid #FFD700; display:block; margin:0 auto; box-shadow:0 0 20px rgba(255,215,0,0.6);"><div style="color:white; font-weight:900; font-size:1.4rem; margin-top:15px;">{pod[0].team_name}</div><div style="color:#FFD700;">{pod[0].wins}-{pod[0].losses}</div><div class="rank-num">1</div></div>""", unsafe_allow_html=True)
        if len(pod) > 2:
            with c_brnz: st.markdown(f"""<div class="podium-step bronze"><img src="{get_logo(pod[2])}" style="width:70px; border-radius:50%; border:3px solid #CD7F32; display:block; margin:0 auto;"><div style="color:white; font-weight:bold; margin-top:10px;">{pod[2].team_name}</div><div style="color:#CD7F32;">{pod[2].wins}-{pod[2].losses}</div><div class="rank-num">3</div></div>""", unsafe_allow_html=True)
        
        st.markdown("---")
        st.subheader("🎖️ Deep Dive Honors")
        col_a, col_b, col_c, col_d = st.columns(4)
        ora = aw['Oracle']
        with col_a: st.markdown(f"""<div class="luxury-card award-card"><img src="{ora['Logo']}" style="width:60px; border-radius:50%; margin-bottom:10px;"><h4 style="color:#00C9FF; margin:0;">The Oracle</h4><div style="font-size:1.1rem; font-weight:bold; color:white;">{ora['Team']}</div><div style="color:#a0aaba; font-size:0.8rem;">{ora['Eff']:.1f}% Efficiency</div><div class="award-blurb">{generate_narrative("Oracle", ora['Team'], ora['Eff'])}</div></div>""", unsafe_allow_html=True)
        sni = aw['Sniper']
        with col_b: st.markdown(f"""<div class="luxury-card award-card"><img src="{sni['Logo']}" style="width:60px; border-radius:50%; margin-bottom:10px;"><h4 style="color:#00C9FF; margin:0;">The Sniper</h4><div style="font-size:1.1rem; font-weight:bold; color:white;">{sni['Team']}</div><div style="color:#a0aaba; font-size:0.8rem;">{sni['Pts']:.1f} Waiver Pts</div><div class="award-blurb">{generate_narrative("Sniper", sni['Team'], sni['Pts'])}</div></div>""", unsafe_allow_html=True)
        pur = aw['Purple']
        with col_c: st.markdown(f"""<div class="luxury-card award-card"><img src="{pur['Logo']}" style="width:60px; border-radius:50%; margin-bottom:10px;"><h4 style="color:#00C9FF; margin:0;">Purple Heart</h4><div style="font-size:1.1rem; font-weight:bold; color:white;">{pur['Team']}</div><div style="color:#a0aaba; font-size:0.8rem;">{pur['Count']} Injuries</div><div class="award-blurb">{generate_narrative("Purple", pur['Team'], pur['Count'])}</div></div>""", unsafe_allow_html=True)
        hoa = aw['Hoarder']
        with col_d: st.markdown(f"""<div class="luxury-card award-card"><img src="{hoa['Logo']}" style="width:60px; border-radius:50%; margin-bottom:10px;"><h4 style="color:#00C9FF; margin:0;">The Hoarder</h4><div style="font-size:1.1rem; font-weight:bold; color:white;">{hoa['Team']}</div><div style="color:#a0aaba; font-size:0.8rem;">{hoa['Pts']:.1f} Bench Pts</div><div class="award-blurb">{generate_narrative("Hoarder", hoa['Team'], hoa['Pts'])}</div></div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("<h3 style='color: #FF4B4B; text-align: center;'>🚽 THE TOILET BOWL</h3>", unsafe_allow_html=True)
        t_col1, t_col2 = st.columns(2)
        toilet = aw['Toilet']
        with t_col1: st.markdown(f"""<div class="luxury-card shame-card"><img src="{toilet['Logo']}" width="80" style="border-radius:50%; border:3px solid #FF4B4B; margin-right:20px;"><div><div style="color:#FF4B4B; font-weight:bold;">LOWEST SCORING FRANCHISE</div><div style="font-size:1.8rem; font-weight:900; color:white;">{toilet['Team']}</div><div style="color:#aaa;">{toilet['Pts']:.1f} Pts</div><div class="award-blurb" style="color:#FF8888;">{generate_narrative("Toilet", toilet['Team'], toilet['Pts'])}</div></div></div>""", unsafe_allow_html=True)
        blowout = aw['Blowout']
        with t_col2: st.markdown(f"""<div class="luxury-card shame-card"><div style="color:#FF4B4B; font-weight:bold;">💥 BIGGEST BLOWOUT VICTIM</div><div style="font-size:1.5rem; font-weight:900; color:white; margin:10px 0;">{blowout['Loser']}</div><div style="color:#aaa;">Def. by {blowout['Winner']} (+{blowout['Margin']:.1f} pts)</div><div class="award-blurb" style="color:#FF8888;">{generate_narrative("Blowout", blowout['Loser'], blowout['Margin'], blowout['Week'])}</div></div>""", unsafe_allow_html=True)
        
elif selected_page == P_VAULT:
    st.header("⏳ The Dynasty Vault")
    if "dynasty_lead" not in st.session_state:
        if st.button("🔓 Unlock Vault"):
            with luxury_spinner("Time Traveling..."):
                df_raw = get_dynasty_data(league_id, espn_s2, swid, year, START_YEAR)
                st.session_state["dynasty_lead"] = process_dynasty_leaderboard(df_raw)
                st.session_state["dynasty_raw"] = df_raw
                st.rerun()
    else:
        st.dataframe(st.session_state["dynasty_lead"], use_container_width=True)
        fig = px.line(st.session_state["dynasty_raw"], x="Year", y="Wins", color="Manager", markers=True)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aaba")
        st.plotly_chart(fig, use_container_width=True)
