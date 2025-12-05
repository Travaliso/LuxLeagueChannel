import streamlit as st
from espn_api.football import League
import pandas as pd
import numpy as np
import requests
import nfl_data_py as nfl
from thefuzz import process
import re
import time
from contextlib import contextmanager
from openai import OpenAI

# ==============================================================================
# 1. CSS & STYLING
# ==============================================================================
def inject_luxury_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Lato:wght@400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Lato', sans-serif; color: #E0E0E0; }
    h1, h2, h3 { font-family: 'Playfair Display', serif; color: #D4AF37 !important; text-shadow: 0 2px 4px rgba(0,0,0,0.5); }
    .stApp { background-color: #060b26; background-image: radial-gradient(circle at 0% 0%, rgba(58, 12, 163, 0.4) 0%, transparent 50%), radial-gradient(circle at 100% 100%, rgba(0, 201, 255, 0.2) 0%, transparent 50%); background-attachment: fixed; background-size: cover; }
    
    .luxury-card { background: rgba(17, 25, 40, 0.75); backdrop-filter: blur(16px); border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.08); padding: 20px; margin-bottom: 15px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3); }
    
    /* BADGES */
    .prop-badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; }
    .badge-fire { background: rgba(255, 75, 75, 0.2); color: #FF4B4B; border: 1px solid #FF4B4B; }
    .badge-gem { background: rgba(0, 201, 255, 0.2); color: #00C9FF; border: 1px solid #00C9FF; }
    .badge-ok { background: rgba(146, 254, 157, 0.2); color: #92FE9D; border: 1px solid #92FE9D; }
    
    .matchup-badge { font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; margin-left: 8px; font-weight: bold; display: inline-block; }
    .matchup-good { color: #92FE9D; border: 1px solid #92FE9D; background: rgba(146, 254, 157, 0.1); }
    .matchup-bad { color: #FF4B4B; border: 1px solid #FF4B4B; background: rgba(255, 75, 75, 0.1); }
    .matchup-mid { color: #a0aaba; border: 1px solid #a0aaba; background: rgba(160, 170, 186, 0.1); }
    
    /* GRID & TEXT */
    .stat-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 5px; margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1); }
    .stat-box { text-align: center; }
    .stat-val { font-size: 1.1rem; font-weight: 700; color: white; }
    .stat-label { font-size: 0.65rem; color: #a0aaba; text-transform: uppercase; }
    
    /* TOOLTIP */
    .tooltip { position: relative; display: inline-block; cursor: pointer; }
    .tooltip .tooltiptext { visibility: hidden; width: 200px; background-color: #1E1E1E; color: #fff; text-align: center; border-radius: 6px; padding: 10px; position: absolute; z-index: 1; bottom: 125%; left: 50%; margin-left: -100px; opacity: 0; transition: opacity 0.3s; border: 1px solid #D4AF37; font-size: 0.7rem; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
    .tooltip:hover .tooltiptext { visibility: visible; opacity: 1; }

    [data-testid="stSidebarNav"] { display: block !important; visibility: visible !important; }
    header[data-testid="stHeader"] { background-color: transparent; }
    
    /* LOADER */
    @keyframes shine { to { background-position: 200% center; } }
    .luxury-loader-text { font-family: 'Helvetica Neue', sans-serif; font-size: 4rem; font-weight: 900; text-transform: uppercase; letter-spacing: 8px; background: linear-gradient(90deg, #1a1c24 0%, #00C9FF 25%, #ffffff 50%, #00C9FF 75%, #1a1c24 100%); background-size: 200% auto; -webkit-background-clip: text; background-clip: text; color: transparent; animation: shine 3s linear infinite; }
    .luxury-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(6, 11, 38, 0.92); backdrop-filter: blur(10px); z-index: 999999; display: flex; flex-direction: column; justify-content: center; align-items: center; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 2. HELPERS
# ==============================================================================
@st.cache_resource
def get_league(league_id, year, espn_s2, swid):
    return League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)

def get_logo(team):
    try: return team.logo_url if team.logo_url else "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png"
    except: return "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png"

def normalize_name(name):
    return re.sub(r'[^a-z0-9]', '', str(name).lower()).replace('iii','').replace('ii','').replace('jr','')

def clean_team_abbr(abbr):
    # Maps ESPN abbreviations to nfl_data_py/standard abbreviations
    mapping = {
        'WSH': 'WAS', 'JAX': 'JAC', 'LAR': 'LA', 'LV': 'LV', 'ARZ': 'ARI', 'HST': 'HOU', 'BLT': 'BAL', 'CLV': 'CLE'
    }
    return mapping.get(abbr, abbr)

@contextmanager
def luxury_spinner(text="Processing..."):
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(f'<div class="luxury-overlay"><div class="luxury-loader-text">LUXURY LEAGUE</div><div style="color:#00C9FF; margin-top:20px;">⚡ {text}</div></div>', unsafe_allow_html=True)
    try: yield
    finally: placeholder.empty()

# ==============================================================================
# 3. CARD RENDERERS
# ==============================================================================
def render_hero_card(col, player):
    with col:
        st.markdown(f"""<div class="luxury-card" style="padding: 15px; display: flex; align-items: center;"><img src="https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{player['ID']}.png&w=80&h=60" style="border-radius: 8px; margin-right: 15px; border: 1px solid rgba(0, 201, 255, 0.5);"><div><div style="color: white; font-weight: 800;">{player['Name']}</div><div style="color: #00C9FF; font-weight: 600;">{player['Points']} PTS</div><div style="color: #a0aaba; font-size: 0.8rem;">{player['Team']}</div></div></div>""", unsafe_allow_html=True)

def render_team_card(col, team_data, rank):
    with col:
        st.markdown(f"""<div class="luxury-card" style="border-left: 4px solid #D4AF37; display:flex; align-items:center;"><div style="font-size:2.5rem; font-weight:900; color:rgba(255,255,255,0.1); margin-right:15px; width:40px;">{rank}</div><div style="flex:1;"><div style="font-size:1.2rem; font-weight:bold; color:white;">{team_data['Team']}</div><div style="font-size:0.8rem; color:#a0aaba;">Power Score: <span style="color:#00C9FF;">{team_data['Power Score']}</span></div></div><div style="text-align:right;"><div style="font-size:1.2rem; font-weight:bold; color:white;">{team_data['Wins']}W</div><div style="font-size:0.7rem; color:#a0aaba;">Luck: {team_data['Luck Rating']:.1f}</div></div></div>""", unsafe_allow_html=True)

def render_prop_card(col, row):
    v = row['Verdict']
    badge_class = "badge-fire" if "Must" in v or "Elite" in v else "badge-gem" if "1" in v else "badge-ok"
    pid = row.get('ESPN ID', 0)
    headshot = f"https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{pid}.png&w=100&h=100" if pid else "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png&w=100&h=100"
    
    main_stat = "Rec Yds"
    line_val = row.get('Rec Yds', 0)
    if row.get('Pass Yds', 0) > 0: main_stat, line_val = "Pass Yds", row['Pass Yds']
    elif row.get('Rush Yds', 0) > 0: main_stat, line_val = "Rush Yds", row['Rush Yds']
    
    edge_val = row.get('Edge', 0.0)
    edge_color = "#00C9FF" if edge_val > 0 else "#FF4B4B"
    edge_arrow = "▲" if edge_val > 0 else "▼"
    
    hit_rate_str = row.get('Hit Rate', 'N/A')
    hit_color = "#E0E0E0"
    if "100%" in str(hit_rate_str): hit_color = "#00C9FF"
    elif "0%" in str(hit_rate_str): hit_color = "#FF4B4B"
    
    matchup_html = ""
    if "vs #" in str(row.get('Matchup Rank', '')):
        try:
            rank = int(re.search(r'#(\d+)', row['Matchup Rank']).group(1))
            m_class = "matchup-good" if rank >= 24 else "matchup-bad" if rank <= 8 else "matchup-mid"
            matchup_html = f'<div class="matchup-badge {m_class}">{row["Matchup Rank"]}</div>'
        except: pass

    html = f"""<div class="luxury-card"><div style="display:flex; justify-content:space-between; align-items:start;"><div style="flex:1;"><div style="display:flex; align-items:center; margin-bottom:10px;"><div class="prop-badge {badge_class}">{v}</div>{matchup_html}</div><div style="font-size:1.3rem; font-weight:900; color:white; line-height:1.2; margin-bottom:5px;">{row['Player']}</div><div style="color:#a0aaba; font-size:0.8rem;">{row.get('Position', 'FLEX')} | {row.get('Team', 'FA')}</div></div><img src="{headshot}" style="width:70px; height:70px; border-radius:50%; border:2px solid {edge_color}; object-fit:cover; background:#000;"></div><div style="margin-top:10px; background:rgba(0,0,0,0.3); padding:8px; border-radius:8px; text-align:center; font-size:0.8rem; border:1px solid {edge_color}; color:{edge_color};"><span style="margin-right:5px;">{edge_arrow} {abs(edge_val):.1f} pts vs ESPN</span><div class="tooltip">ℹ️<span class="tooltiptext"><b>The Edge:</b><br>Blue = Vegas Higher<br>Red = Vegas Lower</span></div></div><div class="stat-grid"><div class="stat-box"><div class="stat-val" style="color:#D4AF37;">{row['Proj Pts']:.1f}</div><div class="stat-label">Vegas Pts</div></div><div class="stat-box"><div class="stat-val" style="color:#fff;">{line_val:.0f}</div><div class="stat-label">{main_stat} Line</div></div><div class="stat-box"><div class="stat-val" style="color:{hit_color};">{hit_rate_str}</div><div class="stat-label">L5 Hit Rate</div></div></div></div>"""
    
    with col: st.markdown(html, unsafe_allow_html=True)

# ==============================================================================
# 3. ANALYTICS CORE
# ==============================================================================
@st.cache_data(ttl=3600*24)
def load_nfl_stats_safe(year):
    for y in [year, year-1]:
        try:
            df = nfl.import_weekly_data([y])
            if not df.empty:
                df['norm_name'] = df['player_display_name'].apply(normalize_name)
                return df
        except: continue
    return pd.DataFrame()

@st.cache_data(ttl=3600*24)
def get_dvp_ranks_safe(year):
    try:
        df = load_nfl_stats_safe(year)
        if df.empty: return {}
        df = df[df['position'].isin(['QB', 'RB', 'WR', 'TE'])]
        # Sum fantasy points allowed by opponent
        dvp = df.groupby(['opponent_team', 'position'])['fantasy_points_ppr'].sum().reset_index()
        # Rank descending (most points allowed = rank 1 = best matchup)
        dvp['rank'] = dvp.groupby('position')['fantasy_points_ppr'].rank(ascending=False)
        
        dvp_map = {}
        for _, row in dvp.iterrows():
            # Map nfl_data_py team abbreviations to standardized ones if needed
            team = clean_team_abbr(row['opponent_team'])
            if team not in dvp_map: dvp_map[team] = {}
            dvp_map[team][row['position']] = int(row['rank'])
        return dvp_map
    except: return {}

@st.cache_data(ttl=3600)
def get_vegas_props(api_key, _league, week):
    # 1. LOAD CONTEXT
    current_year = _league.year
    stats_df = load_nfl_stats_safe(current_year) 
    dvp_map = get_dvp_ranks_safe(current_year)
    
    # 2. BUILD ESPN ROSTER MAP (ROBUST METHOD)
    # Start with ALL rostered players from teams
    espn_map = {}
    
    for team in _league.teams:
        for p in team.roster:
            norm = normalize_name(p.name)
            # Default projection to 0 if not found yet
            espn_map[norm] = {
                "name": p.name, "id": p.playerId, "pos": p.position, 
                "team": team.team_name, "proTeam": p.proTeam, "opponent": "UNK",
                "espn_proj": 0 
            }

    # 2b. ENRICH WITH WEEKLY BOX SCORE DATA (Projections & Opponents)
    box_scores = _league.box_scores(week=week)
    for game in box_scores:
        # Extract opponents
        h_opp = game.away_team.team_abbrev if hasattr(game.away_team, 'team_abbrev') else "UNK"
        a_opp = game.home_team.team_abbrev if hasattr(game.home_team, 'team_abbrev') else "UNK"
        
        # Update Home Players
        for p in game.home_lineup:
            norm = normalize_name(p.name)
            if norm in espn_map:
                espn_map[norm]['espn_proj'] = p.projected_points
                espn_map[norm]['opponent'] = clean_team_abbr(h_opp)
        
        # Update Away Players
        for p in game.away_lineup:
            norm = normalize_name(p.name)
            if norm in espn_map:
                espn_map[norm]['espn_proj'] = p.projected_points
                espn_map[norm]['opponent'] = clean_team_abbr(a_opp)

    # 2c. ADD FREE AGENTS
    try:
        for p in _league.free_agents(size=500):
            norm = normalize_name(p.name)
            if norm not in espn_map:
                # FAs usually don't have weekly proj in this call, but we need them in the map for Vegas match
                espn_map[norm] = {
                    "name": p.name, "id": p.playerId, "pos": p.position, 
                    "team": "Free Agent", "proTeam": p.proTeam, "opponent": "UNK",
                    "espn_proj": getattr(p, 'projected_points', 0)
                }
    except: pass

    # 3. FETCH VEGAS
    url = 'https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds'
    params = {'api_key': api_key, 'regions': 'us', 'markets': 'h2h', 'oddsFormat': 'american'}
    try:
        res = requests.get(url, params=params)
        if res.status_code != 200: return pd.DataFrame({"Status": [f"API Error {res.status_code}"]})
        games = res.json()
        if not games: return pd.DataFrame({"Status": ["No Games Found"]})
        
        player_props = {}
        for game in games[:16]:
            g_url = f"https://api.the-odds-api.com/v4/sports/americanfootball_nfl/events/{game['id']}/odds"
            g_params = {'api_key': api_key, 'regions': 'us', 'markets': 'player_pass_yds,player_rush_yds,player_reception_yds,player_anytime_td', 'oddsFormat': 'american'}
            g_res = requests.get(g_url, params=g_params)
            if g_res.status_code == 200:
                g_data = g_res.json()
                for bm in g_data.get('bookmakers', []):
                    for mkt in bm['markets']:
                        key = mkt['key']
                        for out in mkt['outcomes']:
                            name = out['description']
                            if name not in player_props: player_props[name] = {'pass':0, 'rush':0, 'rec':0, 'td':0}
                            if key == 'player_pass_yds': player_props[name]['pass'] = out.get('point', 0)
                            elif key == 'player_rush_yds': player_props[name]['rush'] = out.get('point', 0)
                            elif key == 'player_reception_yds': player_props[name]['rec'] = out.get('point', 0)
                            elif key == 'player_anytime_td':
                                odds = out.get('price', 0)
                                player_props[name]['td'] = 100/(odds+100) if odds > 0 else abs(odds)/(abs(odds)+100)
            time.sleep(0.05)

        # 4. MERGE
        rows = []
        espn_keys = list(espn_map.keys())
        
        for name, s in player_props.items():
            norm = normalize_name(name)
            match = espn_map.get(norm)
            if not match:
                best = process.extractOne(norm, espn_keys)
                if best and best[1] > 80: match = espn_map[best[0]]
            
            if match:
                # Calculations
                score = (s['pass']*0.04) + (s['rush']*0.1) + (s['rec']*0.1) + (s['td']*6)
                
                # Lowered threshold to catch more players
                if score > 1.0:
                    # Verdict
                    v = "⚠️ Risky"
                    p_pos = match['pos']
                    if p_pos == 'QB': v = "🔥 Elite QB1" if score >= 20 else "💎 QB1" if score >= 16 else "🆗 Streamer"
                    else: v = "🔥 Must Start" if score >= 15 else "💎 RB1/WR1" if score >= 12 else "🆗 Flex Play"
                    
                    # Hit Rate
                    hr_txt = "N/A"
                    if not stats_df.empty:
                        p_stats = stats_df[stats_df['norm_name'] == norm]
                        if not p_stats.empty:
                            l5 = p_stats.sort_values(by='week', ascending=False).head(5)
                            if len(l5) > 0:
                                hits = 0
                                if s['pass']>0: hits = sum(l5['passing_yards'] >= s['pass'])
                                elif s['rush']>0: hits = sum(l5['rushing_yards'] >= s['rush'])
                                elif s['rec']>0: hits = sum(l5['receiving_yards'] >= s['rec'])
                                hr_txt = f"{int((hits/len(l5))*100)}%"

                    # DvP
                    dvp_txt = ""
                    opp = clean_team_abbr(match.get('opponent', 'UNK'))
                    if opp in dvp_map and p_pos in dvp_map[opp]:
                        dvp_txt = f"vs #{dvp_map[opp][p_pos]} {p_pos} Def"

                    rows.append({
                        "Player": match['name'], "Position": p_pos, "Team": match['team'],
                        "ESPN ID": match['id'], "Proj Pts": score, "Edge": score - match['espn_proj'],
                        "Verdict": v, "Hit Rate": hr_txt, "Matchup Rank": dvp_txt,
                        "Pass Yds": s['pass'], "Rush Yds": s['rush'], "Rec Yds": s['rec'], "TD %": s['td']
                    })
        
        if not rows: return pd.DataFrame({"Status": ["No Matching Props Found"]})
        return pd.DataFrame(rows).sort_values(by="Proj Pts", ascending=False)

    except Exception as e:
        return pd.DataFrame({"Status": [f"System Error: {str(e)}"]})

# ---------------------------------------------------------
# OTHER ANALYTICS
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def calculate_heavy_analytics(_league, current_week):
    data_rows = []
    for team in _league.teams:
        power_score = round(team.points_for / current_week, 1)
        true_wins, total_matchups = 0, 0
        for w in range(1, current_week + 1):
            box = _league.box_scores(week=w)
            my_score = next((g.home_score if g.home_team == team else g.away_score for g in box if g.home_team == team or g.away_team == team), 0)
            all_scores = [g.home_score for g in box] + [g.away_score for g in box]
            wins_this_week = sum(1 for s in all_scores if my_score > s)
            true_wins += wins_this_week
            total_matchups += (len(_league.teams) - 1)
        true_win_pct = true_wins / total_matchups if total_matchups > 0 else 0
        actual_win_pct = team.wins / (team.wins + team.losses + 0.001)
        luck_rating = (actual_win_pct - true_win_pct) * 10
        data_rows.append({"Team": team.team_name, "Wins": team.wins, "Points For": team.points_for, "Power Score": power_score, "Luck Rating": luck_rating})
    return pd.DataFrame(data_rows).sort_values(by="Power Score", ascending=False)

@st.cache_data(ttl=3600)
def calculate_season_awards(_league, current_week):
    # Simplified for stability
    return {"MVP": None, "Podium": [], "Oracle": {"Team": "N/A", "Eff": 0, "Logo": ""}, "Sniper": {"Team": "N/A", "Pts": 0, "Logo": ""}, "Purple": {"Team": "N/A", "Count": 0, "Logo": ""}, "Hoarder": {"Team": "N/A", "Pts": 0, "Logo": ""}, "Toilet": {"Team": "N/A", "Pts": 0, "Logo": ""}, "Blowout": {"Winner": "N/A", "Loser": "N/A", "Margin": 0}, "Best Manager": {"Team": "N/A", "Points": 0, "Logo": ""}}

# Stub functions to prevent import errors
def get_ai_scouting_report(key, free_agents_str): return "Analyst Offline"
def get_weekly_recap(key, selected_week, top_team): return "Analyst Offline"
def get_rankings_commentary(key, top_team, bottom_team): return "Analyst Offline"
def get_next_week_preview(key, games_list): return "Analyst Offline"
def get_season_retrospective(key, mvp, best_mgr): return "Analyst Offline"
def get_ai_trade_proposal(key, team_a, team_b, roster_a, roster_b): return "Analyst Offline"
def scan_dark_pool(_league): return pd.DataFrame()
def calculate_draft_analysis(_league): return pd.DataFrame(), None
def get_dynasty_data(league_id, espn_s2, swid, current_year, start_year): return pd.DataFrame()
def process_dynasty_leaderboard(df): return pd.DataFrame()
def run_monte_carlo_simulation(_league): return pd.DataFrame()
def run_multiverse_simulation(_league, forced): return pd.DataFrame()
def analyze_nextgen_metrics_v3(roster, year): return pd.DataFrame()
