import streamlit as st
from espn_api.football import League

st.title("🏈 Fantasy League Recap")

try:
    # Load secrets
    league_id = st.secrets["644655941"]
    swid = st.secrets["318A390B-4F7D-43EA-ACF3-3CDC06A36F9F"]
    espn_s2 = st.secrets["AEAqA4VyoKfmfOGj%2FgFtpq2WY6%2B%2Bu9HgogCc1%2FO8ze9ClTKjI%2FlvVTlBLzeAlROL4D%2FZ4CrLSambNQ1uCK9kvhbPQaBjpEDLctH2wUrc3%2Fy%2FzMYArr4drMAjcKa0pSSPBVcI%2BchNJvAPovUqonXhUAKByw958m8SE6x99qYJJEgfOOFJ%2BKenVOt2Xw%2FYDlQ1qmy%2FJL1NPtJf06%2B45Vie6ZpNrL8LuzZCyM16sLO62bAszJ07U1JfNS%2FJ%2BUztSLMBIfpuUBGZ4KJLvnpqVoQxi4%2Fg8jv5aF6d4VrgLfVV1%2BbzNnHsd2sRVO09LMW%2BUR7QU5k%3D"]
    
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
