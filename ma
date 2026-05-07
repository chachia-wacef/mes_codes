Objet : Plan de migration de la base de données MySQL (v8.0 vers v8.4)
Voici les étapes détaillées de l'intervention pour garantir une transition fluide et sécurisée :

1. Sécurisation et Prérequis
Snapshot manuel : Avant toute opération, nous réaliserons un snapshot (instantané) complet de la base de données. C'est notre filet de sécurité ultime permettant une restauration totale en cas d'imprévu majeur.

Configuration (Parameter Group) : L'instance actuelle utilise les paramètres par défaut (default.mysql8.0). Pour la nouvelle version, AWS appliquera automatiquement la configuration standard default.mysql8.4, garantissant ainsi une compatibilité optimale avec le moteur.

2. Déploiement "Blue/Green"
Nous utilisons la méthode Blue/Green Deployment pour éviter toute interruption de service prolongée :

AWS crée un environnement miroir (Green) avec la version 8.4.

Pendant cette phase, les données sont synchronisées en temps réel depuis l'instance de production actuelle (Blue).

Impact : Le site reste 100% fonctionnel et disponible durant toute la préparation du clone.

3. Phase de Validation et Tests
Avant la bascule définitive, nous procéderons à des vérifications sur l'instance Green via son endpoint temporaire :

Vérification de la connectivité applicative.

Tests de compatibilité des requêtes SQL (notamment sur les colonnes utilisant des mots réservés comme index).

Validation des performances globales sur le nouveau moteur.

4. Bascule (Switchover)
Une fois les tests validés, nous déclencherons la bascule :

L'instance Green devient l'instance de Production.

Elle récupère automatiquement l'endpoint final utilisé par l'application.

Impact : Une coupure de connexion très brève (quelques secondes à une minute) est à prévoir pendant que AWS redirige le trafic DNS.

5. Stratégie de Retour en Arrière (Rollback)
Pour garantir une sécurité maximale après la migration :

Maintien de l'ancienne instance : L'ancienne base (v8.0) restera active sous un endpoint secondaire. Nous la conserverons durant 48 heures. En cas de bug critique détecté après la migration, nous pourrons rediriger l'application vers cette instance quasi instantanément.

Nettoyage : Passé ce délai de 2 jours, l'ancienne instance sera supprimée pour optimiser les coûts.

Note sur les données : En cas de restauration via le Snapshot initial (plus de 48h après), veuillez noter que les données enregistrées entre le début de l'opération et le moment de la restauration ne seraient pas incluses. C'est pourquoi le maintien de l'ancienne instance pendant 48h est notre priorité pour un rollback sans perte.

Points clés à retenir :
Downtime minimal : Moins d'une minute lors du switchover.

Sécurité : L'ancienne base reste disponible en secours immédiat.

Transparence : Aucun changement de configuration requis dans le code de l'application après la bascule.
