Avant de présenter les chiffres et les actions, voici quelques notions clés pour bien comprendre les décisions proposées.

1. Les classes de stockage S3 (rappel)
S3 propose plusieurs classes de stockage avec des tarifs différents selon la fréquence d'accès aux fichiers :

Standard ($0.023/GB) : pour les fichiers consultés régulièrement (notre situation actuelle)
Standard-IA ($0.0125/GB) : Infrequent Access — pour les fichiers consultés occasionnellement (-46%)
Glacier Instant Retrieval ($0.004/GB) : accès instantané mais tarif d'archive (-83%)
Glacier Flexible Retrieval ($0.0036/GB) : accès en quelques minutes à quelques heures
Glacier Deep Archive ($0.00099/GB) : la classe la moins chère (-96%), accès en 12h
Intelligent-Tiering : classe automatique qui déplace les fichiers entre tiers selon les accès
Plus la classe est froide, moins elle coûte cher en stockage, mais plus elle peut être lente ou coûteuse à récupérer.

2. Intelligent-Tiering (IT) — fonctionnement complet
Intelligent-Tiering est une classe automatique qui déplace les fichiers entre plusieurs tiers internes en se basant sur la date de dernière consultation du fichier (last access date).

Règles automatiques de transition :

Frequent Access : tier par défaut à l'entrée
Infrequent Access : si le fichier n'est pas accédé pendant 30 jours → déplacement automatique
Archive Instant Access : si pas d'accès pendant 90 jours → déplacement automatique (accès instantané conservé)
Archive Access (optionnel) : à activer manuellement, après 90 à 730 jours sans accès
Deep Archive Access (optionnel) : à activer manuellement, après 180 à 730 jours sans accès
Remontée automatique : dès qu'un fichier archivé est consulté, il remonte automatiquement en Frequent Access. Aucune intervention manuelle nécessaire.

Coût du monitoring : $0.0025 par 1000 objets/mois — c'est ce qui permet à S3 de tracker les accès. Ce coût est rentable pour les buckets avec peu d'objets, mais peut devenir prohibitif sur des buckets à plusieurs millions d'objets.

3. Les Lifecycle Rules — fonctionnement
Une Lifecycle Rule est une règle de transition qui s'exécute en fonction de l'âge du fichier (date de création ou de dernière modification), pas en fonction de la date de consultation.

Exemples de règles possibles :

"Déplacer tous les fichiers vers Glacier après 90 jours"
"Supprimer les anciennes versions après 365 jours"
"Supprimer les multipart uploads incomplets après 7 jours"
Différence clé avec Intelligent-Tiering :

Lifecycle = basée sur la date de création/modification (calendrier fixe, prévisible). Aucun coût de monitoring.
IT = basée sur la date de dernière consultation (dynamique, intelligent). Coût de monitoring proportionnel au nombre d'objets.
Lifecycle est idéal quand on connaît à l'avance le cycle de vie des fichiers (ex. logs, archives). IT est idéal quand on ne sait pas à l'avance quels fichiers sont chauds ou froids.
