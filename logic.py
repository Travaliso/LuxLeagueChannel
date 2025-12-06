import streamlit as st
from espn_api.football import League
import pandas as pd
import numpy as np
import requests
import nfl_data_py as nfl
from thefuzz import process
import re
import time

@st.cache_resource
def get_league(league_id, year, espn_s2, swid):
    return League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)

def safe_get_logo(team):
    try: return team.logo_url if team.logo_url else None
    except: return None

def normalize_name(name):
    return re.sub(r'[^a-z0-9]', '', str(name).lower()).replace('iii','').replace('ii','').replace('jr','')

def clean_team_abbr(abbr):
    mapping = {
        'WSH': 'WAS', 'JAX': 'JAC', 'LAR': 'LA', 'LV': 'LV', 'ARZ': 'ARI', 
        'HST': 'HOU', 'BLT': 'BAL', 'CLV': 'CLE', 'SL': 'STL', 'KAN': 'KC',
        'NWE': 'NE', 'NOS': 'NO', 'TAM': 'TB', 'GNB': 'GB', 'SFO': 'SF', 
        'LVR': 'LV', 'KCS': 'KC', 'TBB': 'TB', 'JAC': 'JAC', 'LAC': 'LAC'
    }
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

# --- NEW: DEFENSIVE YARDAGE STATS ---
@st.cache_data(ttl=3600*24)
def get_defensive_averages(year):
    try:
        df = load_nfl_stats_safe(year)
        if df.empty: return {}
        
        # 1. Sum yards by Opponent+Week (Total allowed by that defense that week)
        weekly_defs = df.groupby(['opponent_team', 'week']).agg({
            'passing_yards': 'sum',
            'rushing_yards': 'sum'
        }).reset_index()
        
        # 2. Average over the season
        season_avgs = weekly_defs.groupby('opponent_team').mean(numeric_only=True).reset_index()
        
        stats_map = {}
        for _, row in season_avgs.iterrows():
            tm = clean_team_abbr(row['opponent_team'])
            stats_map[tm] = {
                'Pass': f"Allows {row['passing_yards']:.1f} Pass Yds/Gm",
                'Rush': f"Allows {row['rushing_yards']:.1f} Rush Yds/Gm"
            }
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

# --- UPDATED LAB LOGIC ---
def analyze_nextgen_metrics_v3(roster, year, current_week):
    df_rec, df_rush, df_pass, df_seas = load_nextgen_data_v3(year)
    dvp_map = get_dvp_ranks_safe(year)
    def_stats_map = get_defensive_averages(year) # NEW
    
    # Schedule Logic
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
        
        # Get Opponent
        opp = opp_map.get(p_pro_team, "BYE")
        proj = getattr(player, 'projected_points', 0)
        
        # Get Matchup Rank
        matchup_rank_val = "N/A"
        if opp in dvp_map and pos in dvp_map[opp]:
            matchup_rank_val = f"#{dvp_map[opp][pos]}"
            
        # Get Specific Defensive Stat
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
                    insights.append({
                        "Player": p_name, "ID": pid, "Team": p_pro_team, "Position": pos, 
                        "Verdict": verdict, "Metric": "WOPR", "Value": f"{wopr:.2f}", 
                        "Alpha Stat": f"Sep: {sep:.1f}", "Beta Stat": f"aDOT: {adot:.1f}",
                        "Opponent": opp, "Matchup Rank": matchup_rank_val, "ESPN Proj": proj,
                        "Def Stat": def_context # NEW FIELD
                    })
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
                    insights.append({
                        "Player": p_name, "ID": pid, "Team": p_pro_team, "Position": pos,
                        "Verdict": verdict, "Metric": "RYOE / Att", "Value": f"{ryoe:+.2f}", 
                        "Alpha Stat": f"{box_8:.0f}% 8-Man", "Beta Stat": f"Eff: {eff:.2f}",
                        "Opponent": opp, "Matchup Rank": matchup_rank_val, "ESPN Proj": proj,
                        "Def Stat": def_context # NEW FIELD
                    })
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
                    insights.append({
                        "Player": p_name, "ID": pid, "Team": p_pro_team, "Position": pos, 
                        "Verdict": verdict, "Metric": "CPOE", "Value": f"{cpoe:+.1f}%", 
                        "Alpha Stat": f"{time_throw:.2f}s Time", "Beta Stat": f"Air: {air_yds:.1f}",
                        "Opponent": opp, "Matchup Rank": matchup_rank_val, "ESPN Proj": proj,
                        "Def Stat": def_context # NEW FIELD
                    })
    return pd.DataFrame(insights)

# ... (Previous Helper Functions like scan_dark_pool, etc. kept same for brevity) ...

@st.cache_data(ttl=3600)
def get_vegas_props(api_key):
    # (Same as previous version)
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def calculate_heavy_analytics(_league, current_week):
    # (Same as previous version)
    return pd.DataFrame()

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

@st.cache_data(ttl=3600)
def calculate_season_awards(_league, current_week):
    # (Same as previous version)
    return {}

@st.cache_data(ttl=3600)
def calculate_draft_analysis(_league):
    # (Same as previous version)
    return pd.DataFrame(), None

@st.cache_data(ttl=3600)
def scan_dark_pool(_league, limit=20):
    # (Same as previous version)
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def run_monte_carlo_simulation(_league, simulations=1000):
    # (Same as previous version)
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def run_multiverse_simulation(_league, forced_winners_list=None, simulations=1000):
    # (Same as previous version)
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_dynasty_data(league_id, espn_s2, swid, current_year, start_year):
    # (Same as previous version)
    return pd.DataFrame()

def process_dynasty_leaderboard(df_history):
    # (Same as previous version)
    return pd.DataFrame()
