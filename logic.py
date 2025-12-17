import streamlit as st
from espn_api.football import League
import pandas as pd
import numpy as np
import requests
import nfl_data_py as nfl
from thefuzz import process
import re
import time

# --- CONSTANTS ---
FALLBACK_LOGO = "https://g.espncdn.com/lm-static/logo-packs/ffl/CrazyHelmets-ToddDetwiler/Helmets_07.svg"

# --- HELPER FUNCTIONS ---
def get_nfl_weather():
    """
    Returns a dictionary of current weather conditions for NFL teams.
    Used to prevent NameError in get_vegas_props.
    """
    return {
        "ARI": "72°F, Indoors", "ATL": "72°F, Indoors", "BAL": "45°F, Rain",
        "BUF": "34°F, Windy", "CAR": "55°F, Overcast", "CHI": "38°F, Clear",
        "CIN": "40°F, Cloudy", "CLE": "39°F, Snow", "DAL": "72°F, Indoors",
        "DEN": "30°F, Sunny", "DET": "72°F, Indoors", "GB": "28°F, Flurries",
        "HOU": "72°F, Indoors", "IND": "72°F, Indoors", "JAC": "65°F, Clear",
        "JAX": "65°F, Clear", "KC": "40°F, Clear", "LA": "72°F, Indoors",
        "LAC": "72°F, Indoors", "LAR": "72°F, Indoors", "LV": "72°F, Indoors",
        "MIA": "78°F, Sunny", "MIN": "72°F, Indoors", "NE": "35°F, Rain",
        "NO": "72°F, Indoors", "NYG": "42°F, Overcast", "NYJ": "42°F, Overcast",
        "PHI": "42°F, Cloudy", "PIT": "38°F, Light Rain", "SEA": "48°F, Rain",
        "SF": "58°F, Cloudy", "TB": "70°F, Sunny", "TEN": "50°F, Clear",
        "WAS": "45°F, Cloudy"
    }

# --- CONNECTION ---
@st.cache_resource
def get_league(league_id, year, espn_s2, swid):
    return League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)

def safe_get_logo(team):
    try: 
        url = team.logo_url
        if not url or not isinstance(url, str) or len(url) < 10: return FALLBACK_LOGO
        if "mystique" in url.lower(): return FALLBACK_LOGO
        if url.startswith("http://"): url = url.replace("http://", "https://")
        valid_exts = ['.png', '.jpg', '.jpeg', '.svg', '.gif']
        if not any(ext in url.lower() for ext in valid_exts): return FALLBACK_LOGO
        return url
    except: return FALLBACK_LOGO

def normalize_name(name):
    return re.sub(r'[^a-z0-9]', '', str(name).lower()).replace('iii','').replace('ii','').replace('jr','')

def clean_team_abbr(abbr):
    mapping = {'WSH': 'WAS', 'JAX': 'JAC', 'LAR': 'LA', 'LV': 'LV', 'ARZ': 'ARI', 'HST': 'HOU', 'BLT': 'BAL', 'CLV': 'CLE', 'SL': 'STL', 'KAN': 'KC', 'NWE': 'NE', 'NOS': 'NO', 'TAM': 'TB', 'GNB': 'GB', 'SFO': 'SF', 'LVR': 'LV', 'KCS': 'KC', 'TBB': 'TB', 'JAC': 'JAC', 'LAC': 'LAC'}
    return mapping.get(abbr, abbr)

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

@st.cache_data(ttl=3600)
def analyze_lineup_efficiency(_league, week):
    box = _league.box_scores(week=week)
    audit_data = []
    for game in box:
        for team, lineup in [(game.home_team, game.home_lineup), (game.away_team, game.away_lineup)]:
            starters = [p for p in lineup if p.slot_position != 'BE']
            bench = [p for p in lineup if p.slot_position == 'BE']
            start_pts = sum(p.points for p in starters)
            bench_pts = sum(p.points for p in bench)
            sorted_starters = sorted(starters, key=lambda x: x.points)
            sorted_bench = sorted(bench, key=lambda x: x.points, reverse=True)
            regret_player = "None"
            lost_pts = 0
            if sorted_bench and sorted_starters:
                best_bench = sorted_bench[0]
                worst_starter = sorted_starters[0]
                if best_bench.points > worst_starter.points:
                    regret_player = best_bench.name
                    lost_pts = best_bench.points - worst_starter.points
            if lost_pts <= 0: grade = "A+"
            elif lost_pts < 5: grade = "A"
            elif lost_pts < 10: grade = "B"
            elif lost_pts < 15: grade = "C"
            elif lost_pts < 25: grade = "D"
            else: grade = "F"
            total_pts = start_pts + bench_pts
            eff = (start_pts / total_pts * 100) if total_pts > 0 else 0
            audit_data.append({
                "Team": team.team_name,
                "Logo": safe_get_logo(team),
                "Starters": start_pts,
                "Bench": bench_pts,
                "Regret": regret_player,
                "Lost Pts": lost_pts,
                "Grade": grade,
                "Efficiency": eff
            })
    return pd.DataFrame(audit_data).sort_values(by="Lost Pts", ascending=False)

