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
    return ai_response(key, f"Write a DETAILED fantasy football recap for Week {selected_week}. Highlight the Powerhouse of the week: {top_team}. Go into detail on the biggest winners and losers. Style: Wall Street Report.", 2500)

def get_rankings_commentary(key, top_team, bottom_team):
    return ai_response(key, f"Write a commentary on the current Power Rankings. Praise the top team ({top_team}) for their dominance and ruthlessly mock the bottom team ({bottom_team}) for their ineptitude. Style: Stephen A. Smith.", 1500)

def get_next_week_preview(key, games_list):
    matchups_str = ", ".join([f"{g['home']} vs {g['away']} (Spread: {g['spread']})" for g in games_list])
    return ai_response(key, f"Act as a Vegas Sports Bookie. Provide a detailed preview of next week's matchups: {matchups_str}. Analyze the spread for every game. Finally, pick a 'Lock of the Week' and an 'Upset Alert'.", 3000)

def get_season_retrospective(key, mvp, best_mgr):
    return ai_response(key, f"Write a comprehensive 'State of the League' address. MVP: {mvp}. Best Manager: {best_mgr}. Recap the highs and lows of the season so far. Style: Presidential Address.", 4000)

def get_ai_trade_proposal(key, team_a, team_b, roster_a, roster_b):
    return ai_response(key, f"Act as a high-stakes Trade Broker. Propose a fair but exciting trade between Team A ({team_a}): {roster_a} and Team B ({team_b}): {roster_b}. Explain exactly why both sides should take it.", 1500)

def get_ai_scouting_report(key, free_agents_str):
    return ai_response(key, f"You are an elite NFL Talent Scout. Analyze these healthy free agents: {free_agents_str}. Identify 3 'Must Add' players and explain their upside. Style: Scouting Notebook.", 1500)

# --- ASSISTANT GM (ROSTER AWARE) ---
def get_lab_assessment(key, player_name, team, position, opponent, matchup_rank, defensive_stat, metrics, vegas_line, espn_proj, roster_context):
    prompt = f"""
    Act as a decisive Fantasy Football GM. I need to know if I should start {player_name} ({position}, {team}).
    
    PLAYER PROFILE:
    - Opponent: {opponent} ({matchup_rank}, {defensive_stat})
    - Metrics: {metrics}
    - Projections: Vegas {vegas_line} | ESPN {espn_proj}
    
    MY ROSTER OPTIONS AT {position}:
    {roster_context}
    
    INSTRUCTIONS:
    1. Verdict: START, SIT, or PIVOT (to a specific teammate).
    2. The Read: Compare {player_name} directly against the other options in 'My Roster'. If a teammate has a significantly better matchup or metric, recommend them instead. 
       Example: "While {player_name} faces a tough #32 defense, your bench option [Teammate] has a smash spot against #1. Start [Teammate]."
    3. X-Factor: One key stat/factor deciding this specific choice.
    """
    return ai_response(key, prompt, 1500)
