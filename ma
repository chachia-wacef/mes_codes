Plan de migration MySQL (v8.0 vers v8.4) – Validation et étapes d'intervention

Bonjour ANT,

Le plan de migration de notre base de données vers la version 8.4 est désormais finalisé et a été validé en collaboration avec Kader.

Afin de sécuriser l'opération et de minimiser les risques sur l'environnement de production, nous avons convenu d'une approche en deux temps : une phase de test complète sur l'environnement de Recette avant d'intervenir sur la Production. Cette étape intermédiaire est essentielle pour identifier et corriger d'éventuelles incompatibilités applicatives avant la bascule finale.

🛑 Point bloquant à résoudre
Pour mener à bien cette phase de test, j'ai besoin d'un accès à l'application en Recette. Actuellement, l'accès semble restreint par ADFS (qui ne serait plus utilisé d'après mes informations). Ce point est bloquant : nous devons impérativement rétablir cet accès avant de pouvoir initier la migration.

Une fois cet accès rétabli, l'intervention se déroulera selon les étapes suivantes :

====================

Objet : Plan de migration de la base de données (MySQL 8.0 vers 8.4)

Bonjour ANT,

Le plan pour migrer la base de données de la version 8.0 vers la version 8.4 est prêt. Il a été validé avec Kader.

Nous allons d'abord effectuer cette opération sur l'environnement de Recette (hors production). L'objectif est de détecter d'éventuels problèmes imprévus pour réduire les risques et éviter les mauvaises surprises lors de la migration finale sur la production.

Point bloquant à résoudre :
Pour réaliser ces tests, j’ai besoin d'accéder à l’application sur l’environnement de Recette. Actuellement, l’accès est limité par ADFS, mais si j’ai bien compris, cet outil n’est plus utilisé. C’est un point bloquant qu’il faut résoudre avant de pouvoir lancer la migration.

L'intervention se déroulera selon les étapes suivantes :
