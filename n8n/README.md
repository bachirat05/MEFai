# Cortex AI — n8n Workflows

Ce dossier contient les workflows n8n utilisés par Cortex AI pour automatiser la gestion des demandes de congé.

## Workflows

### `cortex_leave_submission.json`

Ce workflow est déclenché lors de la création d'une nouvelle demande de congé.

Flux principal :

```text
Cortex AI Backend
        ↓
Webhook n8n
        ↓
Validation des données
        ↓
Vérification du statut
        ↓
Envoi d'un email au manager
        ↓
Réponse au backend
```

Il permet de :

- valider les informations de la demande ;
- générer une référence de demande ;
- notifier le manager par email ;
- retourner le résultat au backend Cortex AI.

### `cortex_leave_decision_notification.json`

Ce workflow est déclenché après la décision du manager.

Flux principal :

```text
Manager
   ↓
Cortex AI Backend
   ↓
Webhook n8n
   ↓
Vérification du statut
   ├── accepted
   └── rejected
        ↓
Envoi d'un email à l'employé
        ↓
Réponse au backend
```

Le contenu de l'email est adapté selon le statut de la demande :

- `accepted` : demande acceptée ;
- `rejected` : demande refusée.

## Import dans n8n

1. Ouvrir n8n.
2. Aller dans **Workflows**.
3. Choisir **Import from File**.
4. Sélectionner le fichier JSON.
5. Configurer les credentials SMTP.
6. Vérifier les Webhooks.
7. Tester le workflow.
8. Activer le workflow après validation.

## Configuration SMTP

Les credentials SMTP ne sont pas stockés dans ce dépôt.

Après l'import du workflow, chaque développeur doit configurer ses propres credentials SMTP dans n8n.

Il faut également remplacer l'adresse d'expéditeur générique :

```text
your-smtp-sender@example.com
```

par l'adresse utilisée dans l'environnement local.

## Sécurité

Ne jamais publier dans GitHub :

- mots de passe SMTP ;
- API keys ;
- tokens ;
- secrets n8n ;
- credentials Firebase ;
- fichiers `.env`.

Les fichiers JSON présents dans ce dossier contiennent uniquement la structure et la logique des workflows nécessaires au projet.

## Structure du dossier

```text
n8n/
├── README.md
├── cortex_leave_submission.json
└── cortex_leave_decision_notification.json
```