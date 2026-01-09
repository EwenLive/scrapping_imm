# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install poetry
COPY pyproject.toml poetry.lock* ./
# On installe les dépendances sans créer d'environnement virtuel
RUN poetry config virtualenvs.create false && poetry install --no-root --only main

# --- Stage 2: Final ---
FROM python:3.12-slim
WORKDIR /app

# On installe les outils de base
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copie des paquets Python depuis le builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# INSTALLATION CRITIQUE : Playwright + Dépendances système officielles
RUN playwright install chromium
RUN playwright install-deps chromium

# Copie du reste du code
COPY . .

# On s'assure que le fichier JSON existe pour éviter les erreurs de montage
RUN touch annonces_vues.json

CMD ["python", "main.py"]