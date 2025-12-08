import streamlit as st
import os

# 1. Define your Luxury Metadata
TITLE = "Luxury League HQ"
DESCRIPTION = "The ultimate fantasy football concierge. Ledger, Analytics, and Intelligence."
IMAGE_URL = "https://g.espncdn.com/lm-static/logo-packs/ffl/CrazyHelmets-ToddDetwiler/Helmets_07.svg"
URL = "https://theluxuryleagehq.com"

# 2. Locate Streamlit's static index.html
ROOT_DIR = os.path.dirname(st.__file__)
INDEX_PATH = os.path.join(ROOT_DIR, "static", "index.html")

# 3. Define the new meta tags
custom_meta = f"""
    <title>{TITLE}</title>
    <meta name="description" content="{DESCRIPTION}">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{TITLE}">
    <meta property="og:description" content="{DESCRIPTION}">
    <meta property="og:image" content="{IMAGE_URL}">
    <meta property="og:url" content="{URL}">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{TITLE}">
    <meta name="twitter:description" content="{DESCRIPTION}">
    <meta name="twitter:image" content="{IMAGE_URL}">
"""

# 4. Inject into the file
try:
    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        html = f.read()

    # Replace the default title
    html = html.replace("<title>Streamlit</title>", f"<title>{TITLE}</title>")
    
    # Inject our meta tags inside the <head>
    if "</head>" in html:
        html = html.replace("</head>", f"{custom_meta}</head>")
        
        with open(INDEX_PATH, 'w', encoding='utf-8') as f:
            f.write(html)
        print("✅ Luxury Metadata injected successfully!")
    else:
        print("⚠️ Could not find <head> tag in Streamlit index.html")

except Exception as e:
    print(f"❌ Error injecting metadata: {e}")
