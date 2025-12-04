import streamlit as st
import requests
import base64
from fpdf import FPDF
from contextlib import contextmanager

def inject_luxury_css():
    st.markdown("""
    <style>
    header[data-testid="stHeader"] { display: none; }
    footer { display: none; }
    .block-container { padding-top: 1rem !important; }
    .stApp {
        background-color: #060b26; 
        background-image: 
            repeating-linear-gradient(to bottom, transparent, transparent 4px, rgba(0, 0, 0, 0.2) 4px, rgba(0, 0, 0, 0.2) 8px),
            radial-gradient(circle at 0% 0%, rgba(58, 12, 163, 0.4) 0%, transparent 50%),
            radial-gradient(circle at 100% 100%, rgba(0, 201, 255, 0.2) 0%, transparent 50%);
        background-attachment: fixed; background-size: cover;
    }
    h1, h2, h3, h4 { color: #ffffff !important; font-family: 'Helvetica Neue', sans-serif; font-weight: 700 !important; text-shadow: 0 2px 4px rgba(0,0,0,0.5); }
    div[data-testid="stMetricValue"] { font-size: 1.6rem !important; color: #ffffff !important; font-weight: 700; text-shadow: 0 0 10px rgba(0, 201, 255, 0.6); }
    div[data-testid="stMetricLabel"] { color: #a0aaba !important; font-size: 0.8rem; }
    .luxury-card { background: rgba(17, 25, 40, 0.75); backdrop-filter: blur(16px) saturate(180%); border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.08); padding: 20px; margin-bottom: 15px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3); }
    .award-card { border-left: 4px solid #00C9FF; transition: transform 0.3s; min-height: 380px; display: flex; flex-direction: column; justify-content: flex-start; align-items: center; text-align: center; }
    .award-card:hover { transform: translateY(-5px); box-shadow: 0 0 20px rgba(0, 201, 255, 0.3); }
    .award-blurb { color: #a0aaba; font-size: 0.85rem; margin-top: 15px; line-height: 1.5; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 10px; width: 100%; font-style: normal; }
    .shame-card { background: rgba(40, 10, 10, 0.8); border: 1px solid #FF4B4B; border-left: 4px solid #FF4B4B; min-height: 250px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
    .studio-box { border-left: 4px solid #7209b7; }
    .podium-step { border-radius: 10px 10px 0 0; text-align: center; padding: 10px; display: flex; flex-direction: column; justify-content: flex-end; backdrop-filter: blur(10px); box-shadow: 0 4px 20px rgba(0,0,0,0.4); }
    .gold { height: 300px; width: 100%; background: linear-gradient(180deg, rgba(255, 215, 0, 0.2), rgba(17, 25, 40, 0.9)); border: 1px solid #FFD700; border-bottom: none; }
    .silver { height: 240px; width: 100%; background: linear-gradient(180deg, rgba(192, 192, 192, 0.2), rgba(17, 25, 40, 0.9)); border: 1px solid #C0C0C0; border-bottom: none; }
    .bronze { height: 200px; width: 100%; background: linear-gradient(180deg, rgba(205, 127, 50, 0.2), rgba(17, 25, 40, 0.9)); border: 1px solid #CD7F32; border-bottom: none; }
    .rank-num { font-size: 3rem; font-weight: 900; opacity: 0.2; margin-bottom: -20px; }
    section[data-testid="stSidebar"] { background-color: rgba(10, 14, 35, 0.95); border-right: 1px solid rgba(255,255,255,0.05); }
    div[data-testid="stRadio"] > label { color: #8a9ab0 !important; font-size: 0.9rem; margin-bottom: 10px; }
    div[role="radiogroup"] label { padding: 12px 15px !important; border-radius: 10px !important; transition: all 0.3s ease; margin-bottom: 5px; border: 1px solid transparent; background-color: transparent; }
    div[role="radiogroup"] label:hover { background-color: rgba(255, 255, 255, 0.05) !important; color: #ffffff !important; transform: translateX(5px); }
    div[role="radiogroup"] label[data-checked="true"] { background: linear-gradient(90deg, rgba(0, 201, 255, 0.15), transparent) !important; border-left: 4px solid #00C9FF !important; color: #ffffff !important; font-weight: 700 !important; }
    div[role="radiogroup"] label > div:first-child { display: none !important; }
    div[data-testid="stDataFrame"] { background-color: rgba(17, 25, 40, 0.5); border-radius: 15px; padding: 15px; border: 1px solid rgba(255,255,255,0.05); }
    @keyframes shine { to { background-position: 200% center; } }
    .luxury-loader-text { font-family: 'Helvetica Neue', sans-serif; font-size: 4rem; font-weight: 900; text-transform: uppercase; letter-spacing: 8px; background: linear-gradient(90deg, #1a1c24 0%, #00C9FF 25%, #ffffff 50%, #00C9FF 75%, #1a1c24 100%); background-size: 200% auto; color: transparent; -webkit-background-clip: text; background-clip: text; animation: shine 3s linear infinite; }
    .loader-sub { font-family: monospace; color: #00C9FF; font-size: 1.2rem; margin-top: 20px; text-transform: uppercase; letter-spacing: 3px; animation: blink 1.5s infinite ease-in-out; }
    .luxury-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(6, 11, 38, 0.92); backdrop-filter: blur(10px); z-index: 999999; display: flex; flex-direction: column; justify-content: center; align-items: center; }
    </style>
    """, unsafe_allow_html=True)

def load_lottieurl(url: str):
    try: return requests.get(url).json()
    except: return None

@contextmanager
def luxury_spinner(text="Initializing Protocol..."):
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(f'<div class="luxury-overlay"><div class="luxury-loader-text">LUXURY LEAGUE</div><div class="loader-sub">⚡ {text}</div></div>', unsafe_allow_html=True)
    try: yield
    finally: placeholder.empty()

def get_logo_url(team):
    fallback = "https://a.espncdn.com/combiner/i?img=/i/teamlogos/leagues/500/nfl.png"
    try: return team.logo_url if team.logo_url else fallback
    except: return fallback

def render_hero_card(col, player):
    with col:
        st.markdown(f"""
        <div class="luxury-card" style="padding: 15px; display: flex; align-items: center; justify-content: start;">
            <img src="https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/{player['ID']}.png&w=80&h=60" 
                 style="border-radius: 8px; margin-right: 15px; border: 1px solid rgba(0, 201, 255, 0.5); box-shadow: 0 0 10px rgba(0, 201, 255, 0.2);">
            <div>
                <div style="color: #ffffff; font-weight: 800; font-size: 16px; text-transform: uppercase; letter-spacing: 1px;">{player['Name']}</div>
                <div style="color: #00C9FF; font-size: 14px; font-weight: 600;">{player['Points']} PTS</div>
                <div style="color: #a0aaba; font-size: 11px;">{player['Team']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

def clean_for_pdf(text):
    if not isinstance(text, str): return str(text)
    return text.encode('latin-1', 'ignore').decode('latin-1')

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(0, 201, 255)
        self.cell(0, 10, clean_for_pdf('LUXURY LEAGUE PROTOCOL // WEEKLY BRIEFING'), 0, 1, 'C')
        self.ln(5)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 114, 255)
        self.cell(0, 10, clean_for_pdf(title), 0, 1, 'L')
        self.ln(2)
    def chapter_body(self, body):
        self.set_font('Arial', '', 10)
        self.set_text_color(50)
        self.multi_cell(0, 6, clean_for_pdf(body))
        self.ln()

def create_download_link(val, filename):
    b64 = base64.b64encode(val)
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{filename}">Download Executive Briefing (PDF)</a>'
