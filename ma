Objet : [Optimisation] Projet Doublons : Réduction majeure du temps de géocodage

Bonjour à tous,

J'espère que vous allez bien.

Je vous informe que j'ai finalisé l'optimisation de la partie géocodage des adresses au sein du projet "Doublons".

Le problème identifié :
Auparavant, le script renvoyait l'intégralité des adresses à l'API chaque semaine, sans exploiter l'historique des données déjà traitées. Cela représentait environ 1,8 million de lignes pour un temps d'exécution de 2h30 (voir capture 1).

La solution apportée :
La nouvelle version du code intègre désormais une gestion de l'historique. Après plusieurs tests concluants en environnement de Recette, le volume à traiter est passé de 998 726 à 11 581 lignes lors de la dernière exécution.

Résultats :

Temps d'exécution : Passage de 2 heures à 8 minutes.

Fiabilité : Le système continue de soumettre les adresses ayant retourné des valeurs nulles précédemment, afin de pallier les instabilités ponctuelles de l'API.

Le code est testé et prêt pour un déploiement en production.

Je reste à votre disposition pour toute précision.

Bien cordialement,

/////////////////////////////////////

Bonjour Antoine,

J'espère que tu vas bien.

Je te confirme que le plan de migration de la base de données est désormais prêt et a été validé avec Kader.

Déroulement de l'intervention :
L'opération se déroulera selon les trois étapes suivantes :

Sauvegarde : Réalisation d'un snapshot complet de la base de données avant toute modification.

Migration : Changement du type de stockage et configuration du lancement de la migration.

Validation et Nettoyage : Après quelques jours d'observation, nous procéderons à la suppression du snapshot si le système est parfaitement stable.

Planning proposé :
Nous avons la possibilité de lancer cette migration soit immédiatement, soit durant la fenêtre de maintenance hebdomadaire (chaque mardi à 23h30 pour une durée de 30 minutes).

Afin de garantir la continuité de service, nous proposons de planifier cette migration demain soir, mardi, durant la fenêtre de maintenance.

N'hésite pas à me solliciter si tu as des questions ou des ajustements à suggérer.

Bien cordialement,

