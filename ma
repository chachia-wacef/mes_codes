
aws s3api list-object-versions --bucket NOM_DE_VOTRE_BUCKET --prefix nom-du-dossier/ --query 'length(Versions[?IsLatest==`false` || DeleteMarkers])' --output text

aws s3api list-object-versions --bucket NOM_DE_VOTRE_BUCKET --prefix nom-du-dossier/ --query "Versions[?IsLatest=='false'].Size" --output text | awk '{for(i=1;i<=NF;i++) s+=$i} END {print s/1024/1024/1024 " Go"}'
