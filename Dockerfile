# On utilise l'image Playwright Noble directement
FROM mcr.microsoft.com/playwright/python:v1.49.1-noble

# 1. Éviter les questions pendant l'installation
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# 2. Installation de Xvfb (pour l'écran virtuel)
RUN apt-get update && apt-get install -y \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# 3. Installation de Poetry
RUN pip install --no-cache-dir poetry

# 4. Copie uniquement des fichiers de dépendances
COPY pyproject.toml poetry.lock* ./

# 5. Installation des dépendances Python
RUN poetry config virtualenvs.create false \
    && poetry install --no-root --only main

# 6. Installation de Chromium (le navigateur)
RUN playwright install chromium

# 7. Copie du reste du code source
COPY . .

# 8. Création du fichier JSON s'il n'existe pas
RUN touch annonces_vues.json

# 9. Lancement avec l'écran virtuel
CMD ["sh", "-c", "xvfb-run --auto-servernum --server-args='-screen 0 1920x1080x24' python -u main.py 2>&1"]