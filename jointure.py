
from snowflake.snowpark import Session

# 1. Définition des paramètres de connexion
connection_parameters = {
    "account": "votre_identifiant_compte", # Format: <orgname>-<accountname>
    "user": "votre_nom_utilisateur",
    "password": "votre_mot_de_passe",
    "role": "MON_ROLE_ANALYST",
    "warehouse": "MON_WAREHOUSE",
    "database": "MA_BASE_DE_DONNEES",
    "schema": "MON_SCHEMA"
}

# 2. Création de la session Snowpark
try:
    session = Session.builder.configs(connection_parameters).create()
    print("Session Snowpark établie avec succès !")
    
    # Vous pouvez maintenant appeler votre fonction :
    # resultats = changement_bis_snowpark(session, klife, dict_moniteurs, ...)
    
finally:
    # Toujours fermer la session à la fin du script
    session.close()
