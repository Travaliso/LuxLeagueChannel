from openai import OpenAI

def get_openai_client(key):
    if not key: return None
    return OpenAI(api_key=key)

def ai_response(key, prompt, tokens=1500):
    client = get_openai_client(key)
    if not client: return "⚠️ Analyst Offline."
    try: 
        return client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[{"role": "user", "content": prompt}], 
            max_tokens=tokens
        ).choices[0].message.content
    except Exception as e: return f"⚠️ AI Error: {str(e)}"

def get_weekly_recap(key, selected_week, top_team):
    prompt = f"""
    Write a DETAILED fantasy football recap for Week {selected_week}. 
    Highlight the Powerhouse of the week: {top_team}. 
    
    CRITICAL INSTRUCTIONS:
    1. This is FANTASY football, not real football. Team A does not "play defense" against Team B. 
    2. Focus entirely on point production, roster management, and efficiency.
    3. Do NOT use betting terminology (covers, spreads, moneyline).
    
    Style: Wall Street Executive Report.
    """
    return ai_response(key, prompt, 2500)

def get_rankings_commentary(key, top_team, bottom_team):
    prompt = f"""
    Write a commentary on the current Power Rankings. 
    Praise the top team ({top_team}) for their roster construction and point dominance.
    Ruthlessly mock the bottom team ({bottom_team}) for their low scoring and poor management.
    
    Style: Stephen A. Smith (Loud, opinionated, but strictly about FANTASY performance).
    """
    return ai_response(key, prompt, 1500)

def get_next_week_preview(key, games_list):
    # Format matchups with "Projected Margin" instead of "Spread" to remove betting context
    matchups_str = ", ".join([f"{g['home']} vs {g['away']} (Proj Margin: {g['spread']})" for g in games_list])
    
    prompt = f"""
    Act as a Senior Fantasy Football Analyst. Provide a detailed preview of next week's matchups: {matchups_str}.
    
    CRITICAL INSTRUCTIONS:
    1. STRICTLY NO BETTING REFERENCES. Do not use words like 'cover', 'vig', 'lock', or 'odds'.
    2. Analyze the 'Projected Margin'. If a team is a big underdog, discuss their need for high-ceiling 'boom' players to bridge the gap.
    3. Remember: In fantasy, you cannot stop your opponent from scoring. Focus on offensive firepower.
    
    OUTPUT:
    - Breakdown of key matchups.
    - Pick a 'Matchup of the Week' (Closest projected margin).
    - Pick an 'Underdog Watch' (A team projected to lose that has high-upside players).
    """
    return ai_response(key, prompt, 3000)

def get_season_retrospective(key, mvp, best_mgr):
    prompt = f"""
    Write a comprehensive 'State of the League' address. 
    MVP Player: {mvp}. 
    Best Manager: {best_mgr}. 
    
    Recap the highs (scoring explosions) and lows (injury busts) of the season so far.
    Style: Presidential Address.
    """
    return ai_response(key, prompt, 4000)

def get_ai_trade_proposal(key, team_a, team_b, roster_a, roster_b):
    prompt = f"""
    Act as a Trade Broker. Propose a fair mutually beneficial trade between Team A ({team_a}) and Team B ({team_b}).
    
    Team A Roster: {roster_a}
    Team B Roster: {roster_b}
    
    Explain why this trade helps both teams improve their starting lineups.
    """
    return ai_response(key, prompt, 1500)

def get_ai_scouting_report(key, free_agents_str):
    prompt = f"""
    You are an elite NFL Talent Scout looking for FANTASY relevance. 
    Analyze these healthy free agents: {free_agents_str}. 
    
    Identify 3 'Must Add' players based on opportunity (injuries ahead of them) and recent production.
    Style: Scouting Notebook.
    """
    return ai_response(key, prompt, 1500)

# --- ASSISTANT GM (ROSTER AWARE) ---
def get_lab_assessment(key, player_name, team, position, opponent, matchup_rank, defensive_stat, metrics, vegas_line, espn_proj, roster_context):
    prompt = f"""
    Act as a decisive Fantasy Football GM. I need to know if I should start {player_name} ({position}, {team}).
    
    PLAYER PROFILE:
    - Opponent: {opponent} ({matchup_rank} vs position)
    - Context: {defensive_stat}
    - Advanced Metrics: {metrics}
    - Projections: {espn_proj} points
    
    MY ROSTER OPTIONS AT {position}:
    {roster_context}
    
    INSTRUCTIONS:
    1. Verdict: START, SIT, or PIVOT (to a specific teammate).
    2. The Read: Compare {player_name} directly against your other options. 
       If you are projected to lose big, recommend the higher variance (boom/bust) player.
       If you are projected to win, recommend the safer floor player.
    3. X-Factor: One key stat deciding this choice.
    """
    return ai_response(key, prompt, 1500)
