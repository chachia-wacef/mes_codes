
Actions nécessaires avant l'intervention

Accès à l'application : Pour faire les tests, j’ai besoin d’accéder à l’application Themis sur les environnements de Production et de Recette. C’est un point bloquant qu’il faut régler avant de pouvoir lancer la migration.

Tests fonctionnels : Pour être sûr que tout fonctionne bien après la mise à jour, j’aimerais connaître les tests importants à effectuer. Pour cela, j’ai besoin qu’une personne de l’équipe métier me fasse une présentation rapide (un récapitulatif) des fonctionnalités clés de l'application.





Résumé technique des évolutions (MySQL 8.4 LTS)

Le passage à la version 8.4 apporte des changements structurels importants pour la performance et la sécurité :

Statut LTS (Long-Term Support) : Cette version garantit un support critique et des correctifs de sécurité pendant 8 ans (5 ans de support Premier + 3 ans de support Étendu), assurant la pérennité de l'infrastructure.

Sécurité et Authentification : Le plugin mysql_native_password est désormais désactivé par défaut au profit de caching_sha2_password. Cela renforce la sécurité des échanges entre l'application et la base.

Optimisation InnoDB :

Le paramètre innodb_buffer_pool_instances est désormais auto-dimensionné en fonction du hardware (CPU/RAM).

La taille par défaut de innodb_log_buffer_size passe à 64 Mo pour mieux gérer les écritures intensives.

Standardisation SQL :

Nettoyage définitif de la syntaxe de réplication (remplacement des termes MASTER/SLAVE par SOURCE/REPLICA).

Introduction de nouveaux mots-clés réservés (MANUAL, QUALIFY, TABLESAMPLE) pour une meilleure conformité aux standards SQL récents.

Maintenance simplifiée : Suppression d'outils obsolètes (mysqlpump, mysql_upgrade) au profit de processus de mise à jour intégrés directement au moteur au moment du démarrage.
