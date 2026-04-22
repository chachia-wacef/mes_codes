import pandas as pd
import numpy as np

# 1. Joindre df_klife avec df_RIB
# On utilise how='left' pour garder toutes les lignes de klife
df_result = pd.merge(
    df_klife, 
    df_RIB[['IBAN_COD', 'BANQ_COMPTE_NUM', 'NB_CHANGES']], 
    left_on='IBAN', 
    right_on='IBAN_COD', 
    how='left'
)

# 2. Joindre avec df_compte
# On utilise des suffixes pour différencier les NUM_PERS des deux tables
df_result = pd.merge(
    df_result, 
    df_compte[['BANQ_COMPTE_NUM', 'NUM_PERS']], 
    on='BANQ_COMPTE_NUM', 
    how='left', 
    suffixes=('', '_compte')
)

# 3. Définition des conditions de suspicion
# Condition A : L'IBAN n'existe pas dans df_RIB
cond_a = df_result['IBAN_COD'].isna()

# Condition B : Le compte n'existe pas dans df_compte
cond_b = df_result['NUM_PERS_compte'].isna()

# Condition C : Le NUM_PERS ne match pas entre klife et compte
cond_c = df_result['NUM_PERS'] != df_result['NUM_PERS_compte']

# Condition D : NB_CHANGES n'est pas égal à 0
cond_d = df_result['NB_CHANGES'] != 0

# 4. Marquage final
# Une ligne est suspecte si A est vrai OR (si non A, alors B ou C ou D)
# En fait, selon ta logique, c'est un simple OR de toutes les erreurs possibles
df_result['IS_SUSPECT'] = cond_a | cond_b | cond_c | cond_d

# Optionnel : On peut même préciser la raison pour faciliter ton audit
df_result['RAISON'] = np.select(
    [cond_a, cond_b, cond_c, cond_d],
    ['IBAN absent RIB', 'Compte absent table compte', 'NUM_PERS mismatch', 'NB_CHANGES > 0'],
    default='OK'
)


## Étape 1 : Pousser le dataframe decaiss sur Snowflake
# Plutôt que d'importer Snowflake vers Pandas, on va exporter decaiss vers une table temporaire Snowflake. Les tables temporaires sont parfaites pour ça : elles sont rapides, n'encombrent pas la base de données et disparaissent automatiquement à la fin de la session.


from snowflake.connector.pandas_tools import write_pandas
from datetime import datetime, timedelta

def changement_bis(klife, dict_moniteurs, moni, date, bucket, filepath, prefixes, snowflake_conn):
    # 1. Traitement initial de decaiss (inchangé)
    decaiss = apply_filters(klife, dict_moniteurs, moni)
    decaiss = decaiss[decaiss['is_stock'] == 0]
    
    # 2. Création d'une table temporaire dans Snowflake avec les données de decaiss
    # On s'assure d'avoir que les colonnes nécessaires pour alléger l'envoi
    df_to_upload = decaiss[['ID_DECAISSEMENT', 'IBAN_POUR_VIREMENT', 'PERSNUM_CLIENT']]
    
    snowflake_conn.cursor().execute(
        "CREATE TEMPORARY TABLE temp_decaiss (ID_DECAISSEMENT VARCHAR, IBAN_POUR_VIREMENT VARCHAR, PERSNUM_CLIENT VARCHAR)"
    )
    
    # Écriture rapide du dataframe dans la table temporaire
    success, nchunks, nrows, _ = write_pandas(snowflake_conn, df_to_upload, 'TEMP_DECAISS')


## Étape 2 : La Requête SQL Magique
# Maintenant que tes données à analyser sont sur Snowflake, tu peux exécuter une requête qui fait exactement tes merges Pandas et tes calculs de date, puis récupérer uniquement la liste finale.

# 3. Préparation des variables
    nb_month = dict_moniteurs[moni]['top']['nb_month']
    date_obj = datetime.strptime(date, '%Y%m%d')
    date_limite = (date_obj - timedelta(days=30*nb_month)).strftime('%Y-%m-%d')

    # 4. Exécution de la jointure et des filtres côté Snowflake
    query = f"""
    SELECT DISTINCT d.ID_DECAISSEMENT
    FROM temp_decaiss d
    
    -- Premier Merge (Pandas: decaiss avec df_RIB)
    LEFT JOIN TA_TABLE_RIB r 
           ON d.IBAN_POUR_VIREMENT = r.IBAN_COD
           
    -- Deuxième Merge (Pandas: decaiss avec df_Comptes_Bancaires)
    LEFT JOIN TA_TABLE_COMPTES_BANCAIRES cb 
           ON r.BANQ_COMPTE_NUM = cb.BANQ_COMPTE_NUM
           
    WHERE 
       -- Condition 1 : IBAN non trouvé dans df_RIB (Pandas: _merge == left_only)
       r.IBAN_COD IS NULL 
       
       -- Condition 2 : Compte non trouvé (Pandas: _merge == left_only au 2eme merge)
       OR cb.BANQ_COMPTE_NUM IS NULL 
       
       -- Condition 3 : PERSNUM_CLIENT différent de PERS_NUM (Pandas: ~same_pers_num)
       OR d.PERSNUM_CLIENT != cb.PERS_NUM 
       
       -- Condition 4 : Modification trop récente (Pandas: ~old_modification)
       OR r.MODIF_DAT_DERN > '{date_limite}'::DATE
    """
    
    # 5. Récupération directe de la liste finale
    cursor = snowflake_conn.cursor()
    cursor.execute(query)
    
    # Extraction des résultats sous forme de liste native Python
    suspects_list = [row[0] for row in cursor.fetchall()]
    
    return suspects_list
    