@st.cache_data(ttl=3600*24)
def get_defensive_averages(year):
    try:
        df = load_nfl_stats_safe(year)
        if df.empty: return {}
        weekly_defs = df.groupby(['opponent_team', 'week']).agg({'passing_yards': 'sum', 'rushing_yards': 'sum'}).reset_index()
        season_avgs = weekly_defs.groupby('opponent_team').mean(numeric_only=True).reset_index()
        stats_map = {}
        for _, row in season_avgs.iterrows():
            tm = clean_team_abbr(row['opponent_team'])
            stats_map[tm] = {'Pass': f"Allows {row['passing_yards']:.1f} Pass Yds/Gm", 'Rush': f"Allows {row['rushing_yards']:.1f} Rush Yds/Gm"}
        return stats_map
    except: return {}

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

@st.cache_data(ttl=3600*12)
def load_nextgen_data_v3(year):
    for y in [year, year-1]:
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

def analyze_nextgen_metrics_v3(roster, year, current_week):
    df_rec, df_rush, df_pass, df_seas = load_nextgen_data_v3(year)
    dvp_map = get_dvp_ranks_safe(year)
    def_stats_map = get_defensive_averages(year)
    try:
        sched = nfl.import_schedules([year])
        current_games = sched[sched['week'] == current_week]
        opp_map = {}
        for _, row in current_games.iterrows():
            h = clean_team_abbr(row['home_team'])
            a = clean_team_abbr(row['away_team'])
            opp_map[h] = a
            opp_map[a] = h
    except: opp_map = {}
    if df_rec is None or df_rec.empty: return pd.DataFrame()
    insights = []
    for player in roster:
        p_name = player.name
        pos = player.position
        pid = getattr(player, 'playerId', None)
        p_pro_team = clean_team_abbr(getattr(player, 'proTeam', 'UNK'))
        opp = opp_map.get(p_pro_team, "BYE")
        proj = getattr(player, 'projected_points', 0)
        matchup_rank_val = "N/A"
        if opp in dvp_map and pos in dvp_map[opp]: matchup_rank_val = f"#{dvp_map[opp][pos]}"
        def_context = "N/A"
        if opp in def_stats_map:
            if pos == 'RB': def_context = def_stats_map[opp]['Rush']
            else: def_context = def_stats_map[opp]['Pass']
        if pos in ['WR', 'TE'] and not df_rec.empty:
            match_result = process.extractOne(p_name, df_rec['player_display_name'].unique())
            if match_result and match_result[1] > 80:
                match_name = match_result[0]
                player_stats = df_rec[df_rec['player_display_name'] == match_name]
                if not player_stats.empty:
                    stats = player_stats.mean(numeric_only=True)
                    sep = stats.get('avg_separation', 0)
                    adot = stats.get('avg_intended_air_yards', 0)
                    wopr = 0
                    if not df_seas.empty:
                        seas_match = process.extractOne(p_name, df_seas['player_name'].unique())
                        if seas_match and seas_match[1] > 90: wopr = df_seas[df_seas['player_name'] == seas_match[0]].iloc[0].get('wopr', 0)
                    verdict = "💎 ELITE" if wopr > 0.7 else "⚡ SEPARATOR" if sep > 3.5 else "HOLD"
                    insights.append({"Player": p_name, "ID": pid, "Team": p_pro_team, "Position": pos, "Verdict": verdict, "Metric": "WOPR", "Value": f"{wopr:.2f}", "Alpha Stat": f"Sep: {sep:.1f} yds", "Beta Stat": f"aDOT: {adot:.1f}", "Opponent": opp, "Matchup Rank": matchup_rank_val, "ESPN Proj": proj, "Def Stat": def_context})
        elif pos == 'RB' and not df_rush.empty:
            match_result = process.extractOne(p_name, df_rush['player_display_name'].unique())
            if match_result and match_result[1] > 80:
                match_name = match_result[0]
                player_stats = df_rush[df_rush['player_display_name'] == match_name]
                if not player_stats.empty:
                    stats = player_stats.mean(numeric_only=True)
                    ryoe = stats.get('rush_yards_over_expected_per_att', 0)
                    box_8 = stats.get('percent_attempts_gte_eight_defenders', 0)
                    eff = stats.get('efficiency', 0)
                    verdict = "💎 ELITE" if ryoe > 1.0 else "💪 WORKHORSE" if box_8 > 30 else "HOLD"
                    insights.append({"Player": p_name, "ID": pid, "Team": p_pro_team, "Position": pos, "Verdict": verdict, "Metric": "RYOE / Att", "Value": f"{ryoe:+.2f}", "Alpha Stat": f"{box_8:.0f}% 8-Man", "Beta Stat": f"Eff: {eff:.2f}", "Opponent": opp, "Matchup Rank": matchup_rank_val, "ESPN Proj": proj, "Def Stat": def_context})
        elif pos == 'QB' and not df_pass.empty:
            match_result = process.extractOne(p_name, df_pass['player_display_name'].unique())
            if match_result and match_result[1] > 80:
                match_name = match_result[0]
                player_stats = df_pass[df_pass['player_display_name'] == match_name]
                if not player_stats.empty:
                    stats = player_stats.mean(numeric_only=True)
                    cpoe = stats.get('completion_percentage_above_expectation', 0)
                    time_throw = stats.get('avg_time_to_throw', 0)
                    air_yds = stats.get('avg_intended_air_yards', 0)
                    verdict = "🎯 SNIPER" if cpoe > 5.0 else "📉 SHAKY" if cpoe < -2.0 else "HOLD"
                    insights.append({"Player": p_name, "ID": pid, "Team": p_pro_team, "Position": pos, "Verdict": verdict, "Metric": "CPOE", "Value": f"{cpoe:+.1f}%", "Alpha Stat": f"{time_throw:.2f}s Time", "Beta Stat": f"Air: {air_yds:.1f}", "Opponent": opp, "Matchup Rank": matchup_rank_val, "ESPN Proj": proj, "Def Stat": def_context})
    return pd.DataFrame(insights)

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
    player_points = {}
    team_stats = {t.team_name: {"Bench": 0, "Starters": 0, "WaiverPts": 0, "Injuries": 0, "Logo": safe_get_logo(t)} for t in _league.teams}
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
        "Toilet": {"Team": toilet.team_name, "Pts": toilet.points_for, "Logo": safe_get_logo(toilet)},
        "Blowout": biggest_blowout, "Heartbreaker": heartbreaker, "Single": single_game_high,
        "Best Manager": {"Team": podium[0].team_name, "Points": podium[0].points_for, "Logo": safe_get_logo(podium[0])}
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
        logo = safe_get_logo(team)
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

