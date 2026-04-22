
Je reviens vers toi concernant le cas de fraude du 9 février dernier. Voici les points bloquants que j'ai identifiés dans les fichiers de données :

1. Problème de présence de l'IBAN et données manquantes

L'IBAN utilisé pour le virement est absent du fichier du 9 février (MVS_RUBIS_J_20260209).

Il n'apparaît que dans le fichier du lendemain (10 février), avec une date de modification au 09/02.

Sur cette ligne, les colonnes NUM_CT et PERS_NUM sont vides. C'est probablement un problème de jointure qui devrait être résolu avec notre nouvelle approche (interrogation directe des tables).

2. Absence du numéro de personne (PERS_NUM)

Le PERS_NUM associé à cette fraude est introuvable dans les fichiers des 9, 10 et 11 février. Il est totalement absent de la source sur cette période.

3. Anomalie sur la fraîcheur des données

J'ai remarqué une incohérence sur le fichier du lundi 9 février : il ne contient des données que jusqu'au 7 février (décalage de 2 jours).

Pourtant, les autres fichiers (10 et 11 février) sont bien à jour. À titre de comparaison, le lundi 1er février contenait bien les données du jour même. Il semble donc y avoir eu un problème spécifique de mise à jour le 9 février.

Ces éléments expliquent pourquoi la fraude n'a pas pu être détectée par le moniteur à cette date.

Bien cordialement,

Wacef
