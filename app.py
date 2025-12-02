import streamlit as st
from espn_api.football import League
import pandas as pd

st.title("🏈 Fantasy League Recap")

# We will load secrets securely later
try:
    league_id = st.secrets["league_id"]
    year = 2024
    swid = st.secrets["swid"]
    espn_s2 = st.secrets["espn_s2"]
    
    league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
    st.success(f"Connected to league: {league.settings.name}")
    
except Exception as e:
    st.error("Could not connect to ESPN. Check your secrets setup.")