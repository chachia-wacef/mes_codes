
import os
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from snowflake.snowpark import Session

# 1. Charger et déchiffrer la clé privée
def load_private_key(filepath, passphrase=None):
    with open(filepath, "rb") as key_file:
        p_key = serialization.load_pem_private_key(
            key_file.read(),
            password=passphrase.encode() if passphrase else None,
            backend=default_backend()
        )
    
    # Extraire les bytes de la clé au format DER (requis par Snowflake)
    pkb = p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    return pkb

# 2. Définir les paramètres de connexion
# Remplace les valeurs entre < > par tes propres informations
connection_parameters = {
    "account": "<votre_identifiant_compte>", # ex: xy12345.west-europe.azure
    "user": "<votre_nom_utilisateur>",
    "private_key": load_private_key("snowflake_key.p8"), # Chemin vers ton fichier
    "role": "<votre_role>",           # Optionnel
    "warehouse": "<votre_warehouse>", # Optionnel
    "database": "<votre_base>",       # Optionnel
    "schema": "<votre_schema>"        # Optionnel
}

# 3. Créer la session
try:
    session = Session.builder.configs(connection_parameters).create()
    print("Succès ! Connecté à Snowflake.")
    
    # Test rapide
    df = session.sql("SELECT current_version(), current_role()")
    df.show()

except Exception as e:
    print(f"Erreur lors de la connexion : {e}")
