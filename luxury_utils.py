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
    
    .prop-badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; }
    .badge-fire { background: rgba(255, 75, 75, 0.2); color: #FF4B4B; border: 1px solid #FF4B4B; }
    .badge-gem { background: rgba(0, 201, 255, 0.2); color: #00C9FF; border: 1px solid #00C9FF; }
    .badge-ok { background: rgba(146, 254, 157, 0.2); color: #92FE9D; border: 1px solid #92FE9D; }
    
    .matchup-badge { font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; margin-left: 8px; font-weight: bold; display: inline-block; }
    .matchup-good { color: #92FE9D; border: 1px solid #92FE9D; background: rgba(146, 254, 157, 0.1); }
    .matchup-bad { color: #FF4B4B; border: 1px solid #FF4B4B; background: rgba(255, 75, 75, 0.1); }
    .matchup-mid { color: #a0aaba; border: 1px solid #a0aaba; background: rgba(160, 170, 186, 0.1); }
    
    .stat-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 5px; margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1); }
    .stat-box { text-align: center; }
    .stat-val { font-size: 1.1rem; font-weight: 700; color: white; }
    .stat-label { font-size: 0.65rem; color: #a0aaba; text-transform: uppercase; }
    
    .edge-box { margin-top: 10px; background: rgba(0,0,0,0.3); padding: 8px; border-radius: 8px; text-align: center; font-size: 0.8rem; }
    
    .tooltip { position: relative; display: inline-block; cursor: pointer; }
    .tooltip .tooltiptext { visibility: hidden; width: 200px; background-color: #1E1E1E; color: #fff; text-align: center; border-radius: 6px; padding: 10px; position: absolute; z-index: 1; bottom: 125%; left: 50%; margin-left: -100px; opacity: 0; transition: opacity 0.3s; border: 1px solid #D4AF37; font-size: 0.7rem; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
    .tooltip:hover .tooltiptext { visibility: visible; opacity: 1; }

    [data-testid="stSidebarNav"] { display: block !important; visibility: visible !important; }
    header[data-testid="stHeader"] { background-color: transparent; }
    
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
    mapping = {'WSH': 'WAS', 'JAX': 'JAC', 'LAR': 'LA', 'LV': 'LV', 'ARZ': 'ARI', 'HST': 'HOU', 'BLT': 'BAL', 'CLV': 'CLE', 'SL': 'STL'}
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
            m_class = "matchup-good" if rank <= 8 else "matchup-bad" if rank >= 24 else "matchup-mid"
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
        dvp = df.groupby(['opponent_team', 'position'])['fantasy_points_ppr'].sum().reset_index()
        dvp['rank'] = dvp.groupby('position')['fantasy_points_ppr'].rank(ascending=False)
        dvp_map = {}
        for _, row in dvp.iterrows():
            team = clean_team_abbr(row['opponent_team'])
            if team not in dvp_map: dvp_map[team] = {}
            dvp_map[team][row['position']] = int(row['rank'])
        return dvp_map
    except: return {}

@st.cache_data(ttl=3600)
def get_vegas_props(api_key, _league, week):
    current_year = _league.year
    stats_df = load_nfl_stats_safe(current_year) 
    dvp_map = get_dvp_ranks_safe(current_year)
    
    espn_map = {}
    for team in _league.teams:
        for p in team.roster:
            norm = normalize_name(p.name)
            espn_map[norm] = {"name": p.name, "id": p.playerId, "pos": p.position, "team": team.team_name, "proTeam": p.proTeam, "opponent": "UNK", "espn_proj": 0}

    box_scores = _league.box_scores(week=week)
    for game in box_scores:
        h_opp = game.away_team.team_abbrev if hasattr(game.away_team, 'team_abbrev') else "UNK"
        a_opp = game.home_team.team_abbrev if hasattr(game.home_team, 'team_abbrev') else "UNK"
        for p in game.home_lineup:
            norm = normalize_name(p.name)
            if norm in espn_map:
                espn_map[norm]['espn_proj'] = p.projected_points
                espn_map[norm]['opponent'] = clean_team_abbr(h_opp)
        for p in game.away_lineup:
            norm = normalize_name(p.name)
            if norm in espn_map:
                espn_map[norm]['espn_proj'] = p.projected_points
                espn_map[norm]['opponent'] = clean_team_abbr(a_opp)

    try:
        for p in _league.free_agents(size=500):
            norm = normalize_name(p.name)
            if norm not in espn_map:
                espn_map[norm] = {"name": p.name, "id": p.playerId, "pos": p.position, "team": "Free Agent", "proTeam": p.proTeam, "opponent": "UNK", "espn_proj": getattr(p, 'projected_points', 0)}
    except: pass

    # --- FIX 401: USE 'apiKey' NOT 'api_key' ---
    url = 'https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds'
    params = {'apiKey': api_key, 'regions': 'us', 'markets': 'h2h', 'oddsFormat': 'american'}
    try:
        res = requests.get(url, params=params)
        if res.status_code != 200: return pd.DataFrame({"Status": [f"API Error {res.status_code}"]})
        games = res.json()
        
        player_props = {}
        for game in games[:16]:
            g_url = f"https://api.the-odds-api.com/v4/sports/americanfootball_nfl/events/{game['id']}/odds"
            g_params = {'apiKey': api_key, 'regions': 'us', 'markets': 'player_pass_yds,player_rush_yds,player_reception_yds,player_anytime_td', 'oddsFormat': 'american'}
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

        rows = []
        espn_keys = list(espn_map.keys())
        for name, s in player_props.items():
            norm = normalize_name(name)
            match = espn_map.get(norm)
            if not match:
                best = process.extractOne(norm, espn_keys)
                if best and best[1] > 80: match = espn_map[best[0]]
            
            if match:
                score = (s['pass']*0.04) + (s['rush']*0.1) + (s['rec']*0.1) + (s['td']*6)
                if score > 1.0:
                    v = "⚠️ Risky"
                    p_pos = match['pos']
                    if p_pos == 'QB': v = "🔥 Elite QB1" if score >= 20 else "💎 QB1" if score >= 16 else "🆗 Streamer"
                    else: v = "🔥 Must Start" if score >= 15 else "💎 RB1/WR1" if score >= 12 else "🆗 Flex Play"
                    
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

                    dvp_txt = ""
                    opp = match.get('opponent', 'UNK')
                    if opp in dvp_map and p_pos in dvp_map[opp]:
                        rank = dvp_map[opp][p_pos]
                        dvp_txt = f"vs #{rank} {p_pos} Def"

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
# RESTORED ANALYSIS FUNCTIONS
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
        data_rows.append({"Team": team.team_name, "Wins": team.wins, "Points For": team.points_for, "Power Score": power_score, "Luck Rating": luck_rating, "True Win %": true_win_pct})
    return pd.DataFrame(data_rows).sort_values(by="Power Score", ascending=False)

@st.cache_data(ttl=3600)
def calculate_season_awards(_league, current_week):
    # Restored Award Logic
    player_points = {}
    team_stats = {t.team_name: {"Bench": 0, "Starters": 0, "WaiverPts": 0, "Injuries": 0, "Logo": get_logo(t)} for t in _league.teams}
    single_game_high = {"Team": "", "Score": 0, "Week": 0}
    biggest_blowout = {"Winner": "", "Loser": "", "Margin": 0, "Week": 0}
    heartbreaker = {"Winner": "", "Loser": "", "Margin": 999, "Week": 0}
    
    for w in range(1, current_week + 1):
        box = _league.box_scores(week=w)
        for game in box:
            margin = abs(game.home_score - game.away_score)
            winner = game.home_team.team_name if game.home_score > game.away_score else game.away_team.team_name
            loser = game.away_team.team_name if game.home_score > game.away_score else game.home_team.team_name
            
            if margin > biggest_blowout["Margin"]: biggest_blowout = {"Winner": winner, "Loser": loser, "Margin": margin, "Week": w}
            if margin < heartbreaker["Margin"]: heartbreaker = {"Winner": winner, "Loser": loser, "Margin": margin, "Week": w}
            if game.home_score > single_game_high["Score"]: single_game_high = {"Team": game.home_team.team_name, "Score": game.home_score, "Week": w}
            if game.away_score > single_game_high["Score"]: single_game_high = {"Team": game.away_team.team_name, "Score": game.away_score, "Week": w}
            
            def process(lineup, team_name):
                for p in lineup:
                    if p.playerId not in player_points: player_points[p.playerId] = {"Name": p.name, "Points": 0, "Owner": team_name, "ID": p.playerId}
                    player_points[p.playerId]["Points"] += p.points
                    if p.slot_position == 'BE': team_stats[team_name]["Bench"] += p.points
                    else: team_stats[team_name]["Starters"] += p.points
                    status = getattr(p, 'injuryStatus', 'ACTIVE')
                    if str(status).upper() in ['OUT', 'IR', 'RESERVE', 'SUSPENDED']: team_stats[team_name]["Injuries"] += 1
                    acq = getattr(p, 'acquisitionType', 'DRAFT')
                    if acq == 'ADD': team_stats[team_name]["WaiverPts"] += p.points

            process(game.home_lineup, game.home_team.team_name)
            process(game.away_lineup, game.away_team.team_name)

    sorted_players = sorted(player_points.values(), key=lambda x: x['Points'], reverse=True)
    oracle_list = []
    for t, s in team_stats.items():
        total = s["Starters"] + s["Bench"]
        eff = (s["Starters"] / total * 100) if total > 0 else 0
        oracle_list.append({"Team": t, "Eff": eff, "Logo": s["Logo"]})
    
    oracle = sorted(oracle_list, key=lambda x: x['Eff'], reverse=True)[0]
    sniper = sorted([{"Team": t, "Pts": s["WaiverPts"], "Logo": s["Logo"]} for t, s in team_stats.items()], key=lambda x: x['Pts'], reverse=True)[0]
    purple = sorted([{"Team": t, "Count": s["Injuries"], "Logo": s["Logo"]} for t, s in team_stats.items()], key=lambda x: x['Count'], reverse=True)[0]
    hoarder = sorted([{"Team": t, "Pts": s["Bench"], "Logo": s["Logo"]} for t, s in team_stats.items()], key=lambda x: x['Pts'], reverse=True)[0]
    toilet = sorted(_league.teams, key=lambda x: x.points_for)[0]
    podium = sorted(_league.teams, key=lambda x: (x.wins, x.points_for), reverse=True)[:3]
    
    return {
        "MVP": sorted_players[0] if sorted_players else None, "Podium": podium,
        "Oracle": oracle, "Sniper": sniper, "Purple": purple, "Hoarder": hoarder,
        "Toilet": {"Team": toilet.team_name, "Pts": toilet.points_for, "Logo": get_logo(toilet)},
        "Blowout": biggest_blowout, "Heartbreaker": heartbreaker, "Single": single_game_high,
        "Best Manager": {"Team": podium[0].team_name, "Points": podium[0].points_for, "Logo": get_logo(podium[0])}
    }

@st.cache_data(ttl=3600)
def calculate_draft_analysis(_league):
    live_standings = sorted(_league.teams, key=lambda x: (x.wins, x.points_for), reverse=True)
    total_teams = len(_league.teams)
    cutoff_index = int(total_teams * 0.75) 
    safe_team_names = {t.team_name for t in live_standings[:cutoff_index]}
    waiver_points = {}
    roi_data = []
    for team in _league.teams:
        waiver_sum = 0
        logo = get_logo(team)
        for player in team.roster:
            if player.acquisitionType != 'DRAFT': waiver_sum += player.total_points
            else:
                pick_no = 999
                round_no = 99
                if hasattr(_league, 'draft'):
                    for pick in _league.draft:
                        if pick.playerId == player.playerId:
                            pick_no = (pick.round_num - 1) * len(_league.teams) + pick.round_pick
                            round_no = pick.round_num
                            break
                if pick_no < 999:
                     roi_data.append({"Player": player.name, "Team": team.team_name, "Round": round_no, "Pick Overall": pick_no, "Points": player.total_points, "Position": player.position, "ID": player.playerId})
        waiver_points[team.team_name] = {"Pts": waiver_sum, "Logo": logo, "Wins": team.wins}
    sorted_candidates = sorted(waiver_points.items(), key=lambda x: x[1]["Pts"], reverse=True)
    prescient_data = None
    for team_name, stats in sorted_candidates:
        if team_name in safe_team_names:
            prescient_data = {"Team": team_name, "Points": stats["Pts"], "Logo": stats["Logo"], "Wins": stats["Wins"]}
            break
    if not prescient_data and sorted_candidates:
        top = sorted_candidates[0]
        prescient_data = {"Team": top[0], "Points": top[1]["Pts"], "Logo": top[1]["Logo"], "Wins": top[1]["Wins"]}
    return pd.DataFrame(roi_data), prescient_data

@st.cache_data(ttl=3600)
def scan_dark_pool(_league, limit=20):
    free_agents = _league.free_agents(size=150)
    pool_data = []
    for player in free_agents:
        try:
            status = getattr(player, 'injuryStatus', 'ACTIVE')
            status_str = str(status).upper().replace("_", " ") if status else "ACTIVE"
            if any(k in status_str for k in ['OUT', 'IR', 'RESERVE', 'SUSPENDED', 'PUP', 'DOUBTFUL']): continue
            total = player.total_points if player.total_points > 0 else player.projected_total_points
            weeks = _league.current_week if _league.current_week > 0 else 1
            avg_pts = total / weeks
            if avg_pts > 0.5:
                pool_data.append({"Name": player.name, "Position": player.position, "Team": player.proTeam, "Avg Pts": avg_pts, "Total Pts": total, "ID": player.playerId, "Status": status_str})
        except: continue
    df = pd.DataFrame(pool_data)
    if not df.empty: df = df.sort_values(by="Avg Pts", ascending=False).head(limit)
    return df

@st.cache_data(ttl=3600)
def run_monte_carlo_simulation(_league, simulations=1000):
    team_data = {t.team_id: {"wins": t.wins, "points": t.points_for, "name": t.team_name} for t in _league.teams}
    reg_season_end = _league.settings.reg_season_count
    current_w = _league.current_week
    try: num_playoff_teams = _league.settings.playoff_team_count
    except: num_playoff_teams = 4
    team_power = {t.team_id: t.points_for / (current_w - 1) for t in _league.teams}
    results = {t.team_name: 0 for t in _league.teams}
    for i in range(simulations):
        sim_standings = {k: v.copy() for k, v in team_data.items()}
        if current_w <= reg_season_end:
             for w in range(current_w, reg_season_end + 1):
                 for tid, stats in sim_standings.items():
                     performance = np.random.normal(team_power[tid], 15)
                     if performance > 115: sim_standings[tid]["wins"] += 1
        sorted_teams = sorted(sim_standings.values(), key=lambda x: (x["wins"], x["points"]), reverse=True)
        for name in [t["name"] for t in sorted_teams[:num_playoff_teams]]: results[name] += 1
    final_output = []
    for team in _league.teams:
        odds = (results[team.team_name] / simulations) 
        reason = "🔒 Locked." if odds > 0.99 else "🚀 High Prob." if odds > 0.80 else "⚖️ Bubble." if odds > 0.40 else "🙏 Miracle." if odds > 0.05 else "💀 Dead."
        final_output.append({"Team": team.team_name, "Playoff Odds": odds, "Note": reason})
    return pd.DataFrame(final_output).sort_values(by="Playoff Odds", ascending=False)

@st.cache_data(ttl=3600)
def run_multiverse_simulation(_league, forced_winners_list=None, simulations=1000):
    base_wins = {t.team_name: t.wins for t in _league.teams}
    base_points = {t.team_name: t.points_for for t in _league.teams}
    if forced_winners_list:
        for winner in forced_winners_list:
            if winner in base_wins: base_wins[winner] += 1
    reg_season_end = _league.settings.reg_season_count
    current_w = _league.current_week
    sim_start_week = current_w + 1 if forced_winners_list else current_w
    try: num_playoff_teams = _league.settings.playoff_team_count
    except: num_playoff_teams = 4
    team_power = {t.team_name: t.points_for / (current_w - 1) for t in _league.teams}
    results = {t.team_name: 0 for t in _league.teams}
    for i in range(simulations):
        sim_wins = base_wins.copy()
        if sim_start_week <= reg_season_end:
            for w in range(sim_start_week, reg_season_end + 1):
                for team_name in sim_wins:
                    performance = np.random.normal(team_power.get(team_name, 100), 15)
                    if performance > 115: sim_wins[team_name] += 1
        sorted_teams = sorted(sim_wins.keys(), key=lambda x: (sim_wins[x], base_points[x]), reverse=True)
        for team_name in sorted_teams[:num_playoff_teams]: results[team_name] += 1
    final_output = []
    for team_name in results:
        odds = (results[team_name] / simulations) 
        final_output.append({"Team": team_name, "New Odds": odds})
    return pd.DataFrame(final_output).sort_values(by="New Odds", ascending=False)

@st.cache_data(ttl=3600)
def get_dynasty_data(league_id, espn_s2, swid, current_year, start_year):
    all_seasons_data = []
    for y in range(start_year, current_year + 1):
        try:
            hist_league = League(league_id=league_id, year=y, espn_s2=espn_s2, swid=swid)
            for team in hist_league.teams:
                if team.owners:
                    owner_id = team.owners[0]['id']
                    owner_name = f"{team.owners[0]['firstName']} {team.owners[0]['lastName']}"
                else:
                    owner_id = f"Unknown_{team.team_id}"
                    owner_name = f"Team {team.team_id}"
                made_playoffs = 1 if team.final_standing <= hist_league.settings.playoff_team_count else 0
                is_champ = 1 if team.final_standing == 1 else 0
                all_seasons_data.append({"Year": y, "Owner ID": owner_id, "Manager": owner_name, "Team Name": team.team_name, "Wins": team.wins, "Losses": team.losses, "Points For": team.points_for, "Champ": is_champ, "Playoffs": made_playoffs})
        except: continue
    return pd.DataFrame(all_seasons_data)

def process_dynasty_leaderboard(df_history):
    if df_history.empty: return pd.DataFrame()
    leaderboard = df_history.groupby("Owner ID").agg({"Manager": "last", "Wins": "sum", "Losses": "sum", "Points For": "sum", "Champ": "sum", "Playoffs": "sum", "Year": "count"}).reset_index()
    leaderboard["Win %"] = leaderboard["Wins"] / (leaderboard["Wins"] + leaderboard["Losses"]) * 100
    leaderboard = leaderboard.rename(columns={"Year": "Seasons"})
    return leaderboard.sort_values(by="Wins", ascending=False)

# ==============================================================================
# 5. AI AGENTS
# ==============================================================================
def get_openai_client(key): return OpenAI(api_key=key) if key else None

def ai_response(key, prompt, tokens=600):
    if not key: return "⚠️ OpenAI Key Missing in secrets.toml"
    client = get_openai_client(key)
    if not client: return "⚠️ Invalid Client Config"
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=tokens).choices[0].message.content
    except Exception as e: return f"⚠️ AI Error: {str(e)}"

def get_ai_scouting_report(key, free_agents_str):
    return ai_response(key, f"You are an elite NFL Talent Scout. Analyze: {free_agents_str}. Identify 3 'Must Add'. Style: Scouting Notebook.", 500)
def get_weekly_recap(key, selected_week, top_team):
    return ai_response(key, f"Write a 5 sentence fantasy recap for Week {selected_week}. Highlight {top_team}. Style: Wall Street Report.", 800)
def get_rankings_commentary(key, top, bottom):
    return ai_response(key, f"Write a 5 sentence commentary on rankings. Praise {top}, mock {bottom}. Style: Stephen A. Smith.", 600)
def get_next_week_preview(key, games_list):
    matchups_str = ", ".join([f"{g['home']} vs {g['away']}" for g in games_list])
    return ai_response(key, f"Act as a Vegas Bookie. Preview: {matchups_str}. Pick 'Lock of the Week'.", 800)
def get_season_retrospective(key, mvp, best_mgr):
    return ai_response(key, f"Write a 'State of the Union'. MVP: {mvp}. Best: {best_mgr}. Style: Presidential.", 1000)
def get_ai_trade_proposal(key, t1, t2, r1, r2):
    return ai_response(key, f"Propose a fair trade between {t1}: {r1} and {t2}: {r2}. Explain why.", 600)
