
Bonjour à toutes et à tous,

J'espère que vous allez bien.

Suite à l'incident du 9 février concernant le moniteur M18a, nous avons finalisé la mise en place du nouveau moniteur M18_bis. Conformément à l'approche validée dans nos échanges du 20 mars, ce moniteur s'appuie désormais directement sur les tables répliquées de RUBIS, et non plus sur une extraction.

Cependant, nous constatons que cette nouvelle méthode génère un volume de cas suspects nettement supérieur à l'ancienne.

Afin que vous puissiez comparer les données et nous faire un retour sur la pertinence de ces alertes, nous vous avons préparé un export des résultats de ce moniteur sur 5 jours ouvrés (du 21 au 27 avril).

Vous trouverez en pièce jointe les fichiers CSV correspondants (suspects_detail_df_YYYYMMDD.csv). Note : ces fichiers contiennent uniquement les résultats de ce moniteur.

🔍 Rappel de la règle métier (Critères de suspicion)
Pour rappel, une alerte est levée lorsque les deux conditions suivantes sont réunies :

Condition 1 : Les moyens de communication OU le nom ont été modifiés dans les 3 derniers mois.
ET

Condition 2 : Présence d'une anomalie bancaire parmi les suivantes :

RIB inconnu

OU Numéro de compte bancaire inconnu

OU La personne associée au compte bancaire est différente de celle effectuant le décaissement

OU Un changement de RIB a été détecté dans les 3 derniers mois.

📊 Guide de lecture du fichier
Pour faciliter votre analyse, le fichier contient les données brutes ainsi que des colonnes de "diagnostic" (affichant True ou False) :

Identifiants et données de base :

ID_DECAISSEMENT : Identifiant unique du décaissement.

IBAN_POUR_VIREMENT : IBAN du décaissement trouvé dans KLIFE.

BANQ_COMPTE_NUM_RIB_005 : N° de compte bancaire affecté à l'IBAN dans la table RIB LALDT005.

BANQ_COMPTE_NUM_CB_004 : N° de compte bancaire retrouvé dans la table RIB LALDT005 (Null si non trouvé).

IBAN_COD_RIB_005 : IBAN du fichier KLIFE (Null si non trouvé).

PERS_NUM_CB_004 : Numéro client retrouvé dans KLIFE (Null si non trouvé).

PERSNUM_CLIENT_KLIFE : Numéro client rattaché au décaissement dans KLIFE.

MODIF_DAT_DERN : Date de la dernière modification du RIB (Null si le RIB n'est pas trouvé dans la table LALDT005).

Diagnostics (Raisons de l'alerte) :

RIB_INCONNU : True si le RIB du décaissement (KLIFE) n'a pas été trouvé dans la table LALDT005.

COMPTE_NUM_OU_PERSNUM_INVALIDE : True si le compte n'a pas été trouvé dans la table LALDT004, OU si le client associé à ce compte ne correspond pas à celui de KLIFE.

MODIF_RECENTE : True si le couple (Compte, Client) a bien été trouvé, mais que la dernière date de modification du RIB a eu lieu dans les 3 derniers mois.

RECENT_MODIF_COMNIC : True si les moyens de communication ont été changés dans les 3 derniers mois.

RECENT_MODIF_NOM : True si le nom a été changé dans les 3 derniers mois.

Nous restons à votre disposition si vous avez besoin d'aide pour analyser ces écarts.

Merci d'avance pour vos retours,
