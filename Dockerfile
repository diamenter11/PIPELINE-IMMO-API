# Image de base Python légère
FROM python:3.12-slim

# Métadonnées
LABEL maintainer="Pipeline Immo M2 Data Engineering"
LABEL description="API FastAPI Pipeline Immobilière"
LABEL version="1.0.0"

# Répertoire de travail dans le container
WORKDIR /app

# Copier les dépendances d'abord (optimise le cache Docker)
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY main.py .
COPY database.py .
COPY auth.py .

# Le fichier .env n'est PAS copié — il sera fourni via variables d'environnement
# (bonne pratique sécurité : jamais de secrets dans l'image Docker)

# Exposer le port FastAPI
EXPOSE 8000

# Commande de démarrage
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]