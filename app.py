# ------------------------------------------------------------------
# 6. AI HELPERS (MULTI-MODAL LONG FORM)
# ------------------------------------------------------------------
def get_openai_client():
    if not openai_key: return None
    return OpenAI(api_key=openai_key)

def get_weekly_recap():
    client = get_openai_client()
    if not client: return "⚠️ Add 'openai_key' to secrets."
    top_scorer = df_eff.iloc[0]['Team']
    prompt = f"Write a DETAILED, 5-10 sentence fantasy recap for Week {selected_week}. Highlight Powerhouse: {top_scorer}. Go into detail about the matchups. Style: Wall Street Report. Do not be brief."
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=800).choices[0].message.content
    except: return "Analyst Offline."

def get_rankings_commentary():
    client = get_openai_client()
    if not client: return "⚠️ Analyst Offline."
    top = df_eff.iloc[0]['Team']
    bottom = df_eff.iloc[-1]['Team']
    prompt = f"Write a 5-8 sentence commentary on the Power Rankings. Praise the #1 team {top} and ruthlessly mock the last place team {bottom}. Analyze why the bottom team is failing. Style: Stephen A. Smith / Hot Take."
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=600).choices[0].message.content
    except: return "Analyst Offline."

def get_next_week_preview(games_list):
    client = get_openai_client()
    if not client: return "⚠️ Analyst Offline."
    matchups_str = ", ".join([f"{g['home']} vs {g['away']} (Spread: {g['spread']})" for g in games_list])
    prompt = f"Act as a Vegas Sports Bookie. Provide a DETAILED breakdown (5-10 sentences) of next week's matchups: {matchups_str}. Pick one 'Lock of the Week' and one 'Upset Alert' and explain WHY with data."
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=800).choices[0].message.content
    except: return "Analyst Offline."

def get_season_retrospective(mvp, best_mgr):
    client = get_openai_client()
    if not client: return "⚠️ Analyst Offline."
    prompt = f"Write a comprehensive 'State of the Union' address (8-12 sentences) for the Fantasy League. MVP is {mvp}. Best Manager is {best_mgr}. Reflect on the season's glory, the tragedies, and the future. Style: Presidential / Epic."
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=1000).choices[0].message.content
    except: return "Analyst Offline."

def get_ai_trade_proposal(team_a, team_b, roster_a, roster_b):
    client = get_openai_client()
    if not client: return "⚠️ Analyst Offline."
    prompt = f"""
    Act as a high-stakes Trade Broker. Analyze these two rosters and propose a fair, win-win trade.
    
    Team A ({team_a}): {', '.join(roster_a)}
    Team B ({team_b}): {', '.join(roster_b)}
    
    Identify surplus/needs for both. Suggest a specific player-for-player swap. Explain the 'Why' for both sides.
    Style: Jerry Maguire / Wolf of Wall Street.
    """
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=600).choices[0].message.content
    except: return "Analyst Offline."

def get_ai_scouting_report(free_agents_str):
    client = get_openai_client()
    if not client: return "⚠️ Analyst Offline."
    prompt = f"""
    You are an elite NFL Talent Scout. Here is a list of available free agents (The Dark Pool):
    {free_agents_str}
    
    Identify 3 "Must Add" players.
    For each, provide a 1-sentence "Scouting Report" on why they are a hidden gem (e.g. recent volume, injury opportunity).
    Style: Scouting Notebook (Gritty, technical).
    """
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=500).choices[0].message.content
    except: return "Analyst Offline."

# ------------------------------------------------------------------
# 7. DASHBOARD UI
# ------------------------------------------------------------------
st.title(f"🏛️ Luxury League Protocol: Week {selected_week}")

# --- HORIZONTAL HERO ROW (Weekly Elite) ---
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