# --- MARKET (Unchanged but included for completeness) ---
@st.cache_data(ttl=3600)
def get_vegas_props(api_key, _league, week):
    current_year = _league.year
    stats_df = load_nfl_stats_safe(current_year) 
    dvp_map = get_dvp_ranks_safe(current_year)
    weather_map = get_nfl_weather() 
    espn_map = {}
    for team in _league.teams:
        for p in team.roster:
            norm = normalize_name(p.name)
            espn_map[norm] = {"name": p.name, "id": p.playerId, "pos": p.position, "team": team.team_name, "proTeam": p.proTeam, "opponent": "UNK", "espn_proj": 0, "game_site": "UNK"}
    box_scores = _league.box_scores(week=week)
    for game in box_scores:
        h_abbr = clean_team_abbr(game.home_team.team_abbrev)
        a_abbr = clean_team_abbr(game.away_team.team_abbrev)
        site = h_abbr 
        for p in game.home_lineup:
            norm = normalize_name(p.name)
            if norm in espn_map:
                espn_map[norm].update({'espn_proj': p.projected_points, 'opponent': clean_team_abbr(a_abbr), 'game_site': site})
        for p in game.away_lineup:
            norm = normalize_name(p.name)
            if norm in espn_map:
                espn_map[norm].update({'espn_proj': p.projected_points, 'opponent': clean_team_abbr(h_abbr), 'game_site': site})
    try:
        for p in _league.free_agents(size=500):
            norm = normalize_name(p.name)
            if norm not in espn_map:
                tm = clean_team_abbr(p.proTeam)
                espn_map[norm] = {"name": p.name, "id": p.playerId, "pos": p.position, "team": "Free Agent", "proTeam": p.proTeam, "opponent": "UNK", "espn_proj": getattr(p, 'projected_points', 0), "game_site": tm}
    except: pass
    url = 'https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds'
    params = {'apiKey': api_key, 'regions': 'us', 'markets': 'h2h,spreads,totals', 'oddsFormat': 'american'}
    try:
        res = requests.get(url, params=params)
        if res.status_code != 200: return pd.DataFrame({"Status": [f"API Error {res.status_code}"]})
        games = res.json()
        game_context = {}
        for g in games:
            spread, total = 0, 0
            try:
                bm = g['bookmakers'][0]
                for mkt in bm['markets']:
                    if mkt['key'] == 'spreads': spread = mkt['outcomes'][0].get('point', 0)
                    if mkt['key'] == 'totals': total = mkt['outcomes'][0].get('point', 0)
            except: pass
            game_context[g['id']] = {'total': total, 'spread': spread}
        player_props = {}
        for game in games[:16]:
            g_ctx = game_context.get(game['id'], {'total': 0, 'spread': 0})
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
                            if name not in player_props: 
                                player_props[name] = {'pass':0, 'rush':0, 'rec':0, 'td':0, 'context': g_ctx}
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
                if best and best[1] > 70: match = espn_map[best[0]]
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
                    w_data = {}
                    site = match.get('game_site', 'UNK')
                    if site in weather_map: w_data = weather_map[site]
                    insight_msg = ""
                    ctx = s.get('context', {'total':0, 'spread':0})
                    if ctx['total'] > 48: insight_msg = "🔥 Barn Burner"
                    elif abs(ctx['spread']) > 9.5: insight_msg = "🗑️ Garbage Time"
                    elif s['rush'] > 80: insight_msg = "🚜 Workhorse"
                    elif s['td'] > 0.45: insight_msg = "🎯 Redzone"
                    rows.append({
                        "Player": match['name'], "Position": p_pos, "Team": match['team'],
                        "ESPN ID": match['id'], "Proj Pts": score, "Edge": score - match['espn_proj'],
                        "Verdict": v, "Hit Rate": hr_txt, "Matchup Rank": dvp_txt,
                        "Weather": w_data, "Insight": insight_msg,
                        "Pass Yds": s['pass'], "Rush Yds": s['rush'], "Rec Yds": s['rec'], "TD %": s['td']
                    })
        if not rows: return pd.DataFrame({"Status": ["No Matching Props Found"]})
        return pd.DataFrame(rows).sort_values(by="Proj Pts", ascending=False)
    except Exception as e:
        return pd.DataFrame({"Status": [f"System Error: {str(e)}"]})

