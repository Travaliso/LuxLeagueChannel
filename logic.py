import streamlit as st
import pandas as pd
import numpy as np
import requests
from espn_api.football import League
from thefuzz import process
import nfl_data_py as nfl

# --- CONNECTION ---
@st.cache_resource
def get_league(league_id, year, espn_s2, swid):
    return League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)

def safe_get_logo(team):
    # Helper to safely grab logo string for data processing
    try: return team.logo_url if team.logo_url else None
    except: return None

# --- ANALYTICS ---
@st.cache_data(ttl=3600)
def calculate_heavy_analytics(_league, current_week):
    data_rows = []
    for team in _league.teams:
        power_score = round(team.points_for / current_week, 1)
        true_wins, total_matchups = 0, 0
        for w in range(1, current_week + 1):
            box = _league.box_scores(week=w)
            # Find this team's score in that week
            my_score = next((g.home_score if g.home_team == team else g.away_score for g in box if g.home_team == team or g.away_team == team), 0)
            all_scores = [g.home_score for g in box] + [g.away_score for g in box]
            wins_this_week = sum(1 for s in all_scores if my_score > s)
            true_wins += wins_this_week
            total_matchups += (len(_league.teams) - 1)
        true_win_pct = true_wins / total_matchups if total_matchups > 0 else 0
        actual_win_pct = team.wins / (team.wins + team.losses + 0.001)
        luck_rating = (actual_win_pct - true_win_pct) * 10
        data_rows.append({"Team": team.team_name, "Wins": team.wins, "Points For": team.points_for, "Power Score": power_score, "Luck Rating": luck_rating, "True Win %": true_win_pct})
    return pd.DataFrame(data_rows)

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
        odds = (results[team.team_name] / simulations) * 100
        reason = "🔒 Locked." if odds > 99 else "🚀 High Prob." if odds > 80 else "⚖️ Bubble." if odds > 40 else "🙏 Miracle." if odds > 5 else "💀 Dead."
        final_output.append({"Team": team.team_name, "Playoff Odds": odds, "Note": reason})
    return pd.DataFrame(final_output).sort_values(by="Playoff Odds", ascending=False)

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
                    if str(status).upper() in ['OUT', 'IR', 'RESERVE']: team_stats[team_name]["Injuries"] += 1
                    acq = getattr(p, 'acquisitionType', 'DRAFT')
                    if acq == 'ADD': team_stats[team_name]["WaiverPts"] += p.points

            process(game.home_lineup, game.home_team.team_name)
            process(game.away_lineup, game.away_team.team_name)

    sorted_players = sorted(player_points.values(), key=lambda x: x['Points'], reverse=True)
    oracle = sorted([{"Team": t, "Eff": (s["Starters"]/(s["Starters"]+s["Bench"])*100) if (s["Starters"]+s["Bench"])>0 else 0, "Logo": s["Logo"]} for t, s in team_stats.items()], key=lambda x: x['Eff'], reverse=True)[0]
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

# --- MARKET & LAB ---
@st.cache_data(ttl=3600)
def get_vegas_props(api_key):
    url = 'https://api.the-odds-api.com/v4/sports/americanfootball_nfl/events/upcoming/odds'
    params = {'api_key': api_key, 'regions': 'us', 'markets': 'player_pass_yds,player_rush_yds,player_reception_yds,player_anytime_td', 'oddsFormat': 'american', 'dateFormat': 'iso'}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 422 or not response.json(): return pd.DataFrame({"Status": ["Market Closed"]})
        if response.status_code != 200: return None
        data = response.json()
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

@st.cache_data(ttl=3600 * 12) 
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
