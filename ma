Objet : Questions sur le projet FraudDecaissement

Bonjour Antoine,

Comme discuté hier avec l’équipe DS, je t'envoie une liste de points à clarifier pour avancer sur le projet FraudDecaissement :

1. Concernant les IBAN (Table RIB LALDT005)

Selon Sami, si un IBAN n’est pas dans cette table, cela veut dire qu’il n’a pas été modifié et qu’il n’est donc pas suspect. Es-tu d'accord avec cette logique ? Aussi, sais-tu qui peut nous confirmer que cette table ne contient que les modifications ?

Si l'IBAN est présent dans la table, est-ce qu'on peut vérifier en priorité si la date de modification (MODIF_DAT_DERN) date de moins de 3 mois ?

2. Concernant le numéro de contrat (NUM_CT)

Le format de NUM_CT est différent entre le fichier KLIFE et la table LALDT006. S’agit-il bien de la même information ?

Actuellement, il est impossible d'utiliser le "Numéro de Contrat" pour les contrôles à cause de cette différence de format.

Si nous réglons ce problème de format, est-ce qu'on doit vérifier que les valeurs sont identiques entre les deux fichiers ? (Pour rappel, cette table avait été retirée de ma proposition initiale).

3. Problème technique (Snowflake / S3)

La bibliothèque officielle Snowflake ne fonctionne plus avec nos versions de Python (3.7 et 3.8). Avec Bechir, nous pensons qu'il faut copier les tables manuellement sur S3. Qui pourrait s'occuper de cela ?

Merci d'avance pour ton aide.

Bien cordialement,

Wacef