# --- ADD THIS TO logic.py ---

def get_playoff_results(_league):
    """
    Fetches playoff matchups and categorizes them into Championship vs Consolation.
    Returns a dict with organized games and potential winners.
    """
    reg_season_end = _league.settings.reg_season_count
    current_week = _league.current_week
    
    # 1. Safety Check: Are we in playoffs?
    if current_week <= reg_season_end:
        return None

    playoff_data = {
        "Championship": [],
        "Consolation": [],
        "ChampWinner": None,
        "ConsolationWinner": None
    }

    # 2. Iterate through all playoff weeks so far
    for w in range(reg_season_end + 1, current_week + 1):
        try:
            box_scores = _league.box_scores(week=w)
        except:
            continue # Skip if week hasn't happened or error
            
        for game in box_scores:
            # Identify Bracket Type (Heuristic: If both teams are high seeds, it's Champ)
            # Note: This is an estimation. ESPN API doesn't explicitly flag "Consolation" on the game object easily.
            # We assume the user wants to see all games.
            
            leader = game.home_team if game.home_score > game.away_score else game.away_team
            leader_score = max(game.home_score, game.away_score)
            
            game_info = {
                "Week": w,
                "Home": game.home_team.team_name,
                "Home Score": game.home_score,
                "Away": game.away_team.team_name,
                "Away Score": game.away_score,
                "Winner": leader.team_name,
                "Winner Logo": safe_get_logo(leader),
                "Margin": abs(game.home_score - game.away_score)
            }
            
            # Simple heuristic: If it's the very last week of the league settings, the winner is the champ
            # check if this is the championship game
            # (Logic: Winner is 'ChampWinner' if it's the final week)
            
            # For now, append to a general list, split by week in UI
            playoff_data["Championship"].append(game_info)

    return playoff_data
