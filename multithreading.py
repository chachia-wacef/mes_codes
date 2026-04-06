import pandas as pd
import requests
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Configuration
API_URL = "https://api-adresse.data.gouv.fr/search/csv/"
INPUT_FILE = "votre_grand_fichier.csv"
OUTPUT_SUCCESS = "resultats_complets.csv"
OUTPUT_ERRORS = "lignes_en_erreur.csv"

CHUNK_SIZE = 10000 
MAX_WORKERS = 5 # Avec une Session, on peut être un peu plus ambitieux

def process_chunk(session, chunk_id, df_chunk):
    """Envoie un lot à l'API en utilisant la session partagée."""
    csv_buffer = StringIO()
    df_chunk.to_csv(csv_buffer, index=False)
    files = {'data': ('chunk.csv', csv_buffer.getvalue())}
    
    try:
        # On utilise session.post au lieu de requests.post
        response = session.post(API_URL, files=files, timeout=60)
        
        if response.status_code == 200:
            return "SUCCESS", chunk_id, pd.read_csv(StringIO(response.text))
        elif response.status_code == 429:
            return "RETRY", chunk_id, df_chunk
        else:
            return "FAILED", chunk_id, df_chunk
    except Exception as e:
        return "ERROR", chunk_id, df_chunk

def save_to_csv(df, filename):
    file_exists = os.path.isfile(filename)
    df.to_csv(filename, mode='a', index=False, header=not file_exists, encoding='utf-8')

def main():
    print(f"Lancement du traitement avec Session...")
    start_time = time.time()
    
    # 1. Création de la session
    with requests.Session() as session:
        # Optionnel : Configurer des retries automatiques au niveau HTTP
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))
        
        reader = pd.read_csv(INPUT_FILE, chunksize=CHUNK_SIZE)
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # On passe 'session' à chaque tâche
            future_to_chunk = {
                executor.submit(process_chunk, session, i, chunk): i 
                for i, chunk in enumerate(reader)
            }
            
            for future in as_completed(future_to_chunk):
                status, cid, data = future.result()
                
                if status == "SUCCESS":
                    save_to_csv(data, OUTPUT_SUCCESS)
                    print(f"✅ Lot {cid} enregistré.")
                else:
                    save_to_csv(data, OUTPUT_ERRORS)
                    print(f"❌ Lot {cid} échoué (Status: {status}).")

    end_time = time.time()
    print(f"\nTerminé en {(end_time - start_time)/60:.2f} minutes.")

if __name__ == "__main__":
    main()