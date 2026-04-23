from snowflake.snowpark import Session
import snowflake.snowpark.functions as F
from datetime import datetime, timedelta

def changement_bis_snowpark(session: Session, klife, dict_moniteurs, moni, date):
    # 1. Traitement local initial (Pandas)
    decaiss_pd = apply_filters(klife, dict_moniteurs, moni)
    decaiss_pd = decaiss_pd[decaiss_pd['is_stock'] == 0]
    
    # Sélection des colonnes minimales pour l'upload (1M de lignes)
    decaiss_pd = decaiss_pd[['ID_DECAISSEMENT', 'IBAN_POUR_VIREMENT', 'PERSNUM_CLIENT']]

    # 2. Envoi du DataFrame Pandas vers Snowflake (Table Temporaire)
    # Snowpark gère l'upload optimisé via un stage interne automatiquement
    df_decaiss = session.create_dataframe(decaiss_pd)

    # 3. Référence aux tables Snowflake (ne télécharge rien !)
    df_rib = session.table("TA_TABLE_RIB")
    df_comptes = session.table("TA_TABLE_COMPTES_BANCAIRES")

    # 4. Préparation de la date limite
    nb_month = dict_moniteurs[moni]['top']['nb_month']
    date_obj = datetime.strptime(date, '%Y%m%d')
    date_limite = date_obj - timedelta(days=30 * nb_month)

    # 5. Logique de jointure (Pushdown)
    # On fait un LEFT JOIN pour identifier ce qui manque (comme tes merge left_only)
    joined_df = df_decaiss.join(
        df_rib, 
        df_decaiss["IBAN_POUR_VIREMENT"] == df_rib["IBAN_COD"], 
        join_type="left"
    ).join(
        df_comptes,
        df_rib["BANQ_COMPTE_NUM"] == df_comptes["BANQ_COMPTE_NUM"],
        join_type="left"
    )

    # 6. Application des filtres de "Suspects"
    # On définit les conditions qui font qu'un enregistrement est suspect
    is_missing_iban = F.col("IBAN_COD").is_null()
    is_missing_account = F.col("BANQ_COMPTE_NUM").is_null()
    is_wrong_person = F.col("PERSNUM_CLIENT") != F.col("PERS_NUM")
    is_too_recent = F.col("MODIF_DAT_DERN") > F.lit(date_limite)

    suspects_df = joined_df.filter(
        is_missing_iban | is_missing_account | is_wrong_person | is_too_recent
    )

    # 7. Extraction du résultat final
    # On ne récupère que les IDs uniques
    suspects_list = suspects_df.select("ID_DECAISSEMENT").distinct().collect()

    # Transformation de la liste d'objets Row en liste Python simple
    return [row["ID_DECAISSEMENT"] for row in suspects_list]