# PAGE ROUTING
if selected_page == P_LEDGER:
    if "recap" not in st.session_state:
        with luxury_spinner("Analyst is reviewing portfolios..."): 
            st.session_state["recap"] = get_weekly_recap()
    
    st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ The Studio Report</h3>{st.session_state["recap"]}</div>', unsafe_allow_html=True)
    st.header("Weekly Transactions")
    
    m_col1, m_col2 = st.columns(2)
    for i, m in enumerate(matchup_data):
        current_col = m_col1 if i % 2 == 0 else m_col2
        with current_col:
            st.markdown(f"""
            <div class="luxury-card" style="padding: 15px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="text-align: center; width: 40%;">
                        <img src="{m['Home Logo']}" width="50" style="border-radius: 50%; border: 2px solid #00C9FF; padding: 2px; box-shadow: 0 0 15px rgba(0, 201, 255, 0.4);">
                        <div style="font-weight: 700; color: white; font-size: 0.9em; margin-top: 5px;">{m['Home']}</div>
                        <div style="font-size: 20px; color: #00C9FF; font-weight: 800;">{m['Home Score']}</div>
                    </div>
                    <div style="color: #a0aaba; font-size: 10px; font-weight: bold;">VS</div>
                    <div style="text-align: center; width: 40%;">
                        <img src="{m['Away Logo']}" width="50" style="border-radius: 50%; border: 2px solid #0072ff; padding: 2px; box-shadow: 0 0 15px rgba(146, 254, 157, 0.4);">
                        <div style="font-weight: 700; color: white; font-size: 0.9em; margin-top: 5px;">{m['Away']}</div>
                        <div style="font-size: 20px; color: #00C9FF; font-weight: 800;">{m['Away Score']}</div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)
            
            with st.expander(f"📉 View Lineups"):
                max_len = max(len(m['Home Roster']), len(m['Away Roster']))
                df_matchup = pd.DataFrame({
                    f"{m['Home']}": [p['Name'] for p in m['Home Roster']] + [''] * (max_len - len(m['Home Roster'])),
                    f"{m['Home']} Pts": [p['Score'] for p in m['Home Roster']] + [0] * (max_len - len(m['Home Roster'])),
                    "Pos": [p['Pos'] for p in m['Home Roster']] + [''] * (max_len - len(m['Home Roster'])),
                    f"{m['Away']} Pts": [p['Score'] for p in m['Away Roster']] + [0] * (max_len - len(m['Away Roster'])),
                    f"{m['Away']}": [p['Name'] for p in m['Away Roster']] + [''] * (max_len - len(m['Away Roster'])),
                })
                st.dataframe(df_matchup, use_container_width=True, hide_index=True, column_config={f"{m['Home']} Pts": st.column_config.NumberColumn(format="%.1f"), f"{m['Away']} Pts": st.column_config.NumberColumn(format="%.1f")})

elif selected_page == P_HIERARCHY:
    if "rank_comm" not in st.session_state:
        with luxury_spinner("Analyzing hierarchy..."): st.session_state["rank_comm"] = get_rankings_commentary()
    
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
            with luxury_spinner("Compiling Assets..."): st.session_state["df_advanced"] = calculate_heavy_analytics(current_week); st.rerun()
    else:
        df_advanced = st.session_state["df_advanced"]
        fig = px.scatter(df_advanced, x="Power Score", y="Wins", text="Team", size="Points For", color="Luck Rating", color_continuous_scale=["#7209b7", "#4361ee", "#4cc9f0"], title="Luck Matrix", height=600)
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="#a0aaba")
        fig.update_traces(marker=dict(size=15, line=dict(width=2, color='White')), textposition='top center')
        st.plotly_chart(fig, use_container_width=True)

elif selected_page == P_LAB:
    st.header("🧬 The Lab (Next Gen Biometrics)")
    with st.expander("🔎 Biometric Legend (The Code)", expanded=False):
        st.markdown("""
        - 💎 **ELITE:** Top 10% performance in underlying metric (Separation/Efficiency).
        - 🚀 **MONSTER:** Incredible efficiency (YAC > Expected).
        - 🎯 **SNIPER:** Completion % > Expected (Highly Accurate).
        - ⚠️ **TRAP:** High Volume but Low Efficiency (Sell High Candidate).
        - 🚫 **PLODDER:** Inefficient rushing (Rushing Yards < Expected).
        - **Separation:** Yards of distance from nearest defender at catch.
        - **CPOE:** Completion Percentage Over Expectation.
        - **RYOE:** Rushing Yards Over Expectation (Line adjusted).
        - **WOPR:** Weighted Opportunity Rating (Target Share + Air Yards Share).
        """)
    
    team_list = [t.team_name for t in league.teams]
    target_team = st.selectbox("Select Test Subject:", team_list)
    
    if st.button("🧪 Analyze Roster Efficiency"):
        if lottie_lab: st_lottie(lottie_lab, height=200)
        with luxury_spinner("Calibrating Tracking Satellites..."):
            roster_obj = next(t for t in league.teams if t.team_name == target_team).roster
            df_ngs = analyze_nextgen_metrics(roster_obj, year)
            st.session_state["ngs_data"] = df_ngs
            st.rerun()
            
    if "ngs_data" in st.session_state and not st.session_state["ngs_data"].empty:
        st.markdown("### 🔬 Biometric Results")
        df_res = st.session_state["ngs_data"]
        cols = st.columns(2)
        for i, row in df_res.iterrows():
            col = cols[i % 2]
            with col:
                st.markdown(f"""
                <div class="luxury-card" style="border-left: 4px solid #00C9FF; display: flex; align-items: center;">
                    <img src="https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{row['ID']}.png&w=80&h=60" 
                         style="border-radius: 8px; margin-right: 15px; border: 1px solid rgba(0, 201, 255, 0.3);">
                    <div style="flex: 1;">
                        <h4 style="margin:0; color: white; font-size: 1.1em;">{row['Player']}</h4>
                        <div style="font-size: 0.8em; color: #a0aaba;">{row['Team']} • {row['Position']}</div>
                        <div style="color: #00C9FF; font-weight: bold; font-size: 0.9em; margin-top: 4px;">{row['Verdict']}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 0.75em; color: #a0aaba;">{row['Metric']}</div>
                        <div style="font-size: 1.4em; font-weight: bold; color: white;">{row['Value']}</div>
                        <div style="font-size: 0.75em; color: #92FE9D;">{row['Alpha Stat']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    elif "ngs_data" in st.session_state:
        st.info("No Next Gen Data found for this roster (or API connection failed).")

elif selected_page == P_FORECAST:
    st.header("The Crystal Ball")
    if "playoff_odds" not in st.session_state:
        if st.button("🎲 Run Simulation"):
            with luxury_spinner("Running Monte Carlo simulations..."): st.session_state["playoff_odds"] = run_monte_carlo_simulation(); st.rerun()
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
            with luxury_spinner("Checking Vegas lines..."): st.session_state["next_week_commentary"] = get_next_week_preview(games_list)
        
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
                st.markdown(f"""
                <div class="luxury-card" style="padding: 15px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; text-align: center;">
                        <div style="flex: 2;">
                            <div style="font-weight: bold; font-size: 1.1em; color: #ffffff;">{game.home_team.team_name}</div>
                            <div style="color: #00C9FF; text-shadow: 0 0 8px rgba(0, 201, 255, 0.4);">Proj: {h_proj:.1f}</div>
                        </div>
                        <div style="flex: 1; color: #a0aaba; font-size: 0.8em;">
                            <div>VS</div>
                            <div style="color: #00C9FF; margin-top: 5px;">Fav: {fav}</div>
                            <div style="color: #fff;">+{spread:.1f}</div>
                        </div>
                        <div style="flex: 2;">
                            <div style="font-weight: bold; font-size: 1.1em; color: #ffffff;">{game.away_team.team_name}</div>
                            <div style="color: #92FE9D; text-shadow: 0 0 8px rgba(146, 254, 157, 0.4);">Proj: {a_proj:.1f}</div>
                        </div>
                    </div>
                </div>""", unsafe_allow_html=True)
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
                            status = "🚀 SMASH (Vegas Higher)" if delta > 3 else "⚠️ TRAP (ESPN High)" if delta < -3 else "⚖️ Fair Value"
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
            proposal = get_ai_trade_proposal(t1, t2, r_a, r_b)
            st.markdown(f'<div class="luxury-card studio-box"><h3>Proposed Deal</h3>{proposal}</div>', unsafe_allow_html=True)

elif selected_page == P_DARK:
    st.header("🕵️ The Dark Pool (Waiver Wire)")
    st.caption("Scouting available free agents (excluding IR/OUT) for breakout potential.")
    
    has_data = "dark_pool_data" in st.session_state
    
    # BUTTONS AT TOP
    c1, c2 = st.columns([1, 4])
    with c1:
        if not has_data:
            if st.button("🔭 Scan Wire", type="primary"):
                with luxury_spinner("Scouting the wire..."):
                    df_pool = scan_dark_pool()
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
            st.caption("Scanner filtered out players based on Injury Status (OUT/IR) or Low Points.")

elif selected_page == P_TROPHY:
    if "awards" not in st.session_state:
        if st.button("🏅 Unveil Awards"):
            with luxury_spinner("Engraving trophies..."):
                st.session_state["awards"] = calculate_season_awards(current_week)
                st.session_state["season_comm"] = get_season_retrospective(st.session_state['awards']['MVP']['Name'], st.session_state['awards']['Best Manager']['Team'])
                st.rerun()
    else:
        awards = st.session_state["awards"]
        if "season_comm" in st.session_state:
             st.markdown(f'<div class="luxury-card studio-box"><h3>🎙️ State of the League</h3>{st.session_state["season_comm"]}</div>', unsafe_allow_html=True)
        st.divider(); st.header("Season Awards")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="luxury-card award-card"><h3>👑 MVP</h3></div>', unsafe_allow_html=True)
            if awards['MVP']:
                p = awards['MVP']
                st.image(f"https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{p['ID']}.png&w=350&h=254", width=150)
                st.metric(label=p['Name'], value=f"{p['Points']:.1f} pts")
        with c2:
            st.markdown('<div class="luxury-card award-card"><h3>🐋 The Whale</h3></div>', unsafe_allow_html=True)
            mgr = awards['Best Manager']
            st.image(mgr['Logo'], width=100)
            st.metric(label=mgr['Team'], value=f"{mgr['Points']:.1f} pts")
        st.divider()
        c3, c4, c5 = st.columns(3)
        with c3:
            st.markdown("#### 💔 Heartbreaker"); hb = awards['Heartbreaker']
            st.metric(label=f"{hb['Loser']} lost by", value=f"{hb['Margin']:.2f} pts")
        with c4:
            st.markdown("#### 🔥 The Streak"); stk = awards['Streak']
            st.metric(label=stk['Team'], value=f"{stk['Length']} Games")
        with c5:
            st.markdown("#### 💤 Asleep at Wheel"); slp = awards['Sleeper']
            st.metric(label=slp['Team'], value=f"{slp['Count']} Players")
            
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
