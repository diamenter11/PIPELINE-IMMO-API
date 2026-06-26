import boto3
import json
import time
import csv
import gzip
import os
from datetime import datetime

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
STREAM_NAME = "pipeline-immo-dvf-stream"
REGION = "eu-west-3"
BATCH_SIZE = 100        # Nombre de lignes par batch Kinesis
MAX_BATCHES = 999999       # Nombre de batches à envoyer (10 × 100 = 1000 lignes)
DELAY_BETWEEN_BATCHES = 0  # Secondes entre chaque batch

# Chemin vers ton fichier DVF local
DVF_FILE = r"C:\Users\tedon\Downloads\full_2024.csv"

kinesis = boto3.client("kinesis", region_name=REGION)

def lire_dvf_par_batch(filepath, batch_size, max_batches):
    """Lit le fichier DVF et génère des batches de lignes."""
    batch_num = 0
    batch = []

    opener = gzip.open if filepath.endswith(".gz") else open

    with opener(filepath, "rt", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Nettoyer et typer les données
            transaction = {}
            for key, value in row.items():
                if value == "" or value is None:
                    transaction[key] = None
                else:
                    # Essayer de convertir en nombre si possible
                    try:
                        if "." in str(value):
                            transaction[key] = float(value)
                        else:
                            transaction[key] = int(value)
                    except (ValueError, TypeError):
                        transaction[key] = str(value).strip()

            batch.append(transaction)

            if len(batch) >= batch_size:
                yield batch_num, batch
                batch = []
                batch_num += 1

                if batch_num >= max_batches:
                    break

        # Dernier batch incomplet
        if batch and batch_num < max_batches:
            yield batch_num, batch

def envoyer_batch_kinesis(batch_num, transactions):
    """Envoie un batch de transactions vers Kinesis."""
    records = []

    for transaction in transactions:
        # Clé de partition = code département pour distribuer sur les shards
        dept = str(transaction.get("code_departement", "75")).zfill(2)

        records.append({
            "Data": json.dumps(transaction, ensure_ascii=False, default=str),
            "PartitionKey": dept
        })

    # Envoyer en batch (max 500 records par appel Kinesis)
    response = kinesis.put_records(
        StreamName=STREAM_NAME,
        Records=records
    )

    nb_echecs = response.get("FailedRecordCount", 0)
    nb_succes = len(records) - nb_echecs

    return nb_succes, nb_echecs

# ─────────────────────────────────────────────
# MAIN — Ingestion streaming DVF
# ─────────────────────────────────────────────
print(f"Debut ingestion streaming DVF")
print(f"Fichier source : {DVF_FILE}")
print(f"Stream Kinesis : {STREAM_NAME}")
print(f"Batch size : {BATCH_SIZE} lignes | Max batches : {MAX_BATCHES}")
print(f"Volume total prevu : {BATCH_SIZE * MAX_BATCHES} transactions")
print("-" * 60)

total_envoyes = 0
total_echecs = 0
debut = datetime.now()

for batch_num, batch in lire_dvf_par_batch(DVF_FILE, BATCH_SIZE, MAX_BATCHES):
    nb_succes, nb_echecs = envoyer_batch_kinesis(batch_num, batch)
    total_envoyes += nb_succes
    total_echecs += nb_echecs

    print(f"Batch {batch_num + 1:02d}/{MAX_BATCHES} | "
          f"{nb_succes} envoyes | "
          f"{nb_echecs} echecs | "
          f"Total : {total_envoyes} transactions")

    # Délai entre batches pour simuler un flux progressif
    time.sleep(DELAY_BETWEEN_BATCHES)

duree = (datetime.now() - debut).seconds
print("-" * 60)
print(f"Ingestion terminee en {duree} secondes")
print(f"Total envoye : {total_envoyes} transactions vers Kinesis")
print(f"Total echecs : {total_echecs}")
print(f"La Lambda consumer traite chaque batch automatiquement")
print(f"Verifier S3 Bronze : dvf/streaming/ pour les donnees")
print(f"Verifier S3 Bronze : dvf/streaming/rapports/ pour les rapports qualite")