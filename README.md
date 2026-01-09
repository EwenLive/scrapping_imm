# Bot Alerte Immo Leboncoin

Ce bot surveille Leboncoin et envoie les nouvelles annonces sur Discord.

## Installation
1. Remplir le fichier `.env` avec ton URL de recherche et ton Webhook Discord.
2. Installer les dépendances : `pip install playwright playwright-stealth fake-useragent python-dotenv requests`
3. Installer les navigateurs : `playwright install chromium`

## Lancement (Classique)
`python main.py`

## Lancement (Docker)
`docker-compose up --build -d`