# On interroge AWS sur le statut de la tâche
reponse_statut = a2i.describe_human_loop(HumanLoopName="nom_de_votre_tache")

statut = reponse_statut["HumanLoopStatus"]
print(f"Statut actuel : {statut}")

if statut == "Completed":
    # Si c'est terminé, AWS nous donne le lien direct vers le fichier output.json
    chemin_resultat_s3 = reponse_statut["HumanLoopOutput"]["OutputS3Uri"]
    print(f"✅ Résultat disponible ici : {chemin_resultat_s3}")
    
    # Vous pouvez ensuite utiliser boto3 (s3.get_object) pour lire et traiter ce JSON !