
mysqldump -h <rds-prod> -u admin -p \
  --single-transaction \
  --add-drop-table \           # ⭐ DROP TABLE IF EXISTS avant chaque CREATE
  --routines --triggers --events \
  --set-gtid-purged=OFF \
  --no-tablespaces \
  mydb | gzip > dump.sql.gz

///////////// ou en ignorant quelques tables

mysqldump -h <rds-prod> -u admin -p \
  --single-transaction \
  --add-drop-table \
  --routines --triggers --events \
  --set-gtid-purged=OFF \
  --no-tablespaces \
  --ignore-table=mydb.audit_logs \
  --ignore-table=mydb.event_history \
  mydb | gzip > dump.sql.gz


====Aprés sur l'en hors prod

gunzip -c dump.sql.gz | mysql -h <rds-horsprod> -u admin -p mydb
✅ Tables recréées avec structure prod identique
✅ Données remplacées
✅ Pas de conflits de PK/contraintes


