# ==============================================================================
# LUXURY LEAGUE UTILITIES
# Contains: CSS, API Connectors, Math Engines, AI Helpers
# ==============================================================================

import streamlit as st
from espn_api.football import League
import pandas as pd
import numpy as np
import requests
from openai import OpenAI
from fpdf import FPDF
from thefuzz import process
from contextlib import contextmanager
import nfl_data_py as nfl
import base64

# ==============================================================================
# [1.0] THEME & STYLING
# ==============================================================================
def inject_luxury_css():
    st.markdown("""
    <style>
    /* HIDE DEFAULTS */
    header[data-testid="stHeader"] { display: none; }
    footer { display: none; }
    .block-container { padding-top: 1rem !important; }

    /* BACKGROUND - Midnight Vision */
    .stApp {
        background-color: #060b26; 
        background-image: 
            repeating-linear-gradient(to bottom, transparent, transparent 4px, rgba(0, 0, 0, 0.2) 4px, rgba(0, 0, 0, 0.2) 8px),
            radial-gradient(circle at 0% 0%, rgba(58, 12, 163, 0.4) 0%, transparent 50%),
            radial-gradient(circle at 100% 100%, rgba(0, 201, 255, 0.2) 0%, transparent 50%);
        background-attachment: fixed;
        background-size: cover;
    }

    /* TYPOGRAPHY */
    h1, h2, h3, h4 { color: #ffffff !important; font-family: 'Helvetica Neue', sans-serif; font-weight: 700 !important; text-shadow: 0 2px 4px rgba(0,0,0,0.5); }
    div[data-testid="stMetricValue"] { font-size: 1.6rem !important; color: #ffffff !important; font-weight: 700; text-shadow: 0 0 10px rgba(0, 201, 255, 0.6); }
    div[data-testid="stMetricLabel"] { color: #a0aaba !important; font-size: 0.8rem; }

    /* COMPONENTS */
    .luxury-card {
        background: rgba(17, 25, 40, 0.75); backdrop-filter: blur(16px) saturate(180%);
        border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 20px; margin-bottom: 15px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
    }
    .award-card { border-left: 4px solid #00C9FF; transition: transform 0.3s; min-height: 320px; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
    .award-card:hover { transform: translateY(-5px); box-shadow: 0 0 20px rgba(0, 201, 255, 0.3); }
    .shame-card { background: rgba(40, 10, 10, 0.8); border: 1px solid #FF4B4B; border-left: 4px solid #FF4B4B; min-height: 250px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
    .studio-box { border-left: 4px solid #7209b7; }
    .award-blurb { color: #a0aaba; font-size: 0.8rem; margin-top: 15px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 10px; width: 100%; }

    /* PODIUM */
    .podium-step { border-radius: 10px 10px 0 0; text-align: center; padding: 10px; display: flex; flex-direction: column; justify-content: flex-end; backdrop-filter: blur(10px); box-shadow: 0 4px 20px rgba(0,0,0,0.4); }
    .gold { height: 280px; width: 100%; background: linear-gradient(180deg, rgba(255, 215, 0, 0.2), rgba(17, 25, 40, 0.9)); border: 1px solid #FFD700; border-bottom: none; }
    .silver { height: 220px; width: 100%; background: linear-gradient(180deg, rgba(192, 192, 192, 0.2), rgba(17, 25, 40, 0.9)); border: 1px solid #C0C0C0; border-bottom: none; }
    .bronze { height: 180px; width: 100%; background: linear-gradient(180deg, rgba(205, 127, 50, 0.2), rgba(17, 25, 40, 0.9)); border: 1px solid #CD7F32; border-bottom: none; }
    .rank-num { font-size: 3rem; font-weight: 900; opacity: 0.2; margin-bottom: -20px; }

    /* SIDEBAR & NAVIGATION */
    section[data-testid="stSidebar"] { background-color: rgba(10, 14, 35, 0.95); border-right: 1px solid rgba(255,255,255,0.05); }
    div[data-testid="stRadio"] > label { color: #8a9ab0 !important; font-size: 0.9rem; margin-bottom: 10px; }
    div[role="radiogroup"] label { padding: 12px 15px !important; border-radius: 10px !important; transition: all 0.3s ease; margin-bottom: 5px; border: 1px solid transparent; background-color: transparent; }
    div[role="radiogroup"] label:hover { background-color: rgba(255, 255, 255, 0.05) !important; color: #ffffff !important; transform: translateX(5px); }
    div[role="radiogroup"] label[data-checked="true"] { background: linear-gradient(90deg, rgba(0, 201, 255, 0.15), transparent) !important; border-left: 4px solid #00C9FF !important; color: #ffffff !important; font-weight: 700 !important; }
    div[role="radiogroup"] label > div:first-child { display: none !important; }
    div[data-testid="stDataFrame"] { background-color: rgba(17, 25, 40, 0.5); border-radius: 15px; padding: 15px; border: 1px solid rgba(255,255,255,0.05); }
    
    /* LOADER */
    @keyframes shine { to { background-position: 200% center; } }
    .luxury-loader-text { font-family: 'Helvetica Neue', sans-serif; font-size: 4rem; font-weight: 900; text-transform: uppercase; letter-spacing: 8px; background: linear-gradient(90deg, #1a1c24 0%, #00C9FF 25%, #ffffff 50%, #00C9FF 75%, #1a1c24 100%); background-size: 200% auto; color: transparent; -webkit-background-clip: text; background-clip: text; animation: shine 3s linear infinite; }
    .luxury-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(6, 11, 38, 0.92); backdrop-filter: blur(10px); z-index: 999999; display: flex; flex-direction: column; justify-content: center; align-items: center; }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# [2.0] ASSET HELPERS
# ==============================================================================
def get_logo(team):
    fallback = "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png"
    try: return team.logo_url if team.logo_url else fallback
    except: return fallback

def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200: return None
        return r.json()
    except: return None

@contextmanager
def luxury_spinner(text="Initializing Protocol..."):
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(f'<div class="luxury-overlay"><div class="luxury-loader-text">LUXURY LEAGUE</div><div style="color: #00C9FF; margin-top: 20px; font-family: monospace;">⚡ {text}</div></div>', unsafe_allow_html=True)
    try: yield
    finally: placeholder.empty()

# PDF Generation Class
def clean_for_pdf(text):
    if not isinstance(text, str): return str(text)
    return text.encode('latin-1', 'ignore').decode('latin-1')

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(0, 201, 255)
        self.cell(0, 10, clean_for_pdf('LUXURY LEAGUE PROTOCOL // WEEKLY BRIEFING'), 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 114, 255)
        self.cell(0, 10, clean_for_pdf(title), 0, 1, 'L')
        self.ln(2)
    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.set_text_color(50)
        self.multi_cell(0, 6, clean_for_pdf(body))
        self.ln()

def create_download_link(val, filename):
    b64 = base64.b64encode(val)
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{filename}">Download Executive Briefing (PDF)</a>'

# ==============================================================================
# [3.0] ANALYTICS ENGINES
# ==============================================================================

# [3.1] VEGAS PROPS
@st.cache_data(ttl=3600)
def get_vegas_props(api_key):
    url = 'https://api.the-odds-api.com/v4/sports/americanfootball_nfl/events/upcoming/odds'
    params = {'api_key': api_key, 'regions': 'us', 'markets': 'player_pass_yds,player_rush_yds,player_reception_yds,player_anytime_td', 'oddsFormat': 'american', 'dateFormat': 'iso'}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 422: return pd.DataFrame({"Status": ["Market Closed"]}) 
        if response.status_code != 200: return None
        data = response.json()
        if not data: return pd.DataFrame({"Status": ["Market Closed"]}) 
        
        player_props = {}
        for event in data:
            for bookmaker in event['bookmakers']:
                if bookmaker['key'] in ['draftkings', 'fanduel', 'mgm', 'caesars']:
                    for market in bookmaker['markets']:
                        key = market['key']
                        for outcome in market['outcomes']:
                            name = outcome['description']
                            if name not in player_props: player_props[name] = {'pass':0, 'rush':0, 'rec':0, 'td':0}
                            if key == 'player_pass_yds': player_props[name]['pass'] = outcome.get('point', 0)
                            elif key == 'player_rush_yds': player_props[name]['rush'] = outcome.get('point', 0)
                            elif key == 'player_reception_yds': player_props[name]['rec'] = outcome.get('point', 0)
                            elif key == 'player_anytime_td':
                                odds = outcome.get('price', 0)
                                prob = 100/(odds+100) if odds > 0 else abs(odds)/(abs(odds)+100)
                                player_props[name]['td'] = prob
        vegas_data = []
        for name, s in player_props.items():
            score = (s['pass']*0.04) + (s['rush']*0.1) + (s['rec']*0.1) + (s['td']*6)
            if score > 1: vegas_data.append({"Player": name, "Vegas Score": score})
        return pd.DataFrame(vegas_data)
    except: return None

# [3.2] HEAVY ANALYTICS (HEDGE FUND)
@st.cache_data(ttl=3600)
def calculate_heavy_analytics(league, current_week):
    data_rows = []
    for team in league.teams:
        power_score = round(team.points_for / current_week, 1)
        true_wins, total_matchups = 0, 0
        for w in range(1, current_week + 1):
            box = league.box_scores(week=w)
            my_score = next((g.home_score if g.home_team == team else g.away_score for g in box if g.home_team == team or g.away_team == team), 0)
            all_scores = [g.home_score for g in box] + [g.away_score for g in box]
            wins_this_week = sum(1 for s in all_scores if my_score > s)
            true_wins += wins_this_week
            total_matchups += (len(league.teams) - 1)
        true_win_pct = true_wins / total_matchups if total_matchups > 0 else 0
        actual_win_pct = team.wins / (team.wins + team.losses + 0.001)
        luck_rating = (actual_win_pct - true_win_pct) * 10
        data_rows.append({"Team": team.team_name, "Wins": team.wins, "Points For": team.points_for, "Power Score": power_score, "Luck Rating": luck_rating, "True Win %": true_win_pct})
    return pd.DataFrame(data_rows)

# [3.3] SEASON AWARDS
@st.cache_data(ttl=3600)
def calculate_season_awards(league, current_week):
    player_points = {}
    team_stats = {t.team_name: {"Bench": 0, "Starters": 0, "WaiverPts": 0, "Injuries": 0, "Logo": get_logo(t)} for t in league.teams}
    single_game_high = {"Team": "", "Score": 0, "Week": 0}
    biggest_blowout = {"Winner": "", "Loser": "", "Margin": 0, "Week": 0}
    heartbreaker = {"Winner": "", "Loser": "", "Margin": 999, "Week": 0}
    
    for w in range(1, current_week + 1):
        box = league.box_scores(week=w)
        for game in box:
            margin = abs(game.home_score - game.away_score)
            if game.home_score > game.away_score: winner, loser = game.home_team.team_name, game.away_team.team_name
            else: winner, loser = game.away_team.team_name, game.home_team.team_name
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
                    if str(status).upper() in ['OUT', 'IR', 'RESERVE']: team_stats[team_name]["Injuries"] += 1
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
    toilet = sorted(league.teams, key=lambda x: x.points_for)[0]
    podium_sort = sorted(league.teams, key=lambda x: (x.wins, x.points_for), reverse=True)
    
    return {
        "MVP": sorted_players[0] if sorted_players else None, "Podium": podium_sort[:3],
        "Oracle": oracle, "Sniper": sniper, "Purple": purple, "Hoarder": hoarder,
        "Toilet": {"Team": toilet.team_name, "Pts": toilet.points_for, "Logo": get_logo(toilet)},
        "Blowout": biggest_blowout, "Heartbreaker": heartbreaker, "Single": single_game_high,
        "Best Manager": {"Team": podium_sort[0].team_name, "Points": podium_sort[0].points_for, "Logo": get_logo(podium_sort[0])}
    }

# [3.4] MONTE CARLO
@st.cache_data(ttl=3600)
def run_monte_carlo_simulation(league, simulations=1000):
    team_data = {t.team_id: {"wins": t.wins, "points": t.points_for, "name": t.team_name} for t in league.teams}
    reg_season_end = league.settings.reg_season_count
    current_w = league.current_week
    try: num_playoff_teams = league.settings.playoff_team_count
    except: num_playoff_teams = 4
    team_power = {t.team_id: t.points_for / (current_w - 1) for t in league.teams}
    results = {t.team_name: 0 for t in league.teams}
    
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
    for team in league.teams:
        odds = (results[team.team_name] / simulations) * 100
        reason = "🔒 Locked." if odds > 99 else "🚀 High Prob." if odds > 80 else "⚖️ Bubble." if odds > 40 else "🙏 Miracle." if odds > 5 else "💀 Dead."
        final_output.append({"Team": team.team_name, "Playoff Odds": odds, "Note": reason})
    return pd.DataFrame(final_output).sort_values(by="Playoff Odds", ascending=False)

# [3.5] DARK POOL
@st.cache_data(ttl=3600)
def scan_dark_pool(league, limit=15):
    free_agents = league.free_agents(size=150)
    pool_data = []
    for player in free_agents:
        try:
            status = getattr(player, 'injuryStatus', 'ACTIVE')
            status_str = str(status).upper().replace("_", " ") if status else "ACTIVE"
            if any(k in status_str for k in ['OUT', 'IR', 'RESERVE', 'SUSPENDED', 'PUP', 'DOUBTFUL']): continue
            total = player.total_points if player.total_points > 0 else player.projected_total_points
            avg_pts = total / league.current_week if league.current_week > 0 else 0
            if avg_pts > 0.5:
                pool_data.append({"Name": player.name, "Position": player.position, "Team": player.proTeam, "Avg Pts": avg_pts, "Total Pts": total, "ID": player.playerId, "Status": status_str})
        except: continue
    df = pd.DataFrame(pool_data)
    if not df.empty: df = df.sort_values(by="Avg Pts", ascending=False).head(limit)
    return df

# [3.6] DYNASTY VAULT
@st.cache_data(ttl=3600)
def get_dynasty_data(league_id, espn_s2, swid, current_year, start_year):
    all_seasons_data = []
    for y in range(start_year, current_year + 1):
        try:
            hist_league = League(league_id=league_id, year=y, espn_s2=espn_s2, swid=swid)
            for team in hist_league.teams:
                owner_id = team.owners[0]['id'] if team.owners else f"Unknown_{team.team_id}"
                owner_name = f"{team.owners[0]['firstName']} {team.owners[0]['lastName']}" if team.owners else f"Team {team.team_id}"
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

# [3.7] NEXT GEN LAB
@st.cache_data(ttl=3600 * 12) 
def load_nextgen_data_v3(year):
    years_to_try = [year, year - 1]
    for y in years_to_try:
        try:
            df_rec = nfl.import_ngs_data(stat_type='receiving', years=[y])
            if not df_rec.empty:
                df_rush = nfl.import_ngs_data(stat_type='rushing', years=[y])
                df_pass = nfl.import_ngs_data(stat_type='passing', years=[y])
                try: df_seas = nfl.import_seasonal_data([y])
                except: df_seas = pd.DataFrame()
                return df_rec, df_rush, df_pass, df_seas
        except: continue
    return None, None, None, None

def analyze_nextgen_metrics_v3(roster, year):
    df_rec, df_rush, df_pass, df_seas = load_nextgen_data_v3(year)
    if df_rec is None or df_rec.empty: return pd.DataFrame()

    insights = []
    for player in roster:
        p_name, pos, pid, p_team = player.name, player.position, getattr(player, 'playerId', None), getattr(player, 'proTeam', 'N/A')
        
        if pos in ['WR', 'TE'] and not df_rec.empty:
            match_result = process.extractOne(p_name, df_rec['player_display_name'].unique())
            if match_result and match_result[1] > 80:
                stats = df_rec[df_rec['player_display_name'] == match_result[0]].mean(numeric_only=True)
                sep, yac_exp = stats.get('avg_separation', 0), stats.get('avg_yac_above_expectation', 0)
                wopr = 0
                if not df_seas.empty:
                    seas_match = process.extractOne(p_name, df_seas['player_name'].unique())
                    if seas_match and seas_match[1] > 90: wopr = df_seas[df_seas['player_name'] == seas_match[0]].iloc[0].get('wopr', 0)
                verdict = "💎 ELITE" if wopr > 0.7 else "⚡ SEPARATOR" if sep > 3.5 else "🚀 YAC MONSTER" if yac_exp > 2.0 else "HOLD"
                insights.append({"Player": p_name, "ID": pid, "Team": p_team, "Position": pos, "Metric": "WOPR", "Value": f"{wopr:.2f}", "Alpha Stat": f"{sep:.1f} yds Sep", "Verdict": verdict})

        elif pos == 'RB' and not df_rush.empty:
            match_result = process.extractOne(p_name, df_rush['player_display_name'].unique())
            if match_result and match_result[1] > 80:
                stats = df_rush[df_rush['player_display_name'] == match_result[0]].mean(numeric_only=True)
                ryoe, box_8 = stats.get('rush_yards_over_expected_per_att', 0), stats.get('percent_attempts_gte_eight_defenders', 0)
                verdict = "💎 ELITE" if ryoe > 1.0 else "💪 WORKHORSE" if box_8 > 30 else "🚫 PLODDER" if ryoe < -0.5 else "HOLD"
                insights.append({"Player": p_name, "ID": pid, "Team": p_team, "Position": pos, "Metric": "RYOE / Att", "Value": f"{ryoe:+.2f}", "Alpha Stat": f"{box_8:.0f}% 8-Man Box", "Verdict": verdict})
        
        elif pos == 'QB' and not df_pass.empty:
            match_result = process.extractOne(p_name, df_pass['player_display_name'].unique())
            if match_result and match_result[1] > 80:
                stats = df_pass[df_pass['player_display_name'] == match_result[0]].mean(numeric_only=True)
                cpoe, time_throw = stats.get('completion_percentage_above_expectation', 0), stats.get('avg_time_to_throw', 0)
                verdict = "🎯 SNIPER" if cpoe > 5.0 else "⏳ HOLDER" if time_throw > 3.0 else "📉 SHAKY" if cpoe < -2.0 else "HOLD"
                insights.append({"Player": p_name, "ID": pid, "Team": p_team, "Position": pos, "Metric": "CPOE", "Value": f"{cpoe:+.1f}%", "Alpha Stat": f"{time_throw:.2f}s Time", "Verdict": verdict})

    return pd.DataFrame(insights)

# [3.8] AI HELPERS
def get_openai_client(key): return OpenAI(api_key=key) if key else None
def ai_response(key, prompt, tokens=600):
    client = get_openai_client(key)
    if not client: return "⚠️ Analyst Offline."
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=tokens).choices[0].message.content
    except: return "Analyst Offline."
        
# --- [3.9.0] THE MULTIVERSE ENGINE (SCENARIO PLANNING) ---
@st.cache_data(ttl=3600)
def run_multiverse_simulation(_league, forced_winners_list=None, simulations=1000):
    """
    forced_winners_list: A list of Team Names who are GUARANTEED to win next week.
    """
    # 1. Setup Base Data (Current Standings)
    # We map Team Name -> Current Wins
    base_wins = {t.team_name: t.wins for t in _league.teams}
    base_points = {t.team_name: t.points_for for t in _league.teams}
    
    # 2. Apply The "Multiverse" Changes (Forced Outcomes)
    # If a team is in the 'forced_winners_list', we give them a win NOW.
    # We assume the opponent loses (gets 0 wins added).
    if forced_winners_list:
        for winner in forced_winners_list:
            if winner in base_wins:
                base_wins[winner] += 1
                
    # 3. Determine Simulation Scope
    # If we forced outcomes for Next Week, we only simulate from (Next Week + 1) to End.
    # If we didn't force anything, we simulate from Next Week to End.
    reg_season_end = _league.settings.reg_season_count
    current_w = _league.current_week
    
    # If we are forcing next week, the random sim starts the week AFTER next
    sim_start_week = current_w + 1 if forced_winners_list else current_w
    
    try: num_playoff_teams = _league.settings.playoff_team_count
    except: num_playoff_teams = 4
    
    # Calculate Team Power for random simulation
    team_power = {t.team_name: t.points_for / (current_w - 1) for t in _league.teams}
    
    results = {t.team_name: 0 for t in _league.teams}
    
    # 4. Run Simulation
    for i in range(simulations):
        # Create a temporary standings board for this run
        sim_wins = base_wins.copy()
        
        # Loop through remaining weeks
        if sim_start_week <= reg_season_end:
            for w in range(sim_start_week, reg_season_end + 1):
                # Simple Sim: Everyone plays against league average
                # (For a perfect sim, we'd need the exact future schedule object, which is heavy)
                for team_name in sim_wins:
                    power = team_power.get(team_name, 100)
                    performance = np.random.normal(power, 15)
                    if performance > 115: # League avg winning score
                        sim_wins[team_name] += 1
        
        # 5. Determine Playoff Teams for this run
        # Sort by Wins (Desc), then Points (Desc)
        # We use base_points for tiebreaker (assuming points don't change drastically in 2 weeks)
        sorted_teams = sorted(sim_wins.keys(), key=lambda x: (sim_wins[x], base_points[x]), reverse=True)
        
        # Top N make playoffs
        for team_name in sorted_teams[:num_playoff_teams]:
            results[team_name] += 1

    # 6. Formatting Output
    final_output = []
    for team_name in results:
        odds = (results[team_name] / simulations) * 100
        final_output.append({
            "Team": team_name, 
            "New Odds": odds
        })
        
    return pd.DataFrame(final_output).sort_values(by="New Odds", ascending=False)
