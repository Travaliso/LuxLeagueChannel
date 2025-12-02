import streamlit as st
from espn_api.football import League
import pandas as pd

st.title("🏈 Fantasy League Recap")

# We will load secrets securely later
try:
    league_id = st.secrets["644655941"]
    year = 2024
    swid = st.secrets["{318A390B-4F7D-43EA-ACF3-3CDC06A36F9F}"]
    espn_s2 = st.secrets["AEAqA4VyoKfmfOGj%2FgFtpq2WY6%2B%2Bu9HgogCc1%2FO8ze9ClTKjI%2FlvVTlBLzeAlROL4D%2FZ4CrLSambNQ1uCK9kvhbPQaBjpEDLctH2wUrc3%2Fy%2FzMYArr4drMAjcKa0pSSPBVcI%2BchNJvAPovUqonXhUAKByw958m8SE6x99qYJJEgfOOFJ%2BKenVOt2Xw%2FYDlQ1qmy%2FJL1NPtJf06%2B45Vie6ZpNrL8LuzZCyM16sLO62bAszJ07U1JfNS%2FJ%2BUztSLMBIfpuUBGZ4KJLvnpqVoQxi4%2Fg8jv5aF6d4VrgLfVV1%2BbzNnHsd2sRVO09LMW%2BUR7QU5k%3D"]
    
    league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
    st.success(f"Connected to league: {league.settings.name}")
    
except Exception as e:
    st.error("Could not connect to ESPN. Check your secrets setup.")
