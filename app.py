import streamlit as st
from luxury_utils import *
import plotly.express as px
import plotly.graph_objects as go

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

# LOAD ASSETS
lottie_loading = load_lottieurl("https://lottie.host/5a882010-89b6-45bc-8a4d-06886982f8d8/WfK7bXoGqj.json")
lottie_forecast = load_lottieurl("https://lottie.host/936c69f6-0b89-4b68-b80c-0390f777c5d7/C0Z2y3S0bM.json")
lottie_trophy = load_lottieurl("https://lottie.host/362e7839-2425-4c75-871d-534b82d02c84/hL9w4jR9aF.json")
lottie_trade = load_lottieurl("https://lottie.host/e65893a7-e54e-4f0b-9366-0749024f2b1d/z2Xg6c4h5r.json")
lottie_wire = load_lottieurl("https://lottie.host/4e532997-5b65-4f4c-8b2b-077555627798/7Q9j7Z9g9z.json")
lottie_lab = load_lottieurl("https://lottie.host/49907932-975d-453d-b8f1-2d6408468123/bF2y8T8k7s.json")

# ------------------------------------------------------------------
# 3. SIDEBAR NAVIGATION
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
    matchup_data.append({"Home": home.team_name, "Home Score": game.home_score, "Home Logo": home.logo_url, "Home Roster": h_r, "Away": away.team_name, "Away Score": game.away_score, "Away Logo": away.logo_url, "Away Roster": a_r})
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
hero_c1, hero_c2, hero_c3 = st.columns(3)
def render_hero_card(col, player):
    with col:
        st.markdown(f"""
        <div class="luxury-card" style="padding: 15px; display: flex; align-items: center; justify-content: start;">
            <img src="https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{player['ID']}.png&w=80&h=60" 
                 style="border-radius: 8px; margin-right: 15px; border: 1px solid rgba(0, 201, 255, 0.5); box-shadow: 0 0 10px rgba(0, 201, 255, 0.2);">
            <div>
                <div style="color: #ffffff; font-weight: 800; font-size: 16px; text-transform: uppercase; letter-spacing: 1px;">{player['Name']}</div>
                <div style="color: #00C9FF; font-size: 14px; font-weight: 600;">{player['Points']} PTS</div>
                <div style="color: #a0aaba; font-size: 11px;">{player['Team']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

top_3 = df_players.head(3).reset_index(drop=True)
if len(top_3) >= 1: render_hero_card(hero_c1, top_3.iloc[0])
if len(top_3) >= 2: render_hero_card(hero_c2, top_3.iloc[1])
if len(top_3) >= 3: render_hero_card(hero_c3, top_3.iloc[2])
st.markdown("---")

# --- UI ROUTER ---
if selected_page == P_LEDGER:
    if "recap" not in st.session_state:
        with luxury_spinner("Analyst is reviewing portfolios..."): 
            top_team = df_eff.iloc[0]['Team']
            st.session_state["recap"] = ai_response(openai_key, f"Write a DETAILED, 5-10 sentence fantasy recap for Week {selected_week}. Highlight Powerhouse: {top_team}. Style: Wall Street Report.", 800)
    st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ The Studio Report</h3>{st.session_state["recap"]}</div>', unsafe_allow_html=True)
    st.header("Weekly Transactions")
    m_col1, m_col2 = st.columns(2)
    for i, m in enumerate(matchup_data):
        current_col = m_col1 if i % 2 == 0 else m_col2
        with current_col:
            st.markdown(f"""<div class="luxury-card" style="padding: 15px; margin-bottom: 10px;"><div style="display: flex; justify-content: space-between; align-items: center;"><div style="text-align: center; width: 40%;"><img src="{m['Home Logo']}" width="50" style="border-radius: 50%; border: 2px solid #00C9FF; padding: 2px; box-shadow: 0 0 15px rgba(0, 201, 255, 0.4);"><div style="font-weight: 700; color: white; font-size: 0.9em; margin-top: 5px;">{m['Home']}</div><div style="font-size: 20px; color: #00C9FF; font-weight: 800;">{m['Home Score']}</div></div><div style="color: #a0aaba; font-size: 10px; font-weight: bold;">VS</div><div style="text-align: center; width: 40%;"><img src="{m['Away Logo']}" width="50" style="border-radius: 50%; border: 2px solid #0072ff; padding: 2px; box-shadow: 0 0 15px rgba(146, 254, 157, 0.4);"><div style="font-weight: 700; color: white; font-size: 0.9em; margin-top: 5px;">{m['Away']}</div><div style="font-size: 20px; color: #00C9FF; font-weight: 800;">{m['Away Score']}</div></div></div></div>""", unsafe_allow_html=True)
            with st.expander(f"📉 View Lineups"):
                max_len = max(len(m['Home Roster']), len(m['Away Roster']))
                df_matchup = pd.DataFrame({
                    f"{m['Home']}": [p['Name'] for p in m['Home Roster']] + [''] * (max_len - len(m['Home Roster'])),
                    f"{m['Home']} Pts": [p['Score'] for p in m['Home Roster']] + [0] * (max_len - len(m['Home Roster'])),
                    f"{m['Away']} Pts": [p['Score'] for p in m['Away Roster']] + [0] * (max_len - len(m['Away Roster'])),
                    f"{m['Away']}": [p['Name'] for p in m['Away Roster']] + [''] * (max_len - len(m['Away Roster'])),
                })
                st.dataframe(df_matchup, use_container_width=True, hide_index=True, column_config={f"{m['Home']} Pts": st.column_config.NumberColumn(format="%.1f"), f"{m['Away']} Pts": st.column_config.NumberColumn(format="%.1f")})

elif selected_page == P_HIERARCHY:
    if "rank_comm" not in st.session_state:
        with luxury_spinner("Analyzing hierarchy..."): 
            st.session_state["rank_comm"] = ai_response(openai_key, f"Write a 5-8 sentence commentary on Power Rankings. Praise {df_eff.iloc[0]['Team']} and mock {df_eff.iloc[-1]['Team']}. Style: Stephen A. Smith.")
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
    if not df_bench_stars.empty: 
        st.markdown("#### 🚨 'Should Have Started'")
        st.dataframe(df_bench_stars, use_container_width=True, hide_index=True)

elif selected_page == P_HEDGE:
    st.header("Market Analytics")
    if "df_advanced" not in st.session_state:
        st.info("⚠️ Accessing historical market data requires intensive calculation.")
        if st.button("🚀 Analyze Market Data"):
            with luxury_spinner("Compiling Assets..."): st.session_state["df_advanced"] = calculate_heavy_analytics(league, current_week); st.rerun()
    else:
        df_advanced = st.session_state["df_advanced"]
        fig = px.scatter(df_advanced, x="Power Score", y="Wins", text="Team", size="Points For", color="Luck Rating", color_continuous_scale=["#7209b7", "#4361ee", "#4cc9f0"], title="Luck Matrix", height=600)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aaba")
        fig.update_traces(marker=dict(size=15, line=dict(width=2, color='White')), textposition='top center')
        st.plotly_chart(fig, use_container_width=True)

elif selected_page == P_LAB:
    with st.container():
        c1, c2 = st.columns([3, 1])
        with c1: st.header("🧬 The Lab (Next Gen Biometrics)")
        with c2:
             if st.button("🧪 Analyze Roster"):
                 with luxury_spinner("Calibrating Satellites..."):
                     st.session_state["trigger_lab"] = True
                     st.rerun()
    with st.expander("🔎 Biometric Legend", expanded=False):
        st.markdown("- 💎 **ELITE:** Top 10%\n- 🚀 **MONSTER:** High Efficiency\n- 🎯 **SNIPER:** High Accuracy")
    
    team_list = [t.team_name for t in league.teams]
    target_team = st.selectbox("Select Test Subject:", team_list)
    
    if st.session_state.get("trigger_lab"):
        roster_obj = next(t for t in league.teams if t.team_name == target_team).roster
        df_ngs = analyze_nextgen_metrics_v3(roster_obj, year)
        st.session_state["ngs_data"] = df_ngs
        st.session_state["trigger_lab"] = False
        st.rerun()
            
    if "ngs_data" in st.session_state and not st.session_state["ngs_data"].empty:
        df_res = st.session_state["ngs_data"]
        cols = st.columns(2)
        for i, row in df_res.iterrows():
            col = cols[i % 2]
            with col:
                st.markdown(f"""<div class="luxury-card" style="border-left: 4px solid #00C9FF; display: flex; align-items: center;"><img src="https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{row['ID']}.png&w=80&h=60" style="border-radius: 8px; margin-right: 15px; border: 1px solid rgba(0, 201, 255, 0.3);"><div style="flex: 1;"><h4 style="margin:0; color: white; font-size: 1.1em;">{row['Player']}</h4><div style="font-size: 0.8em; color: #a0aaba;">{row['Team']} • {row['Position']}</div><div style="color: #00C9FF; font-weight: bold; font-size: 0.9em; margin-top: 4px;">{row['Verdict']}</div></div><div style="text-align: right;"><div style="font-size: 0.75em; color: #a0aaba;">{row['Metric']}</div><div style="font-size: 1.4em; font-weight: bold; color: white;">{row['Value']}</div><div style="font-size: 0.75em; color: #92FE9D;">{row['Alpha Stat']}</div></div></div>""", unsafe_allow_html=True)
    elif "ngs_data" in st.session_state:
        st.info("No Next Gen Data found.")

elif selected_page == P_FORECAST:
    st.header("The Crystal Ball")
    if "playoff_odds" not in st.session_state:
        if st.button("🎲 Run Simulation"):
            with luxury_spinner("Running Monte Carlo simulations..."): st.session_state["playoff_odds"] = run_monte_carlo_simulation(league); st.rerun()
    else:
        df_odds = st.session_state["playoff_odds"]
        st.dataframe(df_odds, use_container_width=True, hide_index=True, column_config={"Playoff Odds": st.column_config.ProgressColumn("Prob", format="%.1f%%", min_value=0, max_value=100)})
        if st.button("🔄 Re-Simulate"): del st.session_state["playoff_odds"]; st.rerun()

elif selected_page == P_NEXT:
    try:
        next_week = league.current_week
        next_box_scores = league.box_scores(week=next_week)
        games_list = []
        for game in next_box_scores:
            h_proj, a_proj = game.home_projected, game.away_projected
            if h_proj == 0: h_proj = 100
            if a_proj == 0: a_proj = 100
            spread = abs(h_proj - a_proj)
            games_list.append({"home": game.home_team.team_name, "away": game.away_team.team_name, "spread": f"{spread:.1f}"})
        if "next_week_commentary" not in st.session_state:
            with luxury_spinner("Checking Vegas lines..."): st.session_state["next_week_commentary"] = ai_response(openai_key, f"Act as a Vegas Sports Bookie. Preview next week's matchups: {games_list}. Pick 'Lock of the Week' and 'Upset Alert'.")
        st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ Vegas Insider</h3>{st.session_state["next_week_commentary"]}</div>', unsafe_allow_html=True)
        st.header("Next Week's Market Preview")
        nc1, nc2 = st.columns(2)
        for i, game in enumerate(next_box_scores):
            h_proj, a_proj = game.home_projected, game.away_projected
            if h_proj == 0: h_proj = 100
            if a_proj == 0: a_proj = 100
            spread = abs(h_proj - a_proj)
            fav = game.home_team.team_name if h_proj > a_proj else game.away_team.team_name
            curr_col = nc1 if i % 2 == 0 else nc2
            with curr_col:
                st.markdown(f"""<div class="luxury-card" style="padding: 15px;"><div style="display: flex; justify-content: space-between; align-items: center; text-align: center;"><div style="flex: 2;"><div style="font-weight: bold; font-size: 1.1em; color: #ffffff;">{game.home_team.team_name}</div><div style="color: #00C9FF; text-shadow: 0 0 8px rgba(0, 201, 255, 0.4);">Proj: {h_proj:.1f}</div></div><div style="flex: 1; color: #a0aaba; font-size: 0.8em;"><div>VS</div><div style="color: #00C9FF; margin-top: 5px;">Fav: {fav}</div><div style="color: #fff;">+{spread:.1f}</div></div><div style="flex: 2;"><div style="font-weight: bold; font-size: 1.1em; color: #ffffff;">{game.away_team.team_name}</div><div style="color: #92FE9D; text-shadow: 0 0 8px rgba(146, 254, 157, 0.4);">Proj: {a_proj:.1f}</div></div></div></div>""", unsafe_allow_html=True)
    except: st.info("Projections unavailable.")

elif selected_page == P_PROP:
    st.header("📊 The Prop Desk (Vegas vs. ESPN)")
    if not odds_api_key: st.warning("Please add 'odds_api_key' to your secrets.")
    else:
        if "vegas_data" not in st.session_state:
            with luxury_spinner("Calling the bookies in Las Vegas..."): st.session_state["vegas_data"] = get_vegas_props(odds_api_key)
        df_vegas = st.session_state["vegas_data"]
        if df_vegas is not None and not df_vegas.empty:
            if "Status" in df_vegas.columns and df_vegas.iloc[0]["Status"] == "Market Closed":
                st.markdown("""<div class="luxury-card" style="border-left: 4px solid #FFD700;"><h3 style="color: #FFD700; margin-top: 0;">🏦 Market Status: ADJUSTMENT PERIOD</h3><p style="color: #e0e0e0;"><strong>Why is this empty?</strong> It is early in the week. Major books pull player props on Tuesdays.</p></div>""", unsafe_allow_html=True)
            else:
                next_week = league.current_week
                box = league.box_scores(week=next_week)
                trust_data = []
                for game in box:
                    all_players = game.home_lineup + game.away_lineup
                    for player in all_players:
                        if player.slot_position == 'BE': continue
                        match, score, index = process.extractOne(player.name, df_vegas['Player'].tolist())
                        if score > 85:
                            vegas_pts = df_vegas[df_vegas['Player'] == match].iloc[0]['Vegas Score']
                            espn_pts = player.projected_points
                            if espn_pts == 0: espn_pts = 0.1
                            delta = vegas_pts - espn_pts
                            status = "🚀 SMASH" if delta > 3 else "⚠️ TRAP" if delta < -3 else "⚖️ Fair"
                            trust_data.append({"Player": player.name, "Team": player.proTeam, "ESPN Proj": espn_pts, "Vegas Implied": round(vegas_pts, 2), "Delta": round(delta, 2), "Verdict": status})
                if trust_data:
                    st.dataframe(pd.DataFrame(trust_data).sort_values(by="Delta", ascending=False), use_container_width=True, hide_index=True, column_config={"Delta": st.column_config.NumberColumn("Trust Delta", format="%+.1f")})
                else: st.info("No prop lines found yet.")
        else: st.error("Could not fetch odds.")

elif selected_page == P_DEAL:
    st.header("🤝 The AI Dealmaker")
    c1, c2 = st.columns(2)
    with c1: t1 = st.selectbox("Select Team A", [t.team_name for t in league.teams], index=0)
    with c2: t2 = st.selectbox("Select Team B", [t.team_name for t in league.teams], index=1)
    if st.button("🤖 Generate Trade"):
        with luxury_spinner("Analyzing roster deficiencies..."):
            team_a = next(t for t in league.teams if t.team_name == t1)
            team_b = next(t for t in league.teams if t.team_name == t2)
            r_a = [f"{p.name} ({p.position})" for p in team_a.roster]
            r_b = [f"{p.name} ({p.position})" for p in team_b.roster]
            proposal = ai_response(openai_key, f"Act as Trade Broker. Propose a fair trade between Team A ({t1}): {r_a} and Team B ({t2}): {r_b}. Explain why.")
            st.markdown(f'<div class="luxury-card studio-box"><h3>Proposed Deal</h3>{proposal}</div>', unsafe_allow_html=True)

elif selected_page == P_DARK:
    st.header("🕵️ The Dark Pool (Waiver Wire)")
    has_data = "dark_pool_data" in st.session_state
    c1, c2 = st.columns([1, 4])
    with c1:
        if not has_data:
            if st.button("🔭 Scan Wire", type="primary"):
                with luxury_spinner("Scouting the wire..."):
                    df_pool = scan_dark_pool(league)
                    st.session_state["dark_pool_data"] = df_pool
                    if not df_pool.empty:
                        p_str = ", ".join([f"{r['Name']} ({r['Position']}, {r['Avg Pts']:.1f})" for i, r in df_pool.iterrows()])
                        st.session_state["scout_rpt"] = get_ai_scouting_report(p_str)
                    else:
                        st.session_state["scout_rpt"] = "No viable assets found."
                    st.rerun()
        else:
            if st.button("🔄 Rescan Wire"): 
                del st.session_state["dark_pool_data"]
                if "scout_rpt" in st.session_state: del st.session_state["scout_rpt"]
                st.rerun()
    if has_data:
        if "scout_rpt" in st.session_state: st.markdown(f'<div class="luxury-card studio-box"><h3>📝 Scout\'s Notebook</h3>{st.session_state["scout_rpt"]}</div>', unsafe_allow_html=True)
        if not st.session_state["dark_pool_data"].empty:
            st.dataframe(st.session_state["dark_pool_data"], use_container_width=True, hide_index=True, column_config={"Avg Pts": st.column_config.NumberColumn(format="%.1f"), "Total Pts": st.column_config.NumberColumn(format="%.1f")})
        else:
            st.warning("⚠️ No players found matching criteria.")

elif selected_page == P_TROPHY:
    if "awards" not in st.session_state:
        btn_container = st.empty()
        lottie_container = st.empty()
        if btn_container.button("🏅 Unveil Awards"):
            btn_container.empty()
            if lottie_trophy: 
                with lottie_container: st_lottie(lottie_trophy, height=200, key="trophy_anim")
            with luxury_spinner("Engraving trophies..."):
                st.session_state["awards"] = calculate_season_awards(league, current_week)
                awards_data = st.session_state["awards"]
                mvp_name = awards_data['MVP']['Name'] if awards_data['MVP'] else "N/A"
                best_mgr = awards_data['Best Manager']['Team'] if awards_data['Best Manager'] else "N/A"
                st.session_state["season_comm"] = ai_response(openai_key, f"Write a 'State of the Union' for the league based on awards. MVP: {mvp_name}. Best Manager: {best_mgr}. Style: Presidential.", 1000)
            lottie_container.empty()
            st.rerun()
    else:
        awards = st.session_state["awards"]
        if "season_comm" in st.session_state:
             st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ State of the League</h3>{st.session_state["season_comm"]}</div>', unsafe_allow_html=True)
        st.divider()
        st.markdown("<h2 style='text-align: center; margin-bottom: 30px;'>🏆 THE PODIUM</h2>", unsafe_allow_html=True)
        podium_teams = awards.get("Podium", [])
        p1 = podium_teams[0] if len(podium_teams) > 0 else None
        p2 = podium_teams[1] if len(podium_teams) > 1 else None
        p3 = podium_teams[2] if len(podium_teams) > 2 else None
        c_silv, c_gold, c_brnz = st.columns([1, 1.2, 1])
        with c_silv:
            if p2:
                st.markdown(f"""<div class="podium-step silver"><img src="{get_logo(p2)}" style="width: 80px; height: 80px; border-radius: 50%; border: 3px solid #C0C0C0; margin: 0 auto; display: block;"><div style="color: #fff; font-weight: bold; font-size: 1.1rem; margin-top: 10px;">{p2.team_name}</div><div style="color: #C0C0C0; font-size: 0.9rem;">{p2.wins}-{p2.losses}</div><div class="rank-num">2</div></div>""", unsafe_allow_html=True)
        with c_gold:
            if p1:
                st.markdown(f"""<div class="podium-step gold"><img src="{get_logo(p1)}" style="width: 100px; height: 100px; border-radius: 50%; border: 4px solid #FFD700; margin: 0 auto; display: block; box-shadow: 0 0 20px rgba(255, 215, 0, 0.6);"><div style="color: #fff; font-weight: 900; font-size: 1.4rem; margin-top: 15px;">{p1.team_name}</div><div style="color: #FFD700; font-size: 1rem;">{p1.wins}-{p1.losses}</div><div class="rank-num">1</div></div>""", unsafe_allow_html=True)
        with c_brnz:
            if p3:
                st.markdown(f"""<div class="podium-step bronze"><img src="{get_logo(p3)}" style="width: 70px; height: 70px; border-radius: 50%; border: 3px solid #CD7F32; margin: 0 auto; display: block;"><div style="color: #fff; font-weight: bold; font-size: 1.1rem; margin-top: 10px;">{p3.team_name}</div><div style="color: #CD7F32; font-size: 0.9rem;">{p3.wins}-{p3.losses}</div><div class="rank-num">3</div></div>""", unsafe_allow_html=True)
        st.markdown("---")
        st.subheader("🎖️ Deep Dive Honors")
        col_a, col_b, col_c, col_d = st.columns(4)
        ora = awards['Oracle']
        with col_a:
            st.markdown(f"""<div class="luxury-card award-card" style="text-align: center;"><img src="{ora['Logo']}" style="width: 60px; border-radius: 50%; margin-bottom: 10px;"><h4 style="color: #00C9FF; margin: 0;">The Oracle</h4><div style="font-size: 1.1rem; font-weight: bold; color: white;">{ora['Team']}</div><div style="color: #a0aaba; font-size: 0.8rem;">{ora['Eff']:.1f}% Efficiency</div><div class="award-blurb">Most optimal lineups set all season.</div></div>""", unsafe_allow_html=True)
        sni = awards['Sniper']
        with col_b:
            st.markdown(f"""<div class="luxury-card award-card" style="text-align: center;"><img src="{sni['Logo']}" style="width: 60px; border-radius: 50%; margin-bottom: 10px;"><h4 style="color: #00C9FF; margin: 0;">The Sniper</h4><div style="font-size: 1.1rem; font-weight: bold; color: white;">{sni['Team']}</div><div style="color: #a0aaba; font-size: 0.8rem;">{sni['Pts']:.1f} Waiver Pts</div><div class="award-blurb">Highest production from free agent pickups.</div></div>""", unsafe_allow_html=True)
        pur = awards['Purple']
        with col_c:
            st.markdown(f"""<div class="luxury-card award-card" style="text-align: center;"><img src="{pur['Logo']}" style="width: 60px; border-radius: 50%; margin-bottom: 10px;"><h4 style="color: #00C9FF; margin: 0;">Purple Heart</h4><div style="font-size: 1.1rem; font-weight: bold; color: white;">{pur['Team']}</div><div style="color: #a0aaba; font-size: 0.8rem;">{pur['Count']} Injuries</div><div class="award-blurb">Survived the most IR/Out designations.</div></div>""", unsafe_allow_html=True)
        hoa = awards['Hoarder']
        with col_d:
            st.markdown(f"""<div class="luxury-card award-card" style="text-align: center;"><img src="{hoa['Logo']}" style="width: 60px; border-radius: 50%; margin-bottom: 10px;"><h4 style="color: #00C9FF; margin: 0;">The Hoarder</h4><div style="font-size: 1.1rem; font-weight: bold; color: white;">{hoa['Team']}</div><div style="color: #a0aaba; font-size: 0.8rem;">{hoa['Pts']:.1f} Bench Pts</div><div class="award-blurb">Most points left on the bench.</div></div>""", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("<h3 style='color: #FF4B4B; text-align: center;'>🚽 THE TOILET BOWL (Shame Section)</h3>", unsafe_allow_html=True)
        t_col1, t_col2 = st.columns(2)
        toilet = awards['Toilet']
        with t_col1:
            st.markdown(f"""<div class="luxury-card shame-card" style="display: flex; align-items: center;"><img src="{toilet['Logo']}" width="80" style="border-radius: 50%; border: 3px solid #FF4B4B; margin-right: 20px;"><div><div style="color: #FF4B4B; font-weight: bold; letter-spacing: 1px;">LOWEST SCORING FRANCHISE</div><div style="font-size: 1.8rem; font-weight: 900; color: white;">{toilet['Team']}</div><div style="color: #aaa;">Only {toilet['Pts']:.1f} Total Points</div><div class="award-blurb" style="color: #FF8888; border-top: 1px solid #FF4B4B;">Anemic offense all year.</div></div></div>""", unsafe_allow_html=True)
        blowout = awards['Blowout']
        with t_col2:
            st.markdown(f"""<div class="luxury-card shame-card" style="text-align: center;"><div style="color: #FF4B4B; font-weight: bold;">💥 BIGGEST BLOWOUT VICTIM</div><div style="font-size: 1.5rem; font-weight: 900; color: white; margin: 10px 0;">{blowout['Loser']}</div><div style="color: #aaa;">Destroyed by {blowout['Winner']} (+{blowout['Margin']:.1f} pts)</div><div class="award-blurb" style="color: #FF8888; border-top: 1px solid #FF4B4B;">A historic beatdown.</div></div>""", unsafe_allow_html=True)

elif selected_page == P_VAULT:
    st.header("⏳ The Dynasty Vault (All-Time History)")
    st.caption(f"Tracking league history from {START_YEAR} to Present.")
    if "dynasty_leaderboard" not in st.session_state:
        if st.button("🔓 Unlock The Vault"):
            with luxury_spinner(f"Traveling back to {START_YEAR}..."):
                df_raw = get_dynasty_data(year, START_YEAR)
                st.session_state["dynasty_raw"] = df_raw
                st.session_state["dynasty_leaderboard"] = process_dynasty_leaderboard(df_raw)
                st.rerun()
    else:
        st.subheader("🏛️ All-Time Leaderboard")
        df_lead = st.session_state["dynasty_leaderboard"]
        st.dataframe(df_lead, use_container_width=True, hide_index=True, column_config={"Manager": st.column_config.TextColumn("Manager", width="medium"), "Win %": st.column_config.ProgressColumn("Win %", format="%.1f%%", min_value=0, max_value=100), "Champ": st.column_config.NumberColumn("🏆 Rings"), "Playoffs": st.column_config.NumberColumn("🎟️ Playoff Apps"), "Points For": st.column_config.NumberColumn("Total Pts", format="%.0f")})
        st.subheader("📉 Empire History")
        df_chart = st.session_state["dynasty_raw"]
        fig = px.line(df_chart, x="Year", y="Wins", color="Manager", markers=True, title="The Rise and Fall of Empires")
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aaba", xaxis=dict(tickmode='linear', tick0=START_YEAR, dtick=1))
        st.plotly_chart(fig, use_container_width=True)
else:
    st.error(f"Page Not Found: {selected_page}. Please check page definitions.")
