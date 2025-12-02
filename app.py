import streamlit as st
from espn_api.football import League

st.title("🏈 Fantasy League Recap")

try:
    # Load secrets
    league_id = st.secrets["league_id"]swid = st.secrets["swid"]      # Ask for the value inside the "swid" drawer
    espn_s2 = st.secrets["espn_s2"] # Ask for the value inside the "espn_s2" drawer    
    # Try connecting (Updated to 2025)
    year = 2025 
    
    st.write(f"Attempting to connect to League ID: {league_id} for Year: {year}...")
    
    league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
    
    st.success(f"✅ Connected to league: {league.settings.name}")

except Exception as e:
    # This will print the SPECIFIC error from Python
    st.error(f"❌ Connection failed. Detailed error below:")
    st.code(e)
    
    st.warning("""
    Common Fixes:
    1. Check if 'year' is correct in the code.
    2. Check if SWID in secrets has { } curly brackets.
    3. Check if League ID is an integer (no quotes) in secrets.
    """)
