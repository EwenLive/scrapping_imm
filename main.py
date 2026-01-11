import os
import json
import random
import time
from datetime import datetime
from dotenv import load_dotenv
import requests
from playwright.sync_api import sync_playwright
import glob

try:
    from playwright_stealth import stealth_sync # type: ignore
except ImportError:
    from playwright_stealth.stealth import stealth_sync # type: ignore

print("--- LOG : Vérification des verrous Chromium ---", flush=True)
for lock_file in glob.glob("user_data/Singleton*"):
    try:
        os.remove(lock_file)
        print(f"--- LOG : Verrou supprimé : {lock_file} ---", flush=True)
    except Exception as e:
        print(f"--- LOG : Erreur lors de la suppression de {lock_file} : {e} ---", flush=True)

load_dotenv()

# --- CONFIGURATION ---
SEARCH_URL = os.getenv("SEARCH_URL")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DB_FILE = "annonces_vues.json"
HEADLESS = os.getenv("HEADLESS", "False").lower() == "true"

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# --- SIMULATION HUMAINE (Point 3.A) ---
def simulate_human_interaction(page):
    log("🖱️ Simulation d'activité humaine...")
    # Mouvement de souris vers un point aléatoire
    page.mouse.move(random.randint(200, 600), random.randint(200, 600))
    time.sleep(random.uniform(1, 2))
    
    # Scroll aléatoire pour simuler la lecture
    for _ in range(random.randint(2, 3)):
        scroll_amount = random.randint(300, 600)
        page.mouse.wheel(0, scroll_amount)
        time.sleep(random.uniform(1.5, 3))

def handle_cookies(page):
    """Accepte les cookies s'ils apparaissent (Point 3.A)"""
    try:
        # Sélecteur pour le bouton "Accepter" du bandeau Didomi (Leboncoin)
        cookie_selector = '#didomi-notice-agree-button'
        if page.is_visible(cookie_selector, timeout=5000):
            time.sleep(random.uniform(1, 2)) # Délai de réflexion "humain"
            page.click(cookie_selector)
            log("🍪 Cookies acceptés automatiquement.")
    except Exception:
        pass # Pas de bandeau ou déjà accepté

# --- ENVOI DISCORD ---
def send_discord_notification(ad):
    if not DISCORD_WEBHOOK_URL: return
    payload = {
        "username": "Alerte Immo",
        "avatar_url": "https://upload.wikimedia.org/wikipedia/commons/a/ae/Leboncoin_Logo.png",
        "embeds": [{
            "title": f"🏠 {ad['titre']}",
            "url": ad['url'],
            "color": 15814656, 
            "fields": [
                {"name": "💰 Prix", "value": f"**{ad['prix']} €**", "inline": True},
                {"name": "📍 Ville", "value": ad['ville'], "inline": True}
            ],
            "image": {"url": ad['image']} if ad.get('image') else None,
            "footer": {"text": f"ID: {ad['id']} • Trouvé à {datetime.now().strftime('%H:%M')}"}
        }]
    }
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        log(f"❌ Erreur Discord : {e}")

# --- GESTION MÉMOIRE ---
def load_seen_ads():
    if not os.path.exists(DB_FILE): return set()
    try:
        with open(DB_FILE, 'r') as f: return set(json.load(f))
    except: return set()

def save_seen_ads(seen_ids):
    with open(DB_FILE, 'w') as f: json.dump(list(seen_ids), f)

# --- EXTRACTION ---
def extract_ads(page) -> list:
    try:
        # On attend que les données JSON soient injectées dans la page
        script_tag = page.wait_for_selector('script#__NEXT_DATA__', state='attached', timeout=5000)
        if script_tag:
            data = json.loads(script_tag.inner_text())
            ads = data.get('props', {}).get('pageProps', {}).get('searchData', {}).get('ads', [])
            if ads:
                log(f"⚡ JSON: {len(ads)} annonces trouvées.")
                return [{
                    "id": str(ad.get('list_id')),
                    "titre": ad.get('subject'),
                    "prix": ad.get('price', [0])[0] if isinstance(ad.get('price'), list) else ad.get('price'),
                    "url": f"https://www.leboncoin.fr/ad/locations/{ad.get('list_id')}",
                    "ville": ad.get('location', {}).get('city'),
                    "image": ad.get('images', {}).get('urls', [None])[0]
                } for ad in ads[:15]]
    except Exception:
        log("⚠️ Échec extraction JSON.")

        timestamp = datetime.now().strftime('%H%M%S')
        screenshot_path = f"user_data/erreur_{timestamp}.png"
        page.screenshot(path=screenshot_path)
        log(f"📸 Capture d'écran enregistrée : {screenshot_path}")
    return []

# --- BOUCLE PRINCIPALE ---
def run_scraper():
    if not SEARCH_URL: return
    seen_ids = load_seen_ads()

    with sync_playwright() as p:
        user_data_dir = "./user_data"
        # On garde un User-Agent fixe et crédible (Point 3.A stabilisé)
        stable_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=HEADLESS,
            user_agent=stable_ua,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--window-size=1920,1080',
            ],
            viewport={'width': 1920, 'height': 1080},
        )
        
        page = context.pages[0]
        stealth_sync(page)

        try:
            log("📡 Connexion à Leboncoin...")

            # 1. Étape de "chauffage" : On passe par la page d'accueil d'abord
            page.goto("https://www.leboncoin.fr", wait_until="domcontentloaded", timeout=60000)
            time.sleep(random.uniform(2, 4))
            
            # 2. On va sur l'URL de recherche (UNE SEULE FOIS)
            # On utilise 'networkidle' pour laisser Datadome finir ses vérifications
            log("🔍 Navigation vers la recherche...")
            page.goto(SEARCH_URL, wait_until="networkidle", timeout=60000)
            
            # Petite pause de "lecture" humaine
            time.sleep(random.uniform(3, 5)) 
            
            # 3. Gestion des cookies (S'ils apparaissent)
            handle_cookies(page)
            
            # 4. Simulation humaine (mouvements + scroll)
            simulate_human_interaction(page)
            
            # 5. Extraction des données
            annonces = extract_ads(page)
            nouvelles = [a for a in annonces if a['id'] not in seen_ids]
            
            if nouvelles:
                log(f"✅ {len(nouvelles)} NOUVELLES annonces trouvées.")
                for ad in reversed(nouvelles):
                    send_discord_notification(ad)
                    seen_ids.add(ad['id'])
                    time.sleep(random.uniform(1, 2)) # Pause entre les notifications
                save_seen_ads(seen_ids)
            else:
                log("😴 Pas de nouvelle annonce.")

        except Exception as e:
            log(f"❌ Erreur durant le scan : {e}")
        finally:
            context.close()

if __name__ == "__main__":
    while True:
        try:
            run_scraper()
        except Exception as e:
            log(f"⚠️ Erreur critique : {e}")
        
        # Intervalle aléatoire (8 à 15 minutes) pour éviter la détection
        wait_time = random.randint(480, 900) 
        log(f"💤 Prochaine vérification dans {wait_time // 60} minutes...")
        time.sleep(wait_time)