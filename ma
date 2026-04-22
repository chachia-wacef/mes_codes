
Bonjour Antoine,

Merci pour tes réponses. Voici un point sur l'avancement suite à tes retours :

1. Logique des IBAN
C'est très clair. Je vais donc considérer tout IBAN absent de la table RIB comme étant suspect.

2. Utilisation de NUM_CT (Moniteur M18a)
Pour le moment, la version actuelle du code fait la jointure uniquement via le numéro de personne (PERS_NUM). La colonne NUM_CT n'est pas utilisée dans le moniteur M18a pour deux raisons :

Différence de format : Comme tu peux le voir sur les captures ci-dessous, les formats dans le fichier KLIFE et dans la table LALDT006 ne correspondent pas.

Résultat des tests : J'ai lancé une requête pour isoler les lignes où NUM_CT ne contient que des chiffres dans la table LALDT006, et le résultat est vide.

3. Évolution technique (Python / Snowflake)
Concernant les tables de référentiel : Anthony est en train de vérifier si nous pouvons passer à une version de Python plus récente (supérieure à la 3.8). Si c'est possible, cela résoudrait notre problème de bibliothèque et nous pourrions interroger les tables directement sans passer par des exports manuels.

Je te tiens informé de la suite.

Bien cordialement,

Wacef
