Objet : Optimisation des coûts S3 — Analyse et plan d'action pour pfidata & pfedata

Bonjour,

Suite à l'analyse de notre consommation AWS S3, je vous présente un plan d'action pour réduire significativement nos coûts sur les 2 buckets principaux qui représentent ~458$/mois sur une facture globale de 550$/mois.

1. État actuel
Bucket pfidata

Taille totale : 14 TB (314 000 objets)
Versions actuelles : ~11.3 TB
Anciennes versions : 2.7 TB — coût : 62$/mois
100% en classe Standard
Coût mensuel estimé : ~322$/mois
Bucket pfedata

Taille totale : 5.9 TB (35 millions d'objets)
Versions actuelles : seulement ~1.2 TB
Anciennes versions : 4.7 TB (79% du bucket !) — coût : 108$/mois
100% en classe Standard
Coût mensuel estimé : ~136$/mois
2. Problèmes identifiés
Anciennes versions non gérées (le plus critique)

Le versioning est activé sur les 2 buckets : chaque modification crée une nouvelle version conservée indéfiniment au tarif Standard
Total gaspillé : 170$/mois uniquement sur les anciennes versions
Versions actuelles toutes en Standard

Les fichiers non consultés depuis des mois restent facturés au tarif le plus cher
Des classes moins chères existent pour les fichiers froids
Multipart uploads incomplets

1 GB de morceaux de fichiers fantômes sur chaque bucket — invisibles mais facturés
3. Actions recommandées
pfidata — 3 actions

Nettoyage : supprimer les multipart uploads incomplets après 7 jours et les delete markers expirés
Anciennes versions : transition vers Glacier Instant Retrieval après 30 jours, puis Glacier Deep Archive après 90 jours, suppression définitive après 365 jours avec conservation de 2 versions max
Versions actuelles : activation d'Intelligent-Tiering (IT) — S3 déplace automatiquement les fichiers selon les accès réels vers des classes moins chères. Coût monitoring : seulement 0.79$/mois pour 314K objets, très rentable
pfedata — 3 actions

Nettoyage : même règle que pfidata
Anciennes versions : transition directe vers Glacier Deep Archive (retain 2 versions), suppression définitive après 365 jours
Versions actuelles : transition vers Glacier Instant Retrieval après 60 jours d'inactivité. Glacier IR = accès instantané, aucun impact sur les dashboards et applications
Pourquoi pas IT sur pfedata ? 35M d'objets = 87.50$/mois de monitoring, pour seulement 1.2 TB de versions actuelles. Le coût de monitoring dépasserait les économies générées.

4. Projections financières
Avant activation

Total 2 buckets : 458$/mois
Mois 1 (J+30)

Noncurrent versions migrées en Glacier → gain immédiat de ~163$
Total estimé : ~295$/mois
Mois 2 (J+60)

IT pfidata commence à déplacer les fichiers froids + Glacier IR activé sur pfedata
Total estimé : ~235$/mois
Mois 3+ (état stable)

IT pfidata à maturité (30% Frequent / 35% Infrequent / 35% Archive)
Total estimé : ~155$/mois
Économie mensuelle stable : ~$300/mois (-65%)

5. Risques et précautions
Suppression accidentelle : retention de 2 versions + délai 365j avant suppression définitive
Fichier archivé encore utilisé : Glacier IR = accès instantané, transparent pour les apps
Impact dashboards pfedata : Glacier IR = même latence que Standard, aucun impact
6. Décisions attendues
Rétention des anciennes versions : 2 versions max + suppression après 365 jours — est-ce suffisant pour les besoins de rollback de chaque équipe ?
Délai d'archivage pfedata : 60 jours sans accès → Glacier IR — est-ce cohérent avec les cycles d'utilisation des outputs ?
Validation IT sur pfidata : les équipes sont-elles d'accord avec une transition automatique selon les accès réels ?
7. Prochaines étapes (si validation)
Configuration lifecycle nettoyage + anciennes versions sur les 2 buckets — 30 min
Activation Intelligent-Tiering sur pfidata — 30 min
Configuration lifecycle versions actuelles sur pfedata — 30 min
Vérification via Cost Explorer à J+30
Mise en œuvre possible dès cette semaine, aucune interruption de service prévue.

Je reste disponible pour répondre à vos questions ou ajuster les paramètres selon les contraintes de chaque équipe.

Cordialement,
