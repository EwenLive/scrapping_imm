import os
import json
import random
import time
from datetime import datetime
from dotenv import load_dotenv
import requests
from playwright.sync_api import sync_playwright

try:
    from playwright_stealth import stealth_sync # type: ignore
except ImportError:
    from playwright_stealth.stealth import stealth_sync # type: ignore

from fake_useragent import UserAgent # type: ignore

load_dotenv()

# --- CONFIGURATION ---
SEARCH_URL = os.getenv("SEARCH_URL")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL") # Changé ici
DB_FILE = "annonces_vues.json"
HEADLESS = os.getenv("HEADLESS", "False").lower() == "true"

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# --- ENVOI DISCORD ---
def send_discord_notification(ad):
    if not DISCORD_WEBHOOK_URL:
        log("ERREUR : DISCORD_WEBHOOK_URL manquant dans le .env")
        return

    # Création du message "Embed" (formaté proprement)
    payload = {
        "username": "Alerte Immo",
        "avatar_url": "https://upload.wikimedia.org/wikipedia/commons/a/ae/Leboncoin_Logo.png",
        "embeds": [{
            "title": f"🏠 {ad['titre']}",
            "url": ad['url'],
            "color": 15814656, # Orange Leboncoin
            "fields": [
                {"name": "💰 Prix", "value": f"**{ad['prix']} €**", "inline": True},
                {"name": "📍 Ville", "value": ad['ville'], "inline": True}
            ],
            "image": {"url": ad['image']} if ad.get('image') else None,
            "footer": {"text": f"ID: {ad['id']} • Trouvé à {datetime.now().strftime('%H:%M')}"}
        }]
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code == 204:
            log(f"🔔 Notification envoyée pour : {ad['titre']}")
        else:
            log(f"❌ Erreur Discord : {response.status_code}")
    except Exception as e:
        log(f"❌ Erreur réseau Discord : {e}")

# --- GESTION DE LA MÉMOIRE ---
def load_seen_ads():
    if not os.path.exists(DB_FILE):
        return set()
    try:
        with open(DB_FILE, 'r') as f:
            return set(json.load(f))
    except:
        return set()

def save_seen_ads(seen_ids):
    with open(DB_FILE, 'w') as f:
        json.dump(list(seen_ids), f)

# --- EXTRACTION ---
def extract_ads(page) -> list:
    # 1. TENTATIVE JSON
    try:
        script_tag = page.wait_for_selector('script#__NEXT_DATA__', state='attached', timeout=5000)
        if script_tag:
            data = json.loads(script_tag.inner_text())
            ads = data.get('props', {}).get('pageProps', {}).get('searchData', {}).get('ads', [])
            if ads:
                log(f"⚡ Extraction JSON réussie ({len(ads)} annonces)")
                return [{
                    "id": str(ad.get('list_id')),
                    "titre": ad.get('subject'),
                    "prix": ad.get('price', [0])[0] if isinstance(ad.get('price'), list) else ad.get('price'),
                    "url": f"https://www.leboncoin.fr/ad/locations/{ad.get('list_id')}",
                    "ville": ad.get('location', {}).get('city'),
                    "image": ad.get('images', {}).get('urls', [None])[0]
                } for ad in ads[:15]]
    except:
        log("⚠️ JSON non trouvé, passage à l'extraction HTML...")

    # 2. TENTATIVE HTML
    try:
        page.wait_for_selector('article[data-test-id="ad"]', timeout=10000)
        ad_elements = page.locator('article[data-test-id="ad"]').all()
        clean_results = []
        for el in ad_elements[:15]:
            try:
                link = el.locator('a[href^="/ad/locations/"]')
                url_path = link.get_attribute("href")
                price_text = el.locator('[data-test-id="price"]').inner_text()
                price = "".join(filter(str.isdigit, price_text))
                ville = el.locator('p[aria-hidden="true"]').last.inner_text()
                
                clean_results.append({
                    "id": str(url_path.split('/')[-1]) if url_path else "N/A",
                    "titre": link.get_attribute("aria-label").replace("Voir l’annonce: ", ""),
                    "prix": int(price) if price else 0,
                    "url": f"https://www.leboncoin.fr{url_path}",
                    "ville": ville,
                    "image": None # Difficile en HTML simple, on privilégie le JSON
                })
            except: continue
        return clean_results
    except Exception as e:
        log(f"❌ Échec total de l'extraction : {e}")
    return []

def run_scraper():
    if not SEARCH_URL or not DISCORD_WEBHOOK_URL:
        log("ERREUR : Configuration manquante dans le .env (URL ou Webhook).")
        return

    seen_ids = load_seen_ads()

    with sync_playwright() as p:
        user_data_dir = "./user_data"
        actual_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=HEADLESS,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox'],
            user_agent=actual_ua,
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = context.pages[0]
        stealth_sync(page)

        try:
            log("Vérification en cours...")
            page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
            
            if "Please enable JS" in page.content():
                log("❌ Bloqué par DataDome ! Résous le captcha manuellement.")
                page.wait_for_timeout(30000) 
            
            annonces = extract_ads(page)
            nouvelles_annonces = [a for a in annonces if a['id'] not in seen_ids]
            
            if nouvelles_annonces:
                log(f"✅ {len(nouvelles_annonces)} NOUVELLES annonces trouvées.")
                # On inverse pour envoyer la plus vieille en premier
                for ad in reversed(nouvelles_annonces):
                    send_discord_notification(ad)
                    seen_ids.add(ad['id'])
                    time.sleep(1) # Petite pause pour Discord
                
                save_seen_ads(seen_ids)
            else:
                log("😴 Rien de nouveau.")

        except Exception as e:
            log(f"❌ Erreur : {e}")
        finally:
            context.close()

if __name__ == "__main__":
    while True:
        try:
            run_scraper()
        except Exception as e:
            log(f"⚠️ Erreur critique : {e}")
        
        wait_time = random.randint(600, 900) 
        log(f"💤 Repos. Prochaine vérification dans {wait_time // 60} minutes...")
        time.sleep(wait_time)