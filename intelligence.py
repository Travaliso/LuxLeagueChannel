from openai import OpenAI

def get_openai_client(key):
    if not key: return None
    return OpenAI(api_key=key)

def ai_response(key, prompt, tokens=600):
    client = get_openai_client(key)
    if not client: return "⚠️ Analyst Offline."
    try: return client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}], max_tokens=tokens).choices[0].message.content
    except Exception as e: return f"⚠️ AI Error: {str(e)}"

def get_weekly_recap(key, selected_week, top_team):
    return ai_response(key, f"Write a DETAILED, 5-10 sentence fantasy recap for Week {selected_week}. Highlight Powerhouse: {top_team}. Style: Wall Street Report.", 800)

def get_rankings_commentary(key, top_team, bottom_team):
    return ai_response(key, f"Write a 5-8 sentence commentary on Power Rankings. Praise {top_team} and mock {bottom_team}. Style: Stephen A. Smith.", 600)

def get_next_week_preview(key, games_list):
    matchups_str = ", ".join([f"{g['home']} vs {g['away']} (Spread: {g['spread']})" for g in games_list])
    return ai_response(key, f"Act as a Vegas Sports Bookie. Provide a detailed preview of next week's matchups: {matchups_str}. Pick 'Lock of the Week' and 'Upset Alert'.", 800)

def get_season_retrospective(key, mvp, best_mgr):
    return ai_response(key, f"Write a 'State of the Union' address for the league. MVP: {mvp}. Best Manager: {best_mgr}. Style: Presidential.", 1000)

def get_ai_trade_proposal(key, team_a, team_b, roster_a, roster_b):
    return ai_response(key, f"Act as Trade Broker. Propose a fair trade between Team A ({team_a}): {roster_a} and Team B ({team_b}): {roster_b}. Explain why.", 600)

def get_ai_scouting_report(key, free_agents_str):
    return ai_response(key, f"You are an elite NFL Talent Scout. Analyze these healthy free agents: {free_agents_str}. Identify 3 'Must Add' players. Style: Scouting Notebook.", 500)

# --- UPDATED ASSISTANT GM (NON-SPECULATIVE) ---
def get_lab_assessment(key, player_name, team, position, opponent, matchup_rank, metrics, vegas_line, espn_proj):
    prompt = f"""
    Act as a decisive, cold-hard NFL General Manager. Analyze {player_name} ({position}, {team}).
    
    Hard Data:
    - Opponent: {opponent}
    - Matchup Rank: {matchup_rank} (1=Softest, 32=Hardest). Use this to justify your verdict.
    - Advanced Stats: {metrics}
    - Vegas Projection: {vegas_line}
    - ESPN Projection: {espn_proj}
    
    Instructions:
    1. Verdict: One word (START, SIT, HOLD, TRADE).
    2. The Read: 2-3 sentences. BE SPECIFIC. Reference the Matchup Rank number and the Advanced Stats directly. Do not say "might" or "could". Say "will" or "is". 
    3. X-Factor: The one stat that matters most this week.
    """
    return ai_response(key, prompt, 600)
