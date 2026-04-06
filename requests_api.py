import pandas as pd
import requests
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO

# Configuration
API_URL = "https://api-adresse.data.gouv.fr/search/csv/"
INPUT_FILE = "votre_grand_fichier.csv"
OUTPUT_SUCCESS = "resultats_complets.csv"
OUTPUT_ERRORS = "lignes_en_erreur.csv"

CHUNK_SIZE = 5000   # Taille prudente pour la stabilité
MAX_WORKERS = 3     # Nombre de connexions simultanées

def process_chunk(chunk_id, df_chunk):
    """Envoie un lot à l'API et gère les tentatives."""
    csv_buffer = StringIO()
    df_chunk.to_csv(csv_buffer, index=False)
    files = {'data': ('chunk.csv', csv_buffer.getvalue())}
    
    for attempt in range(3):
        try:
            response = requests.post(API_URL, files=files, timeout=60)
            if response.status_code == 200:
                return "SUCCESS", chunk_id, pd.read_csv(StringIO(response.text))
            elif response.status_code == 429:
                time.sleep(2 * (attempt + 1))
        except Exception:
            time.sleep(1)
            
    return "FAILED", chunk_id, df_chunk

def save_to_csv(df, filename):
    """Ajoute les données au fichier CSV, écrit l'entête seulement si nécessaire."""
    file_exists = os.path.isfile(filename)
    df.to_csv(filename, mode='a', index=False, header=not file_exists, encoding='utf-8')

def main():
    print(f"Début du traitement de {INPUT_FILE}...")
    start_time = time.time()
    
    # Lecture par morceaux (iterator)
    reader = pd.read_csv(INPUT_FILE, chunksize=CHUNK_SIZE)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # On lance les tâches
        future_to_chunk = {executor.submit(process_chunk, i, chunk): i for i, chunk in enumerate(reader)}
        
        # On récupère les résultats dès qu'ils arrivent (as_completed)
        for future in as_completed(future_to_chunk):
            chunk_id = future_to_chunk[future]
            try:
                status, cid, data = future.result()
                
                if status == "SUCCESS":
                    save_to_csv(data, OUTPUT_SUCCESS)
                    print(f"✅ Lot {cid} enregistré.")
                else:
                    save_to_csv(data, OUTPUT_ERRORS)
                    print(f"❌ Lot {cid} échoué et sauvegardé dans les erreurs.")
                    
            except Exception as e:
                print(f"⚠️ Erreur critique sur le lot {chunk_id}: {e}")

    duration = (time.time() - start_time) / 60
    print(f"\n--- Terminé en {duration:.2f} minutes ---")
    print(f"Succès : {OUTPUT_SUCCESS}")
    if os.path.exists(OUTPUT_ERRORS):
        print(f"Attention : des erreurs sont dans {OUTPUT_ERRORS}")

if __name__ == "__main__":
    main()
    
    
#
# with requests.Session() as session:
# # Toutes les requêtes ici réutilisent la même connexion
# session.post(URL, files=...)