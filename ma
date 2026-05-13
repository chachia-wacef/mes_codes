
aws s3api list-object-versions --bucket NOM_DE_VOTRE_BUCKET --prefix nom-du-dossier/ --query 'length(Versions[?IsLatest==`false` || DeleteMarkers])' --output text
