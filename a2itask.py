import os
import json
import boto3
from botocore.exceptions import ClientError

# --- CONFIGURATION ---
REGION = "eu-west-1"  # Remplacez par votre région AWS
FLOW_ARN = "arn:aws:sagemaker:eu-west-1:127214194449:flow-definition/wacefdemoextraction8"

BUCKET_DOCUMENTS = "a2ifiletests"
BUCKET_JSON = "a2ifiletests"
# ---------------------
REGION_BUCKET="eu-west-1"
from botocore.config import Config
s3_config = Config(
    signature_version='s3v4',
    region_name=REGION
)

# Initialisation des clients AWS
s3 = boto3.client('s3', config=s3_config)
a2i = boto3.client('sagemaker-a2i-runtime', region_name=REGION)

def lister_documents(bucket_name):
    """Liste tous les fichiers (images/pdfs) dans le bucket de documents."""
    fichiers = []
    paginator = s3.get_paginator('list_objects_v2')
    
    for page in paginator.paginate(Bucket=bucket_name):
        if 'Contents' in page:
            for obj in page['Contents']:
                cle = obj['Key']
                # On filtre pour ne prendre que les images et PDFs
                if cle.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg')):
                    fichiers.append(cle)
    return fichiers

def extraire_json_content(bucket_name, json_key):
    """Récupère et lit le contenu d'un fichier JSON directement depuis S3."""
    try:
        response = s3.get_object(Bucket=bucket_name, Key=json_key)
        json_data = json.loads(response['Body'].read().decode('utf-8'))
        return json_data
    except ClientError as e:
        if e.response['Error']['Code'] == "NoSuchKey":
            print(f"⚠️ Warning: Aucun fichier JSON trouvé pour {json_key}")
        else:
            print(f"❌ Erreur lors de la lecture du JSON {json_key}: {e}")
        return None

def formater_donnees(json_interne):
    """Transforme le JSON plat en liste Clé/Valeur pour le template HTML."""
    extraction_formatee = []
    for cle, valeur in json_interne.items():
        extraction_formatee.append({
            "label": str(cle),
            "value": str(valeur)
        })
    return extraction_formatee

def main():
    print("🔍 Récupération de la liste des documents...")
    documents = lister_documents(BUCKET_DOCUMENTS)
    print(f"Total de documents trouvés : {len(documents)}")

    for doc_key in documents:
        # 1. Déterminer le nom du fichier JSON correspondant
        # Exemple: 'dossier/facture_01.pdf' -> base = 'dossier/facture_01', ext = '.pdf'
        nom_base, ext_doc = os.path.splitext(doc_key)
        json_key = f"{nom_base}.json"
        
        print(f"\n🔄 Traitement de : {doc_key}")
        
        # 2. Récupérer le contenu du JSON correspondant
        json_interne = extraire_json_content(BUCKET_JSON, json_key)
        if not json_interne:
            print(f"⏭️ Passage au document suivant (JSON manquant).")
            continue
            
        # 3. Préparer les données pour le template A2I
        extraction_formatee = formater_donnees(json_interne)
        est_pdf = doc_key.lower().endswith('.pdf')
        # url_document_s3 = f"https://{BUCKET_DOCUMENTS}.s3.{REGION}.amazonaws.com/{doc_key}"
        
        # Génération d'un lien sécurisé temporaire (valable 3 jours / 259200 secondes)
        # url_document_s3 = s3.generate_presigned_url(
        #     ClientMethod='get_object',
        #     Params={
        #         'Bucket': BUCKET_DOCUMENTS,
        #         'Key': doc_key
        #     },
        #     ExpiresIn=259200
        # )
        
        # url_document_s3 = f"s3://{BUCKET_DOCUMENTS}/{doc_key}"
        
        # Dans votre script de lancement :
        # if doc_key.lower().endswith('.pdf'):
        #     clean_key = doc_key.lstrip('/')
        #     url_document_s3 = f"s3://{BUCKET_DOCUMENTS}/{doc_key}" # OK pour le crowd-pdf-viewer d'AWS
        # else:
        #     # Pour exp2.jpg, on doit impérativement générer du https://
        #     url_document_s3 = s3.generate_presigned_url(
        #         ClientMethod='get_object',
        #         Params={'Bucket': BUCKET_DOCUMENTS, 'Key': doc_key},
        #         ExpiresIn=259200
        #     )
        
        url_document_s3 = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': BUCKET_DOCUMENTS,
                'Key': doc_key
            },
            ExpiresIn=259200 # Valable 3 jours
        )

        # print(url_document_s3)
        
        payload = {
            "document_url": url_document_s3,
            "is_pdf": est_pdf,
            "extraction_data": extraction_formatee
        }
        
        # 4. Créer un identifiant unique pour la tâche humaine (sans caractères spéciaux)
        # S3 utilise des '/' mais A2I ne les accepte pas dans le nom de la tâche
        # human_loop_name = doc_key.replace('/', '-').replace('.', '-')
        
        import time
        # On ajoute le timestamp actuel pour garantir l'unicité à chaque exécution
        timestamp = int(time.time())
        human_loop_name = f"{doc_key.replace('/', '-').replace('.', '-')}-{timestamp}"
        
        # 5. Envoyer la tâche à Amazon A2I
        # try:
        #     response = a2i.start_human_loop(
        #         HumanLoopName=human_loop_name,
        #         FlowDefinitionArn=FLOW_ARN,
        #         HumanLoopInput={
        #             'InputContent': json.dumps(payload)
        #         }
        #     )
        #     print(f"✅ Tâche envoyée avec succès ! (ID: {human_loop_name})")
        # except ClientError as e:
        #     if e.response['Error']['Code'] == 'ValidationException':
        #         print(f"⚠️ La tâche {human_loop_name} existe déjà ou est en cours.")
        #     else:
        #         print(f"❌ Erreur A2I pour {human_loop_name}: {e}")
        
        try:
            response = a2i.start_human_loop(
                HumanLoopName=human_loop_name,
                FlowDefinitionArn=FLOW_ARN,
                HumanLoopInput={
                    'InputContent': json.dumps(payload)
                }
            )
            print(f"✅ Tâche envoyée avec succès ! (ID: {human_loop_name})")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code in ['ValidationException', 'ConflictException']:
                print(f"⚠️ La tâche {human_loop_name} existe déjà ou est en conflit.")
            else:
                print(f"❌ Erreur A2I pour {human_loop_name}: {e}")

if __name__ == "__main__":
    main()