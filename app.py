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
current_week = league.current_week - 1
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
    
    matchup_data.append({"Home": home.team_name, "Home Score": game.home_score, "Home Logo": utils.get_logo(home), "Home Roster": h_r, "Away": away.team_name, "Away Score": game.away_score, "Away Logo": utils.get_logo(away), "Away Roster": a_r})
    efficiency_data.append({"Team": home.team_name, "Starters": h_s, "Bench": h_b, "Total Potential": h_s + h_b})
    efficiency_data.append({"Team": away.team_name, "Starters": a_s, "Bench": a_b, "Total Potential": a_s + a_b})

df_eff = pd.DataFrame(efficiency_data).sort_values(by="Total Potential", ascending=False)
df_players = pd.DataFrame(all_active_players).sort_values(by="Points", ascending=False).head(5)
df_bench_stars = pd.DataFrame(bench_highlights).sort_values(by="Score", ascending=False).head(5)

# ------------------------------------------------------------------
# 5. DASHBOARD UI ROUTER
# ------------------------------------------------------------------
st.title(f"🏛️ Luxury League Protocol: Week {selected_week}")

# HERO ROW (Mobile-Optimized Horizontal Scroll)
st.markdown("### 🌟 Weekly Elite")

# Prepare data for the HTML block
top_3 = df_players.head(3).reset_index(drop=True)

# Create a single horizontal container string
hero_html = '<div style="display: flex; gap: 15px; overflow-x: auto; padding-bottom: 10px;">'
for i, p in top_3.iterrows():
    hero_html += f"""
    <div class="luxury-card" style="min-width: 280px; flex: 0 0 auto; padding: 15px; display: flex; align-items: center;">
        <img src="https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{p['ID']}.png&w=80&h=60" 
             style="border-radius: 8px; margin-right: 15px; border: 1px solid rgba(0, 201, 255, 0.5);">
        <div>
            <div style="color: #ffffff; font-weight: 800; font-size: 16px;">{p['Name']}</div>
            <div style="color: #00C9FF; font-size: 14px; font-weight: 600;">{p['Points']} PTS</div>
            <div style="color: #a0aaba; font-size: 11px;">{p['Team']}</div>
        </div>
    </div>
    """
hero_html += '</div>'

# Render the custom HTML block
st.markdown(hero_html, unsafe_allow_html=True)
st.markdown("---")
