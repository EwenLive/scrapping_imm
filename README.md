# 🏠 Bot Alerte Immo Leboncoin

> Système d'automatisation haute performance pour la surveillance immobilière en temps réel avec contournement avancé des protections anti-bot.

---

## ✨ Points Forts & Technologies
Ce bot est conçu pour la **stabilité à long terme** sur des plateformes protégées comme Leboncoin.

* **🛡️ Robustesse Anti-Bot** : Intégration de `Playwright Stealth` et simulation de comportements humains (mouvements de souris erratiques, défilement naturel, délais de réflexion).
* **🌐 Mode Furtif sur Serveur** : Utilisation d'un affichage virtuel (**Xvfb**) au sein de Docker. Cela permet de garder `HEADLESS=False` (beaucoup moins détectable) tout en fonctionnant sur un serveur sans écran.
* **💾 Gestion Intelligente de la Mémoire** : Persistance des données via `annonces_vues.json` pour garantir zéro doublon, même après un redémarrage du conteneur.
* **⚡ Notifications Riches** : Alertes formatées via Discord Webhooks incluant le prix, la ville, et une image de l'annonce.

---

## 🛠️ Installation & Configuration

### 1. Prérequis
- **Docker** et **Docker Compose** (recommandé pour le serveur).
- Ou **Python 3.12+** avec **Poetry** (pour le développement local).

### 2. Configuration (.env)
Créez un fichier `.env` à la racine du projet et complétez les variables suivantes :
```env
SEARCH_URL=[https://www.leboncoin.fr/recherche/](https://www.leboncoin.fr/recherche/)...
DISCORD_WEBHOOK_URL=[https://discord.com/api/webhooks/](https://discord.com/api/webhooks/)...
HEADLESS=False