# MEFai — Assistant RH Intelligent

MEFai est une plateforme RH intelligente développée comme preuve de concept (PoC) professionnelle pour le contexte du Ministère de l'Économie et des Finances du Maroc. Elle combine assistant conversationnel, IA locale, RAG, workflows métier, authentification, contrôle d'accès et administration.

## Stack technique

| Domaine | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS |
| Backend | Python, FastAPI, Pydantic, httpx |
| Identité et autorisations | Firebase Authentication, Firebase Admin SDK, Firebase Custom Claims (RBAC) |
| Agent IA | LangGraph ReAct, LangChain, MCP |
| Modèle et embeddings | Ollama, Qwen3:8b, nomic-embed-text |
| Recherche documentaire | ChromaDB, RAG, ingestion TXT/PDF/DOCX |
| Données métier | SQLite |
| Automatisation | n8n |
| Qualité | pytest, build et lint frontend |

## Fonctionnalités

- Chat RH intelligent fondé sur les documents internes, avec sources et catégories.
- Ingestion documentaire `.txt`, `.pdf` et `.docx`, recherche sémantique et réponses RAG.
- Authentification Firebase et RBAC : `employee`, `manager`, `admin`.
- Demandes de congé, historique et suivi des statuts.
- Validation ou refus par un manager, persistance SQLite et notifications email via n8n.
- Administration, consultation des documents et suivi du statut des services.
- Journaux d'activité et d'audit : se reporter à l'état d'implémentation dans le résumé technique ci-dessous.
- Tests backend automatisés.

## Installation et démarrage

### 1. Cloner le dépôt

```bash
git clone <URL_DU_REPOSITORY>
cd Cortex_AI_Minist-re
git fetch origin
git switch zouhair
git pull
```

La branche de développement indiquée dans la documentation fournie est `zouhair`.

### 2. Environnement Python

Sous Windows PowerShell, depuis la racine du dépôt :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Configuration FastAPI

Créer le fichier d'environnement à partir de l'exemple :

```powershell
Copy-Item .env.example Backend\.env
```

Exemple de paramètres à adapter à votre environnement :

```dotenv
OPENROUTER_API_KEY=
OPENROUTER_MODEL=poolside/laguna-s-2.1:free
LLM_BASE_URL=https://openrouter.ai/api/v1

OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_BASE_URL=http://localhost:11434

CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION_NAME=rh_documents

N8N_WEBHOOK_URL=http://localhost:5678/webhook/conge-test
N8N_SECRET_TOKEN=
N8N_TIMEOUT_SECONDS=15
N8N_STATUS_NOTIFICATION_WEBHOOK_URL=http://localhost:5678/webhook/notification-statut-conge

SERVER_PORT=8000
```

**Attention :** la documentation décrit principalement Qwen3:8b exécuté localement par Ollama. Les variables OpenRouter sont conservées comme configuration mentionnée dans le premier document ; leur utilisation effective dépend du code et de la configuration de la branche utilisée.

### 4. Firebase Admin

Le backend attend un compte de service Firebase au chemin :

```text
Backend/firebase_admin_key.json
```

Récupérer ce fichier par un canal sécurisé auprès d'une personne autorisée. Ne jamais le publier dans le dépôt.

### 5. Installer et préparer Ollama

```bash
ollama pull qwen3:8b
ollama pull nomic-embed-text
ollama list
```

Si le service n'est pas déjà actif :

```powershell
ollama serve
```

URL locale habituelle : `http://localhost:11434`.

### 6. Lancer le backend

Depuis la racine du projet, avec l'environnement virtuel activé :

```powershell
python -m uvicorn app.main:app --app-dir Backend --host 127.0.0.1 --port 8000
```

- API : http://127.0.0.1:8000
- Documentation Swagger : http://127.0.0.1:8000/docs

### 7. Lancer le frontend

Dans un deuxième terminal :

```powershell
cd Frontend
npm install
npm run dev
```

URL Vite habituelle : http://localhost:5173.

**Note :** les documents historiques mentionnent aussi `frontend/` en minuscules. Vérifier la casse exacte du dossier dans la branche clonée.

### 8. Configurer n8n

Démarrer n8n séparément et publier les workflows nécessaires. Renseigner les URLs de webhook et les secrets dans `Backend/.env`.

- Soumission : `/webhook/conge-test`
- Notification du statut : `/webhook/notification-statut-conge`

Les URLs `/webhook-test/...` servent aux essais interactifs ; les workflows publiés utilisent `/webhook/...`.

## RAG et documents

- Répertoire d'ingestion : `Backend/data/documents/`.
- Formats pris en charge : TXT, PDF et DOCX.
- Collection ChromaDB : `rh_documents`.
- Modèle d'embeddings : `nomic-embed-text` via Ollama.

La documentation technique décrit le découpage en chunks, les métadonnées, la recherche et les corrections apportées au grounding. Les documents de démonstration ne sont **pas** des politiques officielles du Ministère.

## Tests et validation

Depuis la racine du projet :

```powershell
pytest Backend/tests
```

Le premier document indique un état de référence de **84 tests réussis** ; le résumé historique contient également des résultats antérieurs, notamment **10 passed, 1 warning**. Ces résultats correspondent à des états documentés différents et n'ont pas été réexécutés lors de cette fusion.

Pour le frontend :

```powershell
cd Frontend
npm run build
npm run lint
```

## Accès selon les rôles

| Rôle | Espaces principaux |
|---|---|
| Employee | Chat IA, demande de congé, mes demandes, paramètres |
| Manager | Espaces Employee + espace Manager |
| Admin | Espaces Manager + administration, documents, audit logs (selon l'état de déploiement) |

Les contrôles d'accès doivent être appliqués côté backend, pas seulement dans la navigation React.

## Architecture fonctionnelle

```text
Utilisateur
  ↓
React / TypeScript
  ↓
Firebase Authentication (ID Token)
  ↓
FastAPI (validation token / RBAC)
  ├── Chat → LangGraph ReAct → MCP → RAG / ChromaDB → Ollama / Qwen3:8b
  ├── Congés → SQLite → n8n → Manager → décision → notification
  └── Administration / Documents / Statuts / Journaux
```

### Workflow de congé

```text
Employé → React → FastAPI → n8n (soumission + email manager)
                         ↓
                   SQLite : pending
                         ↓
               Manager : accepted / rejected
                         ↓
                  SQLite + n8n (notification)
                         ↓
                        Employé
```

## Sécurité

Ne jamais committer ni exposer :

```gitignore
.env
Backend/.env
firebase_admin_key.json
*.db
chroma_db/
.venv/
node_modules/
```

Ne jamais divulguer mots de passe, tokens Firebase, clés de comptes de service, secrets n8n, en-têtes `Authorization` ni données RH sensibles. Les webhooks, permissions documentaires et mécanismes d'audit doivent être durcis et vérifiés avant toute mise en production.

## Structure indicative

```text
Cortex_AI_Minist-re/
├── Backend/
│   ├── app/
│   ├── api/                  (selon la branche)
│   ├── core/                 (selon la branche)
│   ├── data/documents/
│   ├── services/             (selon la branche)
│   └── tests/
├── Frontend/
│   ├── src/
│   └── public/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

La structure exacte dépend de la branche et des refactorisations successives décrites ci-dessous.

## État et évolutions prévues

Le projet est documenté comme un PoC avancé. Les pistes mentionnées incluent le durcissement des webhooks, Docker / Docker Compose, CI/CD, monitoring, gestion avancée des rôles et utilisateurs et permissions fines sur les documents RAG. Certaines fonctionnalités ont évolué au fil du résumé historique ; consulter les sections les plus récentes pour leur état.

---

# Documentation technique détaillée et historique du projet

Cette seconde partie conserve **intégralement** le résumé technique fourni, avec ses architectures, validations, changements et états successifs. Les sections anciennes peuvent décrire des fonctionnalités encore prévues qui ont ensuite été implémentées ; les mises à jour les plus récentes prévalent pour le suivi historique. Le contenu n'a pas été vérifié contre le dépôt Git.

# MEFai — Résumé du projet

## 1. Présentation

**MEFai** est un assistant conversationnel intelligent orienté RH, destiné au contexte du **Ministère de l'Économie et des Finances du Maroc**.

Le projet combine une interface web React, l'authentification Firebase, une API FastAPI sécurisée, un agent LangGraph ReAct, un LLM local **Qwen3:8b** exécuté avec Ollama, un pipeline **RAG** basé sur ChromaDB et des outils métier exposés via **MCP**.

L'objectif est de permettre aux utilisateurs de poser des questions RH et d'obtenir des réponses basées sur les documents internes, tout en préparant une architecture sécurisée avec gestion des rôles, permissions, alertes et workflows métier.

---

## 2. Architecture actuelle

```text
                         ┌──────────────────────┐
                         │       Utilisateur    │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ React + TypeScript   │
                         │ Tailwind CSS         │
                         └──────────┬───────────┘
                                    │
                           Firebase Authentication
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │   Firebase Auth      │
                         │ Email / Password     │
                         └──────────┬───────────┘
                                    │
                              Firebase ID Token
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │       FastAPI        │
                         │ Authentication/RBAC  │
                         └───────┬──────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
              /api/chat                   /mcp
                    │                         │
                    ▼                         ▼
             ChatService                MCP Server
                    │                    SSE / Messages
                    ▼                         │
           LangGraph ReAct                    │
                    │                         │
                    ▼                         │
             Qwen3:8b                        │
              via Ollama                     │
                    │                         │
                    └──────────┬──────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    MCP Tools         │
                    ├──────────────────────┤
                    │ search_documents     │
                    │ soumettre_demande... │
                    └──────────┬───────────┘
                               │
                    ┌──────────┴──────────┐
                    ▼                     ▼
                  RAG                    n8n
                    │               Workflow métier
                    ▼
                ChromaDB
                    │
                    ▼
          nomic-embed-text
             via Ollama
```

---

## 3. Fonctionnement du chatbot

### Flux général

```text
Utilisateur
    ↓
React
    ↓
Firebase Authentication
    ↓
Firebase ID Token
    ↓
FastAPI
    ↓
Vérification du token
    ↓
ChatService
    ↓
LangGraph ReAct
    ↓
Décision : utiliser un outil
    ↓
MCP
    ↓
search_documents
    ↓
RAGService
    ↓
ChromaDB
    ↓
Résultats documentaires
    ↓
Qwen3:8b
    ↓
Réponse finale + source
    ↓
React
```

Pour une question RH nécessitant des informations internes, l'agent utilise `search_documents` afin de récupérer les passages pertinents avant de générer la réponse.

---

## 4. RAG — Retrieval-Augmented Generation

Le système utilise une architecture RAG pour éviter de faire reposer les réponses RH uniquement sur les connaissances générales du modèle.

### Pipeline documentaire

```text
Documents internes
       ↓
Chargement / préparation
       ↓
Découpage en chunks
       ↓
Embeddings
       ↓
nomic-embed-text
       ↓
ChromaDB
       ↓
Recherche sémantique
       ↓
Passages pertinents
       ↓
Qwen3:8b
       ↓
Réponse
```

### Recherche

L'outil MCP `search_documents` accepte notamment :

- `query`
- `category`
- `department`
- `top_k`
- `similarity_threshold`

Les catégories RH utilisées sont notamment :

- `leave_policy`
- `benefits`
- `rh_policy`
- `hr_procedure`
- `training`
- `onboarding`
- `compliance`
- `other`

Une règle importante du projet est que les politiques et procédures RH internes doivent provenir des documents internes récupérés par le RAG.

---

## 5. MCP — Model Context Protocol

Le projet utilise MCP pour séparer les capacités métier du cœur de l'agent.

Le client MCP se connecte au serveur via **SSE** et découvre dynamiquement les outils disponibles.

### Outils actuellement découverts

#### `search_documents`

Permet à l'agent de rechercher des informations dans la base documentaire RH.

#### `soumettre_demande_conge`

Permet de préparer l'intégration d'un workflow de demande de congé.

Paramètres :

```text
employe_id
date_debut
date_fin
type_conge
motif
```

### Découverte dynamique

Le fonctionnement observé est :

```text
GET /mcp/sse
        ↓
MCP session
        ↓
POST /mcp/messages/
        ↓
Tool discovery
        ↓
search_documents
soumettre_demande_conge
        ↓
LangChain tools
        ↓
LangGraph ReAct
```

La découverte dynamique des outils MCP est actuellement fonctionnelle.

---

## 6. LLM local — Qwen3:8b + Ollama

Le chatbot utilise actuellement :

```text
Qwen3:8b
    ↓
Ollama
    ↓
API locale
http://127.0.0.1:11434
```

Le modèle est exécuté localement, ce qui permet de conserver l'inférence dans l'environnement contrôlé du projet.

Le log d'exécution confirme notamment :

```text
Initializing local Ollama model: qwen3:8b
Using local Qwen model through Ollama
POST /api/chat → 200 OK
```

Pour les embeddings, le projet utilise :

```text
nomic-embed-text
```

via Ollama.

---

## 7. LangGraph ReAct

Le chatbot utilise un agent de type **ReAct**.

Son rôle est de :

1. analyser la demande ;
2. déterminer si une information interne est nécessaire ;
3. sélectionner l'outil MCP approprié ;
4. exécuter l'outil ;
5. récupérer les résultats ;
6. générer la réponse finale.

Pour les questions RH internes, une règle applicative impose l'utilisation de `search_documents` avec une catégorie adaptée.

---

## 8. Firebase Authentication

Firebase est utilisé pour gérer l'identité des utilisateurs.

### Frontend

Le frontend React utilise :

- `onAuthStateChanged`
- `signOut`
- Firebase Web SDK

L'utilisateur non authentifié est redirigé vers `Login.tsx`.

### Backend

Le backend utilise Firebase Admin SDK.

La fonction :

```python
verify_firebase_token()
```

effectue :

1. lecture de l'en-tête `Authorization` ;
2. vérification du format `Bearer <token>` ;
3. extraction du Firebase ID Token ;
4. validation avec `firebase_admin.auth.verify_id_token()` ;
5. récupération des informations utilisateur ;
6. rejet des tokens invalides ou expirés avec HTTP 401.

---

## 9. RBAC — Gestion des rôles et permissions

La partie permissions a maintenant été ajoutée au projet.

Le rôle est porté par un **Firebase Custom Claim**.

Exemple de données décodées observées :

```text
role: admin
uid: ...
email: ...
```

### Backend

Une dépendance d'autorisation administrateur est utilisée :

```python
async def require_admin(
    authorization: str | None = Header(default=None),
):
    user = await verify_firebase_token(authorization)

    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="Accès administrateur requis",
        )

    return user
```

La logique est donc :

```text
Request
   ↓
Firebase token
   ↓
Token valide ?
   ├── Non → 401
   │
   └── Oui
        ↓
     role ?
        ├── admin → accès autorisé
        │
        └── autre → 403
```

Cela constitue la première vraie couche d'autorisation côté backend, au-delà de la simple authentification.

---

## 10. Dashboard Administration

Le frontend React contient maintenant une page **Administration**, accessible uniquement lorsque l'utilisateur possède le rôle `admin`.

### Détection du rôle

Le frontend récupère les Custom Claims Firebase avec :

```typescript
const tokenResult =
    await currentUser.getIdTokenResult();

const role = tokenResult.claims.role;

setIsAdmin(role === "admin");
```

### Accès conditionnel

Le bouton **Administration** n'est affiché que si :

```text
isAdmin === true
```

La page admin contient actuellement :

- identité du compte administrateur ;
- rôle ADMIN ;
- état Firebase Authentication ;
- état du RBAC ;
- état de protection backend ;
- statistiques de base ;
- emplacement prévu pour les modules futurs.

### Modules prévus

```text
Administration
├── Utilisateurs
├── Rôles / Permissions
├── Alertes
└── Audit Logs
```

---

## 11. Protection de `/api/chat`

Le frontend transmet le token Firebase :

```http
Authorization: Bearer <Firebase_ID_Token>
```

Le backend vérifie le token avant d'exécuter le chatbot.

Le principe est :

```text
React
  ↓
Firebase ID Token
  ↓
POST /api/chat
  ↓
verify_firebase_token()
  ↓
ChatService
```

Une requête sans token valide ne doit pas atteindre l'agent.

---

## 12. Interface React

Le frontend principal est maintenant **React + TypeScript + Tailwind CSS**.

### Fonctionnalités actuelles

- authentification Firebase ;
- login ;
- chat ;
- historique des conversations ;
- création d'une nouvelle conversation ;
- envoi de messages ;
- indicateur de chargement ;
- affichage des sources ;
- affichage des catégories ;
- copie des réponses ;
- boutons feedback ;
- déconnexion ;
- interface responsive ;
- navigation Conversations / Administration ;
- dashboard administrateur.

### `App.tsx`

Le composant principal gère :

- l'état Firebase ;
- le rôle administrateur ;
- les conversations ;
- l'appel `/api/chat` ;
- l'affichage des réponses ;
- les sources RAG ;
- la page administration ;
- la déconnexion.

---

## 13. Test réel effectué

Un test de bout en bout a été réalisé avec la question :

```text
Quelles sont les règles concernant les congés annuels ?
```

Le système a correctement :

```text
1. Authentifié l'utilisateur Firebase
2. Détecté le rôle admin
3. Initialisé une session MCP
4. Découvert les outils MCP
5. Initialisé Qwen3:8b via Ollama
6. Appelé search_documents
7. Effectué la recherche RAG
8. Récupéré les documents pertinents
9. Généré la réponse avec Qwen
10. Retourne la réponse au frontend
```

Exemple de résultat récupéré :

```text
Le congé annuel accorde 25 jours ouvrables par an
pour tout salarié à temps plein.

Le salarié doit poser ses congés avec un préavis
minimum de 15 jours ouvrés, sauf accord exceptionnel
du manager.
```

La réponse finale contient également la source et la catégorie documentaire.

### Exemple de catégorie utilisée

```text
leave_policy
```

### Exemple de chaîne observée dans les logs

```text
React
 ↓
POST /api/chat
 ↓
Firebase authentication
 ↓
MCP session initialized
 ↓
MCP tool discovered: search_documents
 ↓
Qwen3:8b
 ↓
search_documents
 ↓
RAG search completed
 ↓
Qwen3:8b
 ↓
AGENT FINISHED
 ↓
POST /api/chat → 200 OK
```

Ce test valide le fonctionnement de l'architecture complète sur un cas RH réel de démonstration.

---

## 14. Sécurité actuelle

### Niveau 1 — Authentication

```text
Firebase Authentication
```

Identifie l'utilisateur.

### Niveau 2 — Token validation

```text
Firebase Admin SDK
```

Valide le Firebase ID Token côté backend.

### Niveau 3 — Authorization / RBAC

```text
Firebase Custom Claims
        ↓
role=admin
        ↓
require_admin()
```

Les utilisateurs non administrateurs sont refusés pour les endpoints nécessitant les privilèges admin.

### Objectif de sécurité

```text
Utilisateur
    ↓
Authentication
    ↓
Identity
    ↓
Role
    ↓
Permission
    ↓
Resource / Tool
```

---

## 15. n8n et workflows métier

Le projet prévoit l'utilisation de **n8n** pour les workflows métier.

Le principal cas d'utilisation actuel est :

```text
Utilisateur
    ↓
Assistant
    ↓
soumettre_demande_conge
    ↓
n8n
    ↓
Workflow de demande de congé
```

L'outil MCP est déjà découvert par l'agent.

La validation complète de la chaîne réelle **Backend → n8n → workflow métier** reste une étape à finaliser avant de considérer ce workflow comme totalement validé.

---

## 16. Structure du projet

```text
Cortex_AI_Minist-re-main/
│
├── RESUME.md
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── Login.tsx
│   │   ├── firebase.ts
│   │   └── ...
│   └── package.json
│
├── Backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── firebase_auth.py
│   │   ├── api/
│   │   │   └── routes/
│   │   │       └── chat.py
│   │   ├── schemas/
│   │   └── services/
│   │       ├── chat/
│   │       │   ├── chat_service.py
│   │       │   └── mcp_client.py
│   │       ├── rag/
│   │       │   └── rag_service.py
│   │       └── workflows/
│   │           └── n8n_service.py
│   │
│   ├── chroma_db/
│   ├── seed_documents.py
│   └── tests/
│
└── ...
```

---

## 17. Stack technique actuelle

| Technologie | Rôle |
|---|---|
| React | Interface web |
| TypeScript | Développement frontend |
| Tailwind CSS | Design UI |
| Firebase Authentication | Authentification |
| Firebase Admin SDK | Vérification des tokens |
| Firebase Custom Claims | Gestion des rôles |
| Python 3.14 | Backend |
| FastAPI | API REST + serveur MCP |
| MCP SDK | Communication avec les outils |
| LangGraph | Agent ReAct |
| LangChain | Intégration LLM / tools |
| Qwen3:8b | LLM conversationnel local |
| Ollama | Runtime LLM + embeddings |
| ChromaDB | Base vectorielle |
| nomic-embed-text | Modèle d'embeddings |
| n8n | Automatisation des workflows |
| Pydantic | Validation des données |
| httpx | Client HTTP asynchrone |
| pytest | Tests |

---

## 18. Commandes de lancement

### Ollama

```powershell
ollama serve
```

Vérifier que les modèles nécessaires sont disponibles :

```powershell
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

### Backend

Depuis la racine du projet :

```powershell
venv\Scripts\python.exe -m uvicorn app.main:app --app-dir Backend --host 127.0.0.1 --port 8000
```

### Frontend

Depuis le dossier frontend :

```powershell
npm install
npm run dev
```

### Base documentaire

```powershell
venv\Scripts\python.exe Backend\seed_documents.py
```

### Tests

```powershell
venv\Scripts\python.exe -m pytest Backend\tests\ -q
```

---

## 19. État actuel du projet

### Fonctionnel / implémenté

- [x] Interface React
- [x] Firebase Authentication
- [x] Firebase ID Token
- [x] Vérification Firebase côté backend
- [x] Protection de `/api/chat`
- [x] Firebase Custom Claims
- [x] Détection du rôle `admin`
- [x] Autorisation backend `require_admin`
- [x] Dashboard Administration
- [x] Navigation conditionnelle Admin
- [x] RAG
- [x] ChromaDB
- [x] Embeddings Ollama
- [x] MCP Server
- [x] MCP SSE
- [x] MCP tool discovery
- [x] `search_documents`
- [x] `soumettre_demande_conge`
- [x] LangGraph ReAct
- [x] Qwen3:8b local
- [x] Ollama
- [x] Conversation history
- [x] Affichage des sources
- [x] Affichage des catégories
- [x] Test réel question RH → RAG → Qwen → réponse
- [x] API `/api/chat` retournant HTTP 200 sur le test réalisé

### À finaliser

- [ ] Gestion complète des utilisateurs depuis le dashboard
- [ ] Gestion avancée des rôles et permissions
- [ ] Alertes de données sensibles
- [ ] Audit logs
- [ ] Monitoring détaillé
- [x] Validation Backend → n8n
- [x] Test réel du workflow n8n de demande de congé
- [ ] Sécurisation finale du webhook n8n
- [ ] Tests RBAC complets avec plusieurs rôles
- [ ] Tests de refus HTTP 401/403 systématiques
- [ ] Gestion réelle des pièces jointes/documents depuis l'interface

---


---

## 19 bis. Validation récente de l'intégration n8n

La configuration n8n côté backend a été validée avec :

```json
{
  "status": "ok",
  "rag_initialized": true,
  "n8n_configured": true
}
```

Un test réel du service n8n a également été exécuté avec succès :

```powershell
python Backend/test_n8n_real.py
```

Résultat :

```text
=== RESULTAT N8N ===
{'statut': 'accepted',
 'message': 'Demande transmise avec succès au manager',
 'demande_id': 'REQ-001'}
```

Le scénario réel de demande de congé fonctionne donc sur la chaîne :

```text
React
  ↓
Backend / Agent
  ↓
MCP
  ↓
soumettre_demande_conge
  ↓
N8nService
  ↓
n8n Webhook
  ↓
Workflow n8n
  ↓
Réponse JSON
  ↓
React
```

### Valeur correcte du type de congé

Le modèle `DemandeConge` utilise l'énumération `TypeConge`.

Pour un congé annuel, la valeur attendue est :

```text
conge_annuel
```

et non :

```text
annuel
```

### Correction HTTPX

Dans `Backend/services/workflows/n8n_service.py`, avec HTTPX, la lecture JSON correcte est :

```python
data = response.json()
```

et non :

```python
data = await response.json()
```

### Tests d'intégration

La commande :

```powershell
pytest -v Backend/tests/test_integration.py
```

a été exécutée avec succès :

```text
10 passed, 1 warning
```

Le warning restant provient de ChromaDB et concerne une dépréciation
d'`asyncio.iscoroutinefunction`. Il n'empêche pas les tests de passer.

---


## 20. Prochaine étape recommandée

La prochaine phase logique du projet est de transformer le dashboard admin actuel en véritable module de gestion :

```text
ADMIN DASHBOARD
      │
      ├── Utilisateurs
      │      ├── Liste
      │      ├── Recherche
      │      └── Activation / désactivation
      │
      ├── Rôles
      │      ├── Admin
      │      ├── RH
      │      └── Employé
      │
      ├── Permissions
      │      ├── Documents
      │      ├── Recherche RAG
      │      ├── Workflows
      │      └── Administration
      │
      ├── Alertes
      │      └── Données sensibles
      │
      └── Audit Logs
             ├── Connexions
             ├── Requêtes
             ├── Actions
             └── Appels outils
```

---

## 21. Règles importantes pour la maintenance

Avant toute modification :

1. Lire `RESUME.md`.
2. Identifier le composant concerné.
3. Vérifier le code réel avant de modifier.
4. Ne pas supposer qu'une variable d'environnement existe.
5. Ne pas remplacer une architecture existante sans raison.
6. Préserver les tests existants.
7. Exécuter les tests après modification.
8. Distinguer les problèmes React, FastAPI, Firebase, MCP, RAG, LangGraph, Ollama et n8n.
9. Ne jamais exposer les secrets Firebase ou les clés API.
10. Ne pas déclarer un service fonctionnel uniquement parce qu'une dépendance est installée.
11. Distinguer les tests unitaires/mock des tests d'intégration réels.
12. Les informations RH internes doivent provenir des documents internes récupérés par le RAG.

---

## 22. Résumé exécutif

Le projet dispose maintenant d'une architecture complète de démonstration :

```text
React
  +
Firebase Authentication
  +
RBAC / Admin Custom Claims
  +
FastAPI
  +
MCP
  +
LangGraph ReAct
  +
RAG / ChromaDB
  +
Ollama
  +
Qwen3:8b
  +
n8n
```

La chaîne **authentification → API sécurisée → MCP → outil RAG → recherche documentaire → LLM local → réponse avec source** a été testée avec succès sur une question RH.

La partie **RBAC** est également commencée et fonctionne avec le rôle `admin`, tandis que le dashboard d'administration est déjà intégré au frontend.

Le projet peut donc maintenant passer d'une phase principalement technique de mise en place à une phase de **durcissement des permissions, gestion des utilisateurs, alertes de données sensibles, audit et validation des workflows métier**.

---

## 23. Améliorations récentes — Août 2026

Cette section regroupe les améliorations ajoutées récemment au projet afin de refléter l'état réel actuel de l'architecture.

### 23.1 Correction de la recherche RAG générale RH

Un problème a été identifié lorsque l'utilisateur lançait une recherche générale telle que :

```text
Rechercher les documents disponibles concernant les ressources humaines.
```

L'agent choisissait parfois automatiquement :

```text
category="other"
```

ce qui pouvait conduire à une recherche vide même lorsque des documents RH pertinents existaient.

Une garde a donc été ajoutée dans le client MCP pour reconnaître les recherches RH générales et supprimer la catégorie `other` dans ce cas.

Principe appliqué :

```python
if _tool_name == "search_documents":
    query = str(kwargs.get("query", "")).lower()

    general_hr_search_markers = (
        "documents disponibles",
        "documents rh",
        "ressources humaines",
        "recherche générale",
        "rechercher les documents",
        "liste des documents",
    )

    is_general_hr_search = any(
        marker in query
        for marker in general_hr_search_markers
    )

    if (
        is_general_hr_search
        and kwargs.get("category") == "other"
    ):
        kwargs["category"] = None
```

Résultat validé :

```text
Recherche RH générale
    ↓
MCP search_documents
    ↓
category forcée à None
    ↓
RAG
    ↓
5 résultats pertinents
    ↓
Réponse finale avec documents RH
```

Cette correction permet de conserver les catégories pour les recherches ciblées tout en évitant un filtrage inutile lors d'une recherche RH générale.

### 23.2 Refactorisation du frontend React

Le frontend a été restructuré afin de réduire fortement la taille de `App.tsx` et de séparer les responsabilités.

Les composants principaux extraits sont maintenant :

```text
Frontend/src/
│
├── components/
│   ├── Admin/
│   │   └── AdminDashboard.tsx
│   ├── Chat/
│   │   ├── ChatInput.tsx
│   │   ├── ChatMessage.tsx
│   │   ├── ChatPanel.tsx
│   │   └── EmptyChat.tsx
│   ├── Leave/
│   │   └── LeaveRequestForm.tsx
│   ├── Header.tsx
│   └── Sidebar.tsx
│
├── hooks/
│   └── useChat.ts
│
├── services/
│   └── api.ts
│
├── types/
│   └── index.ts
│
├── App.tsx
├── Login.tsx
└── firebase.ts
```

Le hook `useChat.ts` centralise maintenant la logique liée aux conversations : message courant, état de chargement, liste des conversations, conversation active, historique, appel API `/api/chat`, traitement de la réponse, sources/catégories, copie, touche Entrée et création de conversations.

`App.tsx` est désormais principalement responsable de l'authentification, de la détection du rôle, du routage de page et de la composition des composants.

### 23.3 Type centralisé pour les pages frontend

Un type commun a été ajouté dans `Frontend/src/types/index.ts` :

```typescript
export type AppPage =
  | "chat"
  | "leave"
  | "requests"
  | "documents"
  | "settings"
  | "manager"
  | "admin";
```

Ce type est maintenant partagé entre `App.tsx`, `Sidebar.tsx` et `Header.tsx`.

### 23.4 Nouvelle page dédiée aux demandes de congé

Une page React dédiée aux demandes de congé a été ajoutée.

```text
Utilisateur
    ↓
Sidebar
    ↓
Demande de congé
    ↓
LeaveRequestForm
    ↓
Firebase ID Token
    ↓
POST /api/conges
    ↓
FastAPI
    ↓
N8nService
    ↓
n8n
    ↓
Réponse métier
    ↓
demande_id
    ↓
React
```

La page contient notamment l'identifiant employé, les dates de début et de fin, le type de congé, le motif, la validation frontend, l'état de chargement, les erreurs, la confirmation de succès et la référence `demande_id`.

### 23.5 Nouveau endpoint REST protégé `/api/conges`

Un nouvel endpoint FastAPI dédié a été ajouté :

```http
POST /api/conges
```

Il est protégé par Firebase via `verify_firebase_token`.

### 23.6 Validation réelle React → FastAPI → n8n

Le nouvel endpoint `/api/conges` a été testé depuis le frontend avec un utilisateur Firebase authentifié.

Réponse n8n réelle observée :

```json
{
  "statut": "accepted",
  "message": "Demande transmise avec succès au manager",
  "demande_id": "REQ-1786585285996"
}
```

Le backend a retourné `HTTP 200 OK`, ce qui valide la chaîne complète React → Firebase → FastAPI → N8nService → n8n → React avec un `demande_id` dynamique.

### 23.7 Service frontend centralisé pour les appels API

Le fichier `Frontend/src/services/api.ts` centralise maintenant les appels API principaux avec notamment :

```text
sendChatMessage()
submitLeaveRequest()
```

`LeaveRequestForm.tsx` n'effectue plus directement le `fetch()` vers le backend.

### 23.8 Renforcement du schéma `DemandeConge`

Le schéma Pydantic a été nettoyé et renforcé.

Il utilise `TypeConge` pour limiter les valeurs acceptées et applique notamment :

- `extra="forbid"` ;
- `employe_id` obligatoire et nettoyé ;
- longueur contrôlée ;
- `date_fin >= date_debut` ;
- type de congé limité à l'énumération ;
- motif obligatoire et nettoyé ;
- longueur du motif contrôlée.

Le backend retourne automatiquement `422 Unprocessable Content` pour une requête invalide. Un test réel a confirmé ce comportement.

### 23.9 Répartition de la validation

La validation est maintenant répartie de façon claire :

```text
Frontend
    ↓
Validation UX

FastAPI / Pydantic
    ↓
Validation officielle et sécurité des données

n8n
    ↓
Règles métier / workflow
```

La validation technique n'est donc pas dupliquée inutilement dans n8n.

### 23.10 Configuration n8n du nouvel endpoint

La configuration passe par :

```python
from core.config import get_settings

settings = get_settings()
```

avec `n8n_webhook_url`, `n8n_secret_token` et `n8n_timeout_seconds`.

### 23.11 Nettoyage du routing FastAPI

La route `/api/admin/test` dupliquée a été supprimée afin de conserver une seule définition.

### 23.12 Navigation frontend mise à jour

Le frontend supporte maintenant sept pages principales :

```text
chat
leave
requests
documents
settings
manager
admin
```

Le header adapte son contenu selon la page.

### 23.13 État fonctionnel actualisé

Les éléments suivants sont maintenant validés :

```text
[x] Recherche RAG générale RH corrigée
[x] Refactorisation de App.tsx
[x] Composants Chat séparés
[x] Sidebar séparée
[x] Header séparé
[x] Hook useChat
[x] Service API frontend
[x] Type AppPage centralisé
[x] Page React de demande de congé
[x] Navigation vers la page congé
[x] Endpoint POST /api/conges
[x] Protection Firebase de /api/conges
[x] Validation Pydantic renforcée
[x] Rejet HTTP 422 des demandes invalides
[x] Appel réel FastAPI → n8n
[x] Réponse n8n HTTP 200
[x] demande_id dynamique
[x] Affichage du résultat dans React
[x] Suppression du fetch direct du formulaire
[x] Suppression de la route admin de test dupliquée
```

---

## 24. Architecture actualisée après les améliorations

```text
                         Utilisateur
                              │
                              ▼
                    React + TypeScript
                              │
                  ┌───────────┴───────────┐
                  │                       │
                  ▼                       ▼
               Chat UI              LeaveRequestForm
                  │                       │
                  └───────────┬───────────┘
                              │
                     Firebase ID Token
                              │
                              ▼
                           FastAPI
                              │
               ┌──────────────┴──────────────┐
               │                             │
               ▼                             ▼
          POST /api/chat               POST /api/conges
               │                             │
               ▼                             ▼
          ChatService                 DemandeConge
               │                       validation
               ▼                             │
       LangGraph ReAct                       ▼
               │                         N8nService
               ▼                             │
          MCP Client                         ▼
               │                            n8n
        ┌──────┴─────────┐                   │
        ▼                ▼                   ▼
 search_documents   soumettre...        Workflow RH
        │                                    │
        ▼                                    ▼
     RAGService                          demande_id
        │                                    │
        ▼                                    ▼
     ChromaDB                              React
        │
        ▼
 nomic-embed-text
        │
        ▼
     Qwen3:8b
        │
        ▼
      React
```

---

## 25. État actuel mis à jour

### Fonctionnel / validé

- [x] Interface React + TypeScript + Tailwind CSS
- [x] Firebase Authentication
- [x] Firebase ID Token
- [x] Vérification Firebase côté backend
- [x] Protection de `/api/chat`
- [x] Protection de `/api/conges`
- [x] Firebase Custom Claims
- [x] Rôle administrateur
- [x] `require_admin`
- [x] Dashboard Administration
- [x] Navigation Conversations / Congés / Mes demandes / Manager / Administration / Documents / Paramètres
- [x] Hook `useChat`
- [x] Service API frontend centralisé
- [x] RAG
- [x] ChromaDB
- [x] Embeddings Ollama
- [x] MCP Server
- [x] MCP SSE
- [x] Découverte dynamique des outils MCP
- [x] `search_documents`
- [x] Correction des recherches RH générales
- [x] `soumettre_demande_conge`
- [x] LangGraph ReAct
- [x] Qwen3:8b local
- [x] Ollama
- [x] Historique de conversation
- [x] Affichage des sources
- [x] Affichage des catégories
- [x] Endpoint REST `/api/conges`
- [x] Formulaire React de demande de congé
- [x] Validation frontend
- [x] Validation Pydantic backend
- [x] Rejet des demandes invalides avec HTTP 422
- [x] Validation réelle Backend → n8n
- [x] Test réel React → FastAPI → n8n
- [x] Réponse métier n8n
- [x] `demande_id` dynamique
- [x] Tests d'intégration existants
- [x] Nettoyage du routing `/api/admin/test`

### À finaliser

- [ ] Gestion complète des utilisateurs depuis le dashboard
- [ ] Gestion avancée des rôles et permissions
- [ ] Alertes de données sensibles
- [ ] Audit logs
- [ ] Monitoring détaillé
- [x] Webhooks n8n publiés et utilisés via les URLs de production `/webhook/...`
- [ ] Renforcement final de la sécurité du webhook n8n (secret, contrôle d'accès, durcissement)
- [x] Gestion persistante des demandes de congé avec SQLite
- [x] Historique des demandes de congé côté employé
- [x] Rôle `manager` via Firebase Custom Claims
- [x] Endpoints manager protégés par `require_manager_or_admin`
- [x] Validation / refus des demandes par le manager
- [x] Notifications email du manager lors d'une nouvelle demande
- [x] Notifications email de l'employé après acceptation / refus
- [x] Workflow n8n distinct pour la notification de statut
- [x] Tests backend : `10 passed, 1 warning`
- [x] Build frontend React validé avec `npm run build`
- [ ] Tests RBAC complets avec plusieurs rôles
- [ ] Tests systématiques HTTP 401 / 403
- [ ] Gestion réelle des pièces jointes et documents depuis l'interface
- [x] Consultation admin de la base documentaire depuis la page Documents
- [ ] Upload / suppression / réindexation de documents depuis l’interface
- [x] Page Paramètres utilisateur avec informations de compte
- [x] Changement de mot de passe via Firebase avec réauthentification
- [ ] Paramètres système admin dynamiques (Ollama / RAG / n8n / monitoring)
- [ ] Migration de `OllamaEmbeddings` vers `langchain-ollama` pour supprimer le warning de dépréciation

---

## 26. Prochaine phase recommandée actualisée

Ordre recommandé :

```text
1. Paramètres système admin : statut Ollama / RAG / n8n
2. Upload et réindexation de documents depuis l’interface Admin
3. Tests de sécurité HTTP 401 / 403 / RBAC avec plusieurs rôles
4. Durcissement final des webhooks n8n
5. Audit logs
6. Gestion des utilisateurs / rôles avancés
7. Permissions fines sur les documents RAG
8. Monitoring
9. Gestion des pièces jointes
10. Migration de `OllamaEmbeddings` vers `langchain-ollama`
```

Le projet dispose maintenant de deux chemins métier principaux validés :

```text
QUESTION RH
    ↓
React
    ↓
Firebase
    ↓
FastAPI
    ↓
LangGraph / MCP
    ↓
RAG
    ↓
Qwen3:8b
    ↓
Réponse sourcée
```

et :

```text
DEMANDE DE CONGÉ
    ↓
React
    ↓
Firebase
    ↓
FastAPI /api/conges
    ↓
Pydantic Validation
    ↓
N8nService
    ↓
n8n
    ↓
Workflow métier
    ↓
demande_id
    ↓
Confirmation React
```

Ces deux chaînes ont maintenant été validées dans l'environnement de développement.

---

## 27. Mise à jour majeure — Gestion complète des demandes de congé

Cette section décrit l'état réel le plus récent du workflow de congé après l'ajout de la persistance, du rôle manager et des notifications email.

### 27.1 Persistance SQLite

Une base SQLite est maintenant utilisée pour conserver les demandes de congé.

Le modèle `LeaveRequestModel` contient notamment :

```text
demande_id
user_uid
employee_email
employe_id
type_conge
date_debut
date_fin
motif
statut
message
created_at
```

`demande_id` est unique et sert de référence fonctionnelle du workflow.

Le champ `employee_email` a été ajouté afin de pouvoir notifier directement l'employé après la décision du manager.

Une migration SQLite manuelle a été appliquée pour ajouter la colonne :

```sql
ALTER TABLE leave_requests
ADD COLUMN employee_email VARCHAR(255);
```

### 27.2 Statut applicatif normalisé

Même si le premier workflow n8n peut retourner un statut interne lors de la soumission, le backend enregistre désormais toute nouvelle demande avec :

```text
pending
```

Le cycle de vie applicatif devient donc :

```text
pending
   ├── accepted
   └── rejected
```

Cela donne une vraie signification à l'étape de validation du manager.

### 27.3 Endpoints de consultation et de gestion

Les endpoints suivants sont maintenant disponibles :

```http
POST  /api/conges
GET   /api/conges
GET   /api/manager/conges
PATCH /api/manager/conges/{demande_id}
```

Le rôle manager ou admin est requis pour les endpoints `/api/manager/...`.

Le backend utilise :

```python
require_manager_or_admin
```

pour autoriser uniquement les rôles :

```text
manager
admin
```

### 27.4 Rôle manager dans Firebase

Le rôle `manager` est porté par un Firebase Custom Claim.

Après attribution du claim, l'utilisateur doit effectuer un logout/login afin d'obtenir un nouveau Firebase ID Token contenant le rôle.

Le frontend adapte ensuite la navigation :

```text
Employé
├── Conversations
├── Demande de congé
├── Mes demandes
└── Paramètres

Manager
├── Conversations
├── Demande de congé
├── Mes demandes
├── Espace Manager
└── Paramètres

Admin
├── Conversations
├── Demande de congé
├── Mes demandes
├── Espace Manager
├── Administration
├── Documents
└── Paramètres
```

### 27.5 Page `Mes demandes`

Une page dédiée permet à l'employé de consulter ses propres demandes depuis SQLite.

Fonctionnalités principales :

```text
- liste des demandes
- statut pending / accepted / rejected
- statistiques
- filtres par statut
- affichage du détail
- date de création
- motif
- référence demande_id
```

La récupération est sécurisée par Firebase et filtrée avec le `user_uid`.

### 27.6 Dashboard Manager

Le frontend possède maintenant un composant :

```text
Frontend/src/components/Manager/ManagerDashboard.tsx
```

Il permet au manager de :

```text
- consulter toutes les demandes
- voir les statistiques
- afficher le détail d'une demande
- accepter une demande pending
- refuser une demande pending
```

Les boutons d'action ne sont disponibles que lorsque :

```text
statut == pending
```

### 27.7 Premier workflow n8n — Soumission d'une demande

Le premier workflow gère la soumission initiale.

Architecture actuelle :

```text
Webhook
  ↓
Valider demande de congé
  ↓
IF statut == en_attente
  ├── True
  │    ↓
  │  Send an Email au manager
  │    ↓
  │  Respond to Webhook
  │
  └── False
       ↓
     Respond to Webhook
```

Le workflow génère un identifiant dynamique du type :

```text
REQ-1786667425656
```

La réponse de succès contient maintenant explicitement :

```json
{
  "statut": "accepted",
  "message": "Demande transmise avec succès au manager",
  "demande_id": "REQ-..."
}
```

Le `demande_id` est récupéré directement depuis le nœud de validation afin d'éviter qu'un nœud email intermédiaire ne remplace le `$json`.

### 27.8 Protection contre les `demande_id` invalides

Le backend ne doit plus utiliser :

```python
result.get("demande_id", "N/A")
```

La logique actuelle valide explicitement la présence du champ :

```python
demande_id = result.get("demande_id")

if not demande_id:
    logger.error(
        "n8n response missing demande_id: %s",
        result,
    )

    raise N8nServiceError(
        "n8n response does not contain a valid demande_id"
    )
```

Cette protection évite l'enregistrement de références vides ou `"N/A"` dans SQLite et évite les conflits de contrainte `UNIQUE`.

Les anciens enregistrements invalides créés avant cette correction ont été supprimés.

### 27.9 Deuxième workflow n8n — Notification de décision

Un second workflow n8n distinct a été créé pour notifier l'employé après la décision du manager.

Webhook :

```text
notification-statut-conge
```

Architecture :

```text
Webhook
  ↓
IF {{$json.body.statut}} == accepted
  ├── True
  │    ↓
  │  Send Email accepté
  │    ↓
  │  Respond 200
  │
  └── False
       ↓
     Send Email refusé
       ↓
     Respond 200
```

Payload envoyé par FastAPI :

```json
{
  "email": "employee@example.com",
  "demande_id": "REQ-...",
  "statut": "accepted"
}
```

ou :

```json
{
  "email": "employee@example.com",
  "demande_id": "REQ-...",
  "statut": "rejected"
}
```

### 27.10 Configuration des webhooks n8n

Les deux workflows ont été publiés dans n8n.

Les URLs utilisées par l'application sont maintenant des URLs de production n8n :

```env
N8N_WEBHOOK_URL=http://localhost:5678/webhook/conge-test
N8N_STATUS_NOTIFICATION_WEBHOOK_URL=http://localhost:5678/webhook/notification-statut-conge
```

Les URLs `/webhook-test/...` sont réservées aux scripts et tests interactifs nécessitant `Listen for test event`.

### 27.11 Extension de `N8nService`

`N8nService` supporte maintenant deux webhooks :

```python
N8nService(
    webhook_url=...,
    secret_token=...,
    timeout_seconds=...,
    status_notification_webhook_url=...,
)
```

Deux opérations métier principales sont disponibles :

```text
soumettre_demande_conge()
notifier_statut_demande()
```

### 27.12 Fiabilité de la mise à jour manager

Le traitement du `PATCH` manager a été séparé en deux étapes :

```text
1. mise à jour SQLite
2. tentative de notification n8n
```

Si la base de données échoue :

```text
→ HTTP 500
```

Si la base est mise à jour mais que la notification email échoue :

```text
→ la décision reste enregistrée
→ l'erreur de notification est journalisée
→ la réponse manager reste cohérente avec l'état réellement enregistré
```

Cela évite qu'un incident email fasse croire au manager que son acceptation ou son refus n'a pas été enregistré.

### 27.13 Tests end-to-end validés

Le scénario suivant a été testé avec succès :

```text
Employé
  ↓
POST /api/conges
  ↓
Firebase Authentication
  ↓
FastAPI
  ↓
n8n workflow 1
  ↓
notification manager
  ↓
SQLite : pending
  ↓
Espace Manager
  ↓
PATCH /api/manager/conges/{demande_id}
  ↓
accepted / rejected
  ↓
n8n workflow 2
  ↓
email à l'employé
  ↓
Mes demandes mises à jour
```

Les deux branches ont été validées :

```text
[x] accepted → email d'acceptation reçu
[x] rejected → email de refus reçu
```

### 27.14 Validation technique après modifications

Après les changements récents :

```text
pytest -q
```

résultat :

```text
10 passed, 1 warning
```

Le warning restant provient de ChromaDB :

```text
DeprecationWarning:
asyncio.iscoroutinefunction is deprecated
```

Il n'est pas bloquant actuellement.

Le frontend a également été validé avec :

```powershell
cd Frontend
npm run build
```

Le build React/TypeScript est fonctionnel.

### 27.15 État fonctionnel du workflow congé

```text
[x] Formulaire React de demande
[x] Authentification Firebase
[x] Validation Pydantic
[x] Premier workflow n8n
[x] demande_id dynamique
[x] Notification email au manager
[x] Persistance SQLite
[x] Statut pending
[x] Historique employé
[x] Rôle manager Firebase
[x] Dashboard Manager
[x] Acceptation
[x] Refus
[x] Deuxième workflow n8n
[x] Email d'acceptation à l'employé
[x] Email de refus à l'employé
[x] Webhooks n8n publiés
[x] Protection contre demande_id vide / N/A
[x] Tests backend
[x] Build frontend
```

### 27.16 Architecture congé actuelle

```text
EMPLOYÉ
   │
   ▼
React
   │
   ▼
Firebase ID Token
   │
   ▼
POST /api/conges
   │
   ▼
FastAPI / Pydantic
   │
   ▼
N8nService
   │
   ▼
n8n Workflow 1
   │
   ├── Génère demande_id
   └── Email manager
   │
   ▼
SQLite
statut = pending
   │
   ▼
ManagerDashboard
   │
   ├── Accepter
   └── Refuser
   │
   ▼
PATCH /api/manager/conges/{demande_id}
   │
   ▼
SQLite
accepted / rejected
   │
   ▼
N8nService.notifier_statut_demande()
   │
   ▼
n8n Workflow 2
   │
   ├── accepted → email acceptation
   └── rejected → email refus
   │
   ▼
EMPLOYÉ
```

---

## 28. Prochaine étape recommandée après validation du workflow congé

Le workflow de congé principal est maintenant fonctionnel de bout en bout.

Les prochaines priorités recommandées sont :

```text
1. Paramètres système admin : statut Ollama / RAG / n8n
2. Upload et réindexation de documents depuis l’interface Admin
3. Tests de sécurité HTTP 401 / 403 / RBAC avec plusieurs rôles
4. Durcissement final des webhooks n8n
5. Audit logs
6. Gestion des utilisateurs / rôles avancés
7. Permissions fines sur les documents RAG
8. Monitoring
9. Gestion des pièces jointes
10. Migration de OllamaEmbeddings vers langchain-ollama
```

Le projet dispose maintenant de trois axes fonctionnels principaux :

```text
1. Chat RH sécurisé + RAG
2. Administration / RBAC
3. Workflow de congé complet avec validation manager et notifications email
```

---

## 29. Mise à jour — Base documentaire RAG multi-fichiers

Cette section décrit les améliorations récentes apportées au pipeline documentaire RAG.

### 29.1 Ingestion depuis un répertoire de documents

Le script `Backend/seed_documents.py` charge désormais automatiquement les documents présents dans `Backend/data/documents/`. Les formats supportés sont `.txt`, `.pdf` et `.docx`.

Le pipeline conserve l’architecture suivante :

```text
Fichier → Extraction du texte → RecursiveCharacterTextSplitter → Métadonnées → DocumentIngestion → RAGService → Ollama Embeddings → ChromaDB
```

Le chunking actuel utilise `chunk_size = 800` et `chunk_overlap = 200`. Les métadonnées sont propagées à chaque chunk.

### 29.2 Documents de démonstration ajoutés

Huit documents de démonstration ont été ajoutés :

```text
avantages_sociaux.txt
formation_professionnelle.txt
onboarding_nouvel_employe.txt
politique_conges.txt
procedure_demande_conge.txt
reglement_interieur.txt
securite_et_confidentialite.txt
teletravail.txt
```

Ces documents sont destinés aux tests du système RAG et ne doivent pas être présentés comme des procédures officielles du Ministère.

### 29.3 Validation de l’ingestion

L’ingestion a été validée avec succès :

```text
8 documents → 13 chunks → Batch ingestion successful → 13 chunks ingérés dans ChromaDB
```

Un premier essai avait échoué lorsque le service Ollama n’était pas disponible sur `localhost:11434`. Après démarrage d’Ollama, l’ingestion a réussi.

### 29.4 Nettoyage de ChromaDB

Une ancienne collection contenait encore des chunks issus des documents RH hard-codés. Cela produisait un mélange d’informations anciennes et nouvelles. La base `chroma_db` a été réinitialisée puis reconstruite à partir des huit nouveaux documents.

Après nettoyage, les réponses ne contiennent plus les anciennes informations absentes des nouveaux documents, telles que le remboursement internet de 30 €, le casque fourni ou l’avenant obligatoire au contrat.

### 29.5 Correction de la classification des procédures

`procedure_demande_conge.txt` contient à la fois les mots `procedure` et `conge`. La fonction `detect_category()` testait auparavant `conge` avant `procedure`, ce qui classait incorrectement le document dans `leave_policy`.

La priorité a été corrigée afin de tester les procédures avant les congés. Le document est maintenant classé `hr_procedure`.

### 29.6 Validation fonctionnelle du retrieval

Un test ciblé a récupéré correctement les étapes détaillées de la procédure interne de demande de congé : connexion, accès à la rubrique, identifiant employé, type de congé, dates, motif, soumission, statut en attente, notification manager, acceptation/refus, notification employé et suivi dans « Mes demandes ».

### 29.7 Renforcement du grounding du LLM

Le `SYSTEM_PROMPT` de `ChatService` a été renforcé afin d’imposer un grounding plus strict : utilisation obligatoire de `search_documents` pour les informations RH internes, interdiction d’inventer des chiffres/délais/conditions, interdiction de transformer une recommandation en obligation, signalement des informations absentes et distinction entre question informative et demande d’action.

Exemple validé : le document dit « L’employé renseigne le motif. ». L’assistant ne doit plus transformer cette phrase en « Le motif est obligatoire. ».

### 29.8 Distinction question informative / action métier

```text
QUESTION INFORMATIVE → search_documents → réponse RAG
DEMANDE D’ACTION → soumettre_demande_conge
```

Exemples :

```text
« Quelles sont les étapes pour demander un congé ? » → search_documents
« Je veux soumettre une demande de congé. » → soumettre_demande_conge
```

### 29.9 Affichage des sources et catégories

Les métadonnées techniques telles que `internal_wiki` et `hr_procedure` peuvent être présentées avec des libellés plus lisibles :

```text
Source : Documentation RH interne
Catégorie : Procédure RH
```

Lorsque le document indique explicitement qu’il s’agit d’un document de démonstration ou de test, l’assistant doit également l’indiquer sans le présenter comme officiel.

---

## 30. Mise à jour — Pages Documents et Paramètres

### 30.1 Page Documents

Une nouvelle page React a été ajoutée : `Frontend/src/components/Documents/DocumentsPage.tsx`. Elle permet de consulter la base documentaire réelle utilisée par le projet.

### 30.2 Endpoint Documents

Un endpoint FastAPI dédié a été ajouté :

```http
GET /api/documents
```

Il lit les fichiers présents dans `Backend/data/documents/` et retourne le nom, le type et la taille. Le frontend affiche le nombre réel de documents ainsi que la liste des fichiers.

### 30.3 Accès Documents réservé à l’administrateur

La page Documents n’est pas affichée aux employés ni aux managers. La protection est appliquée dans le Sidebar, dans `App.tsx` et côté backend avec `require_admin` sur `GET /api/documents`.

Navigation actuelle :

```text
Employé : Conversations / Demande de congé / Mes demandes / Paramètres
Manager : Conversations / Demande de congé / Mes demandes / Espace Manager / Paramètres
Admin : Conversations / Demande de congé / Mes demandes / Espace Manager / Administration / Documents / Paramètres
```

### 30.4 Page Paramètres

Une nouvelle page `Frontend/src/components/Settings/SettingsPage.tsx` est disponible pour employee, manager et admin. La partie commune affiche les informations du compte et les paramètres de sécurité.

### 30.5 Changement de mot de passe Firebase

Le changement de mot de passe est maintenant géré via Firebase Authentication avec `EmailAuthProvider.credential()`, `reauthenticateWithCredential()` puis `updatePassword()`. Les mots de passe ne sont jamais stockés dans le backend applicatif.

Les erreurs gérées incluent mot de passe actuel incorrect, nouveau mot de passe trop court, confirmation différente, nouveau mot de passe identique à l’ancien, reconnexion récente requise et trop de tentatives.

### 30.6 Paramètres système administrateur

La section « Paramètres système » est maintenant connectée à des données réelles via un endpoint administrateur protégé :

```http
GET /api/admin/system-status
```

Le backend retourne notamment :

```text
ollama
rag
n8n
documents
embedding_model
rag_collection
```

L'interface admin affiche donc dynamiquement :

- état Ollama ;
- état du RAG ;
- état de configuration n8n ;
- nombre réel de documents ;
- modèle d'embeddings ;
- collection RAG.

Le statut Ollama a été validé manuellement : il passe de « Hors ligne » à « En ligne » après démarrage du service Ollama.

---

## 31. Mise à jour — Cycle de vie complet des documents RAG

### 31.1 Service d'ingestion réutilisable

Un service dédié existe maintenant :

```text
Backend/services/rag/document_ingestion.py
```

Il centralise :

- lecture `.txt` ;
- lecture `.pdf` ;
- lecture `.docx` ;
- classification documentaire ;
- métadonnées ;
- chunking ;
- construction des `DocumentIngestion`.

Le chunking reste basé sur :

```text
chunk_size = 800
chunk_overlap = 200
```

### 31.2 Upload administrateur

La page Documents permet maintenant à l'administrateur d'ajouter réellement un document.

Endpoint :

```http
POST /api/documents/upload
```

Caractéristiques :

- admin-only ;
- formats `.txt`, `.pdf`, `.docx` ;
- nom de fichier sécurisé ;
- refus des doublons ;
- sauvegarde dans `Backend/data/documents/` ;
- ingestion immédiate dans le RAG ;
- rollback du fichier si l'extraction ou l'ingestion échoue.

### 31.3 Suppression ciblée

La suppression est également fonctionnelle :

```http
DELETE /api/documents/{filename}
```

Le backend :

1. valide le nom du fichier ;
2. reconstruit les chunks attendus ;
3. supprime uniquement les IDs Chroma liés au document ;
4. supprime le fichier disque ;
5. tente une réingestion si la suppression disque échoue après suppression RAG.

Il n'est donc plus nécessaire de réinitialiser globalement ChromaDB pour supprimer un seul document.

### 31.4 IDs déterministes

`RAGService` utilise des IDs déterministes basés sur le contenu des chunks. Cela permet :

- upsert ciblé ;
- suppression ciblée ;
- réingestion contrôlée ;
- limitation des doublons.

### 31.5 Validation end-to-end

Le cycle suivant a été validé manuellement :

```text
Upload document
    ↓
Ingestion RAG
    ↓
Question dans le chat
    ↓
Réponse basée sur le document
    ↓
Suppression document
    ↓
Suppression ciblée Chroma
    ↓
Le document n'est plus retrouvé par le RAG
```

Un cas de test avec une prime de transport fictive de `777 MAD` a confirmé le bon fonctionnement de l'upload, de la classification `benefits`, du retrieval puis de la suppression.

---

## 32. Mise à jour — RBAC complet et tests de sécurité

### 32.1 Matrice de rôles

Les rôles applicatifs utilisés sont maintenant :

```text
employee
manager
admin
```

Matrice actuelle :

```text
EMPLOYEE
- Chat IA
- Demande de congé
- Mes demandes
- Paramètres

MANAGER
- Chat IA
- Demande de congé
- Mes demandes
- Espace Manager
- Paramètres

ADMIN
- Tableau de bord
- Chat IA
- Demande de congé
- Mes demandes
- Espace Manager
- Administration
- Documents
- Paramètres
```

### 32.2 Dashboard réservé à l'admin

Le type `AppPage` inclut maintenant :

```typescript
"dashboard"
```

Le Dashboard global est réservé à l'administrateur.

Protections frontend :

- le bouton « Tableau de bord » n'est visible que pour `isAdmin === true` ;
- le rendu est également protégé dans `App.tsx` ;
- si un employee ou manager tente d'arriver sur `dashboard`, fallback vers `chat` ;
- après login, l'admin arrive sur le Dashboard, les autres rôles sur le Chat.

Le frontend ne constitue toujours pas la couche de sécurité principale : les endpoints sensibles restent protégés côté backend.

### 32.3 Tests RBAC isolés

Une suite dédiée `Backend/tests/test_rbac.py` vérifie notamment :

- utilisateur non authentifié → `401` ;
- token invalide → `401` ;
- employee interdit sur admin/documents/manager → `403` ;
- manager autorisé sur endpoints manager mais interdit sur admin/documents ;
- admin autorisé sur les endpoints administratifs ;
- upload document admin-only ;
- delete document admin-only ;
- protections path traversal / extension invalide / fichier absent.

Les tests utilisent :

- Firebase mocké ;
- SQLite temporaire ;
- faux n8n ;
- faux MCP/chat quand nécessaire ;
- faux client HTTP pour les statuts système.

À cette étape, la suite avait atteint :

```text
37 passed
```

---

## 33. Mise à jour — Nouveau Dashboard Admin et activité réelle

### 33.1 Refonte UI

Le frontend a été redesigné dans une direction « dashboard professionnel » :

- sidebar structurée par sections ;
- topbar compacte ;
- cartes KPI ;
- Documents récents ;
- Actions rapides ;
- Conversations récentes ;
- section Activité ;
- section Activité récente ;
- design blanc / slate avec accent violet ;
- cartes arrondies, bordures fines et ombres légères.

Le principe retenu est de ne jamais afficher de statistiques fictives : seules les données réelles sont utilisées ; sinon l'interface affiche un état vide ou « Non disponible ».

### 33.2 Activity Logs persistants

Une couche d'activité applicative a été ajoutée en SQLite.

Les événements suivis incluent notamment :

```text
CHAT_MESSAGE
DOCUMENT_UPLOAD
DOCUMENT_DELETE
LEAVE_CREATED
LEAVE_ACCEPTED
LEAVE_REJECTED
```

Les logs stockent des métadonnées minimales utiles à l'audit, sans enregistrer les mots de passe, tokens Firebase, secrets ou contenu complet sensible des messages.

### 33.3 Endpoint activité admin

Le Dashboard utilise maintenant une API d'activité réelle :

```http
GET /api/admin/activity
```

avec une fenêtre glissante, par défaut :

```text
7 derniers jours
```

Le backend agrège les événements par jour et complète les jours sans activité avec `0`.

### 33.4 Graphique réel

La section « Activité (7 derniers jours) » n'est plus un placeholder.

Elle est alimentée par les logs SQLite et représente les événements réels, par exemple :

- conversations ;
- documents ;
- activité RH.

La fenêtre « 7 derniers jours » est glissante : elle ne nécessite pas d'attendre sept jours pour fonctionner.

### 33.5 Activité récente

La carte latérale affiche les événements récents réellement enregistrés, par exemple une nouvelle demande de congé.

Le comportement a été validé manuellement après création d'une demande : le graphique RH et l'activité récente ont été mis à jour.

---

## 34. Mise à jour — Lecture DOCX structurée et amélioration du RAG Formation

### 34.1 Problème détecté avec les tableaux DOCX

Un document professionnel de démonstration :

```text
Politique_Formation_Certification_Numerique_Demo.docx
```

a servi de test avancé.

Il contenait notamment :

- un crédit indicatif de 4 jours de formation par année civile ;
- un délai de soumission de 10 jours ouvrés ;
- une session cybersécurité chaque mercredi à 10 h 00 pendant 90 minutes ;
- des règles de remboursement de certification ;
- un plafond de 2 500 MAD ;
- un exemple de remboursement de 2 400 MAD pour une certification de 3 000 MAD.

Les tableaux étaient auparavant aplatis sous forme de cellules séparées par `|`, ce qui réduisait le contexte sémantique.

### 34.2 Reader DOCX partagé

Un nouveau reader partagé a été créé :

```text
Backend/services/rag/docx_reader.py
```

Il extrait :

- paragraphes ;
- tableaux ;
- cellules non vides ;
- lignes structurées avec leurs en-têtes ;
- contenu sans duplication inutile.

Exemple :

```text
Élément: Frais d’examen
Règle de démonstration: Remboursement à hauteur de 80 % après réussite
Limite: 2 500 MAD par certification
```

`document_ingestion.py` et `seed_documents.py` réutilisent désormais cette logique commune.

### 34.3 Classification Formation

Les mots-clés de classification `training` ont été renforcés avec des termes comme :

```text
certification
certificat
certif
```

Le document de formation/certification est donc correctement classé :

```text
training
```

### 34.4 Réingestion ciblée

La réingestion du document est ciblée et ne nécessite pas de reset global ChromaDB.

Le document de test a produit :

```text
10 chunks
```

### 34.5 Validation retrieval

Des tests ont confirmé la récupération correcte de passages contenant :

```text
4 jours de formation par année civile
80 %
2 500 MAD
2 400 MAD
```

Le chatbot a également répondu correctement au cas :

```text
Certification payée : 3 000 MAD
Remboursement : 80 %
Calcul : 2 400 MAD
Plafond : 2 500 MAD
Montant final : 2 400 MAD
```

La valeur n'est pas hardcodée : elle provient du document RAG.

---

## 35. Mise à jour — Routing RAG Formation / Procédures

### 35.1 Bug de catégorie

Une question telle que :

```text
Qui valide une demande de formation après l’employé ?
```

était parfois routée en :

```text
hr_procedure
```

alors que le document concerné était indexé en :

```text
training
```

Le filtre excluait donc le bon chunk.

### 35.2 Normalisation de catégorie

Une normalisation a été ajoutée afin que les procédures explicitement liées à la formation/certification soient routées vers `training`.

Un fallback contrôlé peut également basculer de `hr_procedure` vers `training` lorsqu'une recherche de procédure de formation ne retourne aucun résultat.

### 35.3 Reranking des chunks procéduraux

Pour les questions de procédure formation, un reranking générique favorise les chunks contenant des marqueurs structurels tels que :

```text
Étape
Responsable
Délai cible
Action
Soumettre
avant la session
```

Cela permet de prioriser les tableaux de processus plutôt que des exemples sémantiquement proches.

### 35.4 Normalisation MCP end-to-end

Le correctif a ensuite été étendu à la chaîne réelle :

```text
Frontend
  ↓
ChatService
  ↓
Qwen
  ↓
MCP
  ↓
search_documents
  ↓
RAG
```

Pour une intention explicite `training + procedure` :

- la catégorie est normalisée en `training` ;
- `top_k` est porté à `8` ;
- `similarity_threshold` est stabilisé à `0.5` ;
- la question utilisateur originale est conservée si la reformulation du LLM devient trop vague ;
- un contexte RAG est préchargé avant que le modèle ne puisse conclure prématurément à l'absence d'information.

### 35.5 Validation frontend réelle

Les reformulations suivantes ont été testées depuis le frontend réel :

```text
Quel est le délai minimum pour soumettre une demande de formation ?
Quand dois-je soumettre ma demande de formation ?
Quel préavis faut-il respecter pour une formation ?
```

Elles retournent maintenant toutes correctement :

```text
Au moins 10 jours ouvrés avant la session.
```

D'autres questions validées :

```text
Qui valide après l’employé ? → Manager
Qui intervient après le manager ? → RH / Administration
Combien de temps le manager a-t-il pour valider ? → 3 jours ouvrés
```

Le comportement a donc été validé end-to-end et non uniquement via retrieval direct.

---

## 36. État fonctionnel global actualisé — 15 août 2026

### Fonctionnel / validé

```text
[x] React + TypeScript + Tailwind CSS
[x] Firebase Authentication
[x] Firebase ID Token
[x] Firebase Custom Claims
[x] rôles employee / manager / admin
[x] protections backend 401 / 403
[x] require_admin
[x] require_manager_or_admin

[x] Chat RH sécurisé
[x] LangGraph ReAct
[x] Qwen3:8b via Ollama
[x] MCP dynamique
[x] search_documents
[x] soumettre_demande_conge

[x] RAG + ChromaDB
[x] nomic-embed-text
[x] ingestion TXT / PDF / DOCX
[x] lecture DOCX paragraphes + tableaux structurés
[x] classification documentaire
[x] routing training / procedure renforcé
[x] reranking des chunks procéduraux
[x] validation frontend des reformulations formation
[x] grounding strict et fallback d'information absente

[x] workflow congé complet
[x] SQLite
[x] demande_id dynamique
[x] notifications n8n manager / employé
[x] Mes demandes
[x] Espace Manager
[x] acceptation / refus

[x] page Documents admin-only
[x] GET /api/documents
[x] POST /api/documents/upload
[x] DELETE /api/documents/{filename}
[x] ingestion immédiate après upload
[x] suppression RAG ciblée
[x] validation upload → chat → delete → absence retrieval

[x] page Paramètres
[x] changement de mot de passe Firebase
[x] GET /api/admin/system-status
[x] statut Ollama / RAG / n8n dynamique

[x] Dashboard admin-only
[x] KPI basés sur données réelles
[x] graphique Activité 7 jours réel
[x] Activity Logs SQLite
[x] Activité récente
[x] fallback dashboard → chat pour employee/manager

[x] tests RBAC multi-rôles
[x] tests RAG formation/procédure
[x] tests d'intégration
[x] frontend build OK
[x] frontend lint OK
```

### Dernier état des tests

Après les corrections RAG Formation / procédure, la suite backend a atteint :

```text
69 passed
```

Les warnings restants sont principalement des warnings de dépréciation, notamment autour de `datetime.utcnow`, Chroma/LangChain. Ils ne sont pas bloquants actuellement.

---

## 37. Mise à jour — Page Demande de congé finalisée

### 37.1 Refonte UI

La page **Demande de congé** a été redesignée afin de rester cohérente avec le nouveau Dashboard MEFai.

La page comporte maintenant :

- un header clair ;
- des cartes de synthèse basées sur les demandes réelles ;
- un formulaire principal structuré ;
- un récapitulatif dynamique de la demande ;
- un rappel du processus de validation ;
- une zone d’aide ;
- des états de chargement, succès et erreur ;
- un design responsive cohérent avec le reste de l’application.

Aucune donnée métier fictive n’a été ajoutée.

### 37.2 Workflow conservé

La refonte ne modifie pas le fonctionnement métier existant :

```text
Utilisateur
   ↓
LeaveRequestForm
   ↓
Firebase ID Token
   ↓
POST /api/conges
   ↓
FastAPI / Pydantic
   ↓
n8n
   ↓
SQLite
statut = pending
   ↓
Espace Manager
   ↓
accepted / rejected
   ↓
notification employé
   ↓
Mes demandes
```

### 37.3 Validation manuelle

Le scénario suivant a été validé depuis l’interface réelle :

```text
[x] création d'une demande
[x] statut pending
[x] apparition dans Espace Manager
[x] acceptation / refus
[x] mise à jour de Mes demandes
[x] workflow n8n conservé
[x] persistance SQLite conservée
```

La page Demande de congé peut donc être considérée comme validée fonctionnellement et visuellement dans l’état actuel du projet.

---

## 38. Mise à jour — Audit Logs administrateur

### 38.1 Objectif

Une vraie page **Audit Logs** réservée à l’administrateur a été ajoutée afin d’exploiter les événements déjà persistés dans SQLite.

La fonctionnalité ne repose sur aucune donnée mock.

### 38.2 Endpoint

Un endpoint administrateur protégé a été ajouté :

```http
GET /api/admin/audit-logs
```

Paramètres supportés :

```text
page
page_size
action
role
resource
user
date_from
date_to
```

La requête utilise SQLAlchemy avec filtres côté base, `LIMIT`, `OFFSET` et `COUNT`.

Les résultats sont triés par :

```text
created_at DESC
```

### 38.3 Protection RBAC

La route est protégée avec :

```python
require_admin
```

Comportement attendu et validé par les tests :

```text
Sans authentification → 401
Employee → 403
Manager → 403
Admin → 200
```

Le frontend applique également :

- affichage du menu Audit Logs uniquement pour l’admin ;
- protection du rendu dans `App.tsx` ;
- fallback vers le chat pour employee/manager.

### 38.4 Page React

Un composant dédié a été créé :

```text
Frontend/src/components/Admin/AuditLogsPage.tsx
```

La page contient notamment :

- filtres serveur ;
- table desktop ;
- cards mobile ;
- pagination réelle ;
- modal de détails ;
- badges pour actions et rôles ;
- loading state ;
- empty state ;
- error state ;
- retry ;
- recherche utilisateur/email ;
- filtres date/action/rôle/ressource.

### 38.5 Données et confidentialité

Les événements affichés comprennent notamment :

```text
CHAT_MESSAGE
DOCUMENT_UPLOAD
DOCUMENT_DELETE
LEAVE_CREATED
LEAVE_ACCEPTED
LEAVE_REJECTED
```

Les données sensibles sont minimisées.

Ne sont pas exposés dans les Audit Logs :

- mot de passe ;
- Firebase ID Token ;
- Authorization header ;
- secret n8n ;
- contenu complet sensible du chat ;
- prompt système.

Pour les messages du chat, des métadonnées minimales sont utilisées plutôt que le texte complet.

### 38.6 Tests automatisés

Les tests couvrent notamment :

- accès admin ;
- employee `403` ;
- manager `403` ;
- sans authentification `401` ;
- tri `created_at DESC` ;
- pagination ;
- filtre action ;
- filtre rôle ;
- filtre ressource ;
- recherche utilisateur/email ;
- plage de dates ;
- aucun résultat ;
- sérialisation/redaction des détails ;
- matrice RBAC mise à jour.

Après cette implémentation :

```text
84 passed
```

Le frontend reste également valide :

```text
npm run build → OK
npm run lint  → OK
```

### 38.7 Incident de routing observé et corrigé

Lors du premier test navigateur, la page Audit Logs affichait :

```text
404 Not Found
```

La cause n’était pas le code de routing mais une ancienne instance Uvicorn encore active sur le port `8000`.

La route réelle était bien :

```http
GET /api/admin/audit-logs
```

Après arrêt de l’ancien processus et redémarrage du backend actuel :

- `/openapi.json` contient `/api/admin/audit-logs` ;
- une requête sans token retourne `401` au lieu de `404` ;
- l’interface récupère correctement les événements.

Un conflit de port Windows `WinError 10048` a également été résolu en arrêtant le processus qui occupait déjà `127.0.0.1:8000`.

### 38.8 Validation manuelle réelle

La page a ensuite été validée dans le navigateur avec un compte admin réel.

Résultat :

```text
[x] page chargée
[x] événements affichés
[x] pagination affichée
[x] filtres disponibles
[x] données SQLite réelles
[x] événements réels visibles après utilisation de l’application
[x] Audit Logs réservé à l’admin
```

La fonctionnalité **Audit Logs** peut donc être considérée comme validée end-to-end.

---

## 39. État fonctionnel global actualisé — 15 août 2026

### Fonctionnel / validé

```text
[x] React + TypeScript + Tailwind CSS
[x] Firebase Authentication
[x] Firebase ID Token
[x] Firebase Custom Claims
[x] rôles employee / manager / admin
[x] protections backend 401 / 403
[x] require_admin
[x] require_manager_or_admin

[x] Chat RH sécurisé
[x] LangGraph ReAct
[x] Qwen3:8b via Ollama
[x] MCP dynamique
[x] search_documents
[x] soumettre_demande_conge

[x] RAG + ChromaDB
[x] nomic-embed-text
[x] ingestion TXT / PDF / DOCX
[x] lecture DOCX paragraphes + tableaux structurés
[x] classification documentaire
[x] routing training / procedure renforcé
[x] reranking des chunks procéduraux
[x] validation frontend des reformulations formation
[x] grounding strict et fallback d'information absente

[x] workflow congé complet
[x] SQLite
[x] demande_id dynamique
[x] notifications n8n manager / employé
[x] Mes demandes
[x] Espace Manager
[x] acceptation / refus
[x] page Demande de congé redesignée et validée

[x] page Documents admin-only
[x] GET /api/documents
[x] POST /api/documents/upload
[x] DELETE /api/documents/{filename}
[x] ingestion immédiate après upload
[x] suppression RAG ciblée
[x] validation upload → chat → delete → absence retrieval

[x] page Paramètres
[x] changement de mot de passe Firebase
[x] GET /api/admin/system-status
[x] statut Ollama / RAG / n8n dynamique

[x] Dashboard admin-only
[x] KPI basés sur données réelles
[x] graphique Activité 7 jours réel
[x] Activity Logs SQLite
[x] Activité récente
[x] fallback dashboard → chat pour employee/manager

[x] page Audit Logs admin-only
[x] GET /api/admin/audit-logs
[x] pagination Audit Logs
[x] filtres Audit Logs
[x] redaction des détails sensibles
[x] validation navigateur réelle des Audit Logs

[x] tests RBAC multi-rôles
[x] tests RAG formation/procédure
[x] tests Audit Logs
[x] tests d'intégration
[x] backend : 84 passed
[x] frontend build OK
[x] frontend lint OK
```

---

## 40. Points encore à poursuivre

Les prochaines priorités sont maintenant :

```text
[ ] Durcissement final des webhooks n8n
[ ] Gestion avancée des utilisateurs / rôles
[ ] Permissions fines par document RAG
[ ] Monitoring détaillé
[ ] Gestion réelle des pièces jointes
[ ] Migration OllamaEmbeddings vers langchain-ollama
[ ] Réduction progressive des warnings de dépréciation
```

### Prochaine priorité recommandée

La prochaine étape technique recommandée est :

```text
Durcissement sécurité des webhooks n8n
```

Objectifs prévus :

- authentification du webhook ;
- validation d’un secret côté n8n ;
- refus des appels non autorisés ;
- validation stricte des payloads ;
- réduction de l’exposition du webhook ;
- logs sans secrets ;
- tests des appels sans token / token invalide / token valide ;
- réflexion sur rate limiting et anti-replay si nécessaire.

Après cette étape :

```text
1. Gestion utilisateurs / rôles avancés
2. Permissions fines sur les documents
3. Monitoring
4. Gestion des pièces jointes
5. Migration vers langchain-ollama
```

---

## 41. Résumé exécutif final actualisé

MEFai est maintenant un PoC RH souverain fonctionnel combinant :

```text
React / TypeScript / Tailwind
        +
Firebase Authentication / RBAC
        +
FastAPI
        +
LangGraph ReAct
        +
MCP
        +
RAG / ChromaDB
        +
Ollama
        +
Qwen3:8b
        +
nomic-embed-text
        +
SQLite
        +
n8n
```

Les principaux flux validés sont désormais :

```text
1. Question RH → Agent → MCP → RAG → Qwen → réponse sourcée

2. Document Admin
   → Upload
   → Ingestion RAG
   → Recherche
   → Suppression ciblée

3. Demande de congé
   → n8n
   → SQLite
   → Manager
   → Décision
   → notification employé

4. Dashboard Admin
   → System Status
   → Activity Logs
   → données réelles

5. Audit Logs Admin
   → SQLite
   → filtres/pagination
   → détails minimisés
   → validation navigateur

6. RBAC employee / manager / admin
   → navigation conditionnelle
   → protections frontend
   → protections backend 401/403
```

Le projet a désormais dépassé la phase de simple PoC technique. Il dispose de plusieurs flux métier et d’administration validés de bout en bout.

La phase actuelle est principalement une phase de **durcissement sécurité, gouvernance, monitoring et gestion avancée des permissions**.

---

## 42. Mise à jour — Résolution dynamique du manager pour les congés

### 42.1 Problème initial

Le workflow n8n utilisait auparavant une adresse manager statique / de test.

Cela pouvait conduire à un envoi vers une adresse obsolète telle que :

```text
manager@test.com
```

Le comportement a été corrigé afin que le manager soit maintenant déterminé côté backend.

### 42.2 Résolution côté Firebase

Le backend utilise désormais Firebase Admin SDK pour rechercher un utilisateur ayant :

```text
custom_claims["role"] == "manager"
```

avec une adresse email valide.

Si plusieurs managers sont présents, la sélection est déterministe : les emails valides sont triés alphabétiquement et le premier est utilisé.

Le frontend ne fournit jamais `manager_email`.

`manager_email` n'est pas exposé dans le modèle public `DemandeConge`.

Le flux devient :

```text
Utilisateur
   ↓
POST /api/conges
   ↓
Firebase Authentication
   ↓
Backend résout le manager réel
   ↓
manager_email ajouté uniquement au payload interne
   ↓
n8n
   ↓
email manager
```

### 42.3 Cas sans manager

Si aucun manager valide n'est disponible :

```text
HTTP 422
Aucun manager valide n'est configuré pour recevoir la demande.
```

Dans ce cas, n8n n'est pas appelé et aucun faux succès n'est renvoyé.

---

## 43. Mise à jour — Service commun de soumission de congé

Une couche métier commune a été ajoutée :

```text
Backend/services/workflows/leave_submission_service.py
```

Elle centralise la logique de soumission afin d'éviter toute duplication entre :

- la page Demande de congé ;
- le Chat IA.

La logique commune comprend maintenant :

```text
1. validation des données
2. résolution du manager Firebase
3. appel n8n
4. récupération de demande_id
5. persistance SQLite
6. statut pending
7. Activity/Audit Log LEAVE_CREATED
8. exposition dans Mes demandes
9. exposition dans Espace Manager
```

La page et le Chat IA passent donc par le même pipeline métier.

---

## 44. Mise à jour — Demande de congé depuis le Chat IA

Le Chat IA peut désormais créer une vraie demande de congé, pas seulement informer l'utilisateur.

### 44.1 Comportement

Lorsqu'une intention claire est détectée, par exemple :

```text
Je veux demander un congé du 20 au 24 août.
Pose-moi un congé annuel du 3 au 5 septembre.
Je veux prendre deux jours de congé.
```

l'agent réutilise le tool de soumission de congé existant.

Aucun workflow parallèle n'a été créé.

### 44.2 Informations nécessaires

La demande n'est soumise que lorsque les champs requis sont disponibles :

```text
employe_id
type_conge
date_debut
date_fin
motif
```

Si une information manque, l'agent demande uniquement les informations manquantes.

Il ne doit jamais :

- inventer un champ ;
- inventer un manager ;
- accepter `manager_email` depuis le Chat ;
- annoncer un succès si n8n a échoué.

### 44.3 Résultat

Après création depuis le Chat :

```text
[x] demande_id réelle
[x] statut pending
[x] sauvegarde SQLite
[x] apparition dans Mes demandes
[x] apparition dans Espace Manager
[x] manager dynamique
[x] email n8n
[x] accept / reject
[x] notification employé
```

La soumission depuis le Chat a été validée manuellement end-to-end.

---

## 45. Mise à jour — Correction du workflow n8n de soumission

### 45.1 Problème de destinataire

Le node `Send an Email` utilisait initialement un destinataire statique ou n'arrivait pas à résoudre le destinataire.

Le champ `To Email` utilise maintenant la valeur dynamique provenant du backend :

```text
manager_email
```

Le manager réel est donc transmis par FastAPI et utilisé par n8n.

### 45.2 Problème de réponse n8n

Le backend recevait auparavant :

```text
HTTP 200
body vide
```

puis tentait :

```python
response.json()
```

ce qui provoquait :

```text
JSONDecodeError
500 Internal Server Error
```

Le backend a été renforcé afin de détecter :

- body vide ;
- JSON invalide ;
- format inattendu ;
- absence de `demande_id`.

Une réponse n8n invalide produit désormais une erreur contrôlée au lieu d'un crash JSON générique.

### 45.3 Pipeline n8n final

Le workflow de soumission est maintenant organisé comme suit :

```text
Webhook
   ↓
Valider demande de congé
   ↓
If
   ├── false → Respond to Webhook erreur
   │
   └── true
        ↓
     Send an Email
        ↓
     Préparer réponse
        ↓
     Respond to Webhook success
```

Le node `Préparer réponse` prépare notamment :

```text
demande_id
statut
message
```

Le backend reçoit désormais une vraie référence du type :

```text
REQ-1786830808118
```

au lieu d'une expression n8n affichée littéralement.

---

## 46. Validation end-to-end du workflow congé multi-entry

Le workflow complet a été validé avec les deux entrées :

```text
A. Page Demande de congé
B. Chat IA
```

Résultat :

```text
[x] manager réel résolu via Firebase
[x] email envoyé au bon manager
[x] n8n retourne une réponse exploitable
[x] demande_id dynamique
[x] statut pending
[x] persistance SQLite
[x] Mes demandes
[x] Espace Manager
[x] accept / reject
[x] notification employé
[x] Audit Log LEAVE_CREATED
[x] même logique métier pour page et Chat
```

Le workflow congé multi-entry peut être considéré comme validé end-to-end.

---

## 47. Tests automatisés — état actualisé

Après les corrections manager dynamique / service commun / Chat IA / n8n :

```text
97 tests passed
```

Les nouveaux tests couvrent notamment :

- manager Firebase trouvé ;
- manager transmis à n8n ;
- absence de manager ;
- rôles non-manager ignorés ;
- manager sans email ignoré ;
- sélection déterministe de plusieurs managers ;
- `manager_email` rejeté côté payload public ;
- injection interne de `manager_email` ;
- Chat IA avec intention de congé complète ;
- champs manquants ;
- persistance SQLite ;
- visibilité employee / manager ;
- accept / reject ;
- erreur n8n sans faux succès.

---

## 48. État fonctionnel global actualisé — 15 août 2026

### Fonctionnel / validé

```text
[x] React + TypeScript + Tailwind CSS
[x] Firebase Authentication
[x] Firebase Admin SDK
[x] Firebase Custom Claims
[x] RBAC employee / manager / admin

[x] FastAPI
[x] SQLite
[x] LangGraph ReAct
[x] MCP
[x] Ollama
[x] Qwen3:8b
[x] ChromaDB
[x] nomic-embed-text

[x] Chat RH avec grounding RAG strict
[x] ingestion TXT / PDF / DOCX
[x] lecture DOCX structurée
[x] routing training / procedure renforcé

[x] workflow congé via page
[x] workflow congé via Chat IA
[x] service commun de soumission
[x] manager dynamique Firebase
[x] manager_email server-side uniquement
[x] n8n email manager
[x] demande_id dynamique
[x] persistance pending
[x] Mes demandes
[x] Espace Manager
[x] acceptation / refus
[x] notification employé

[x] Documents admin-only
[x] upload / ingestion / suppression ciblée
[x] Dashboard admin
[x] System Status
[x] Activity Logs
[x] Audit Logs admin-only
[x] pagination / filtres / redaction

[x] 97 tests backend passés
[x] frontend build OK
[x] frontend lint OK
```

---

## 49. Priorités suivantes

La prochaine priorité recommandée reste :

```text
Durcissement sécurité des webhooks n8n
```

À traiter ensuite :

```text
1. authentification webhook renforcée
2. validation stricte des payloads
3. gestion propre des secrets
4. protection anti-replay si pertinente
5. rate limiting si pertinent
6. logs sans secrets
7. tests sécurité webhook
8. Docker / Docker Compose
9. CI/CD
10. monitoring / observabilité
11. gestion avancée des utilisateurs et rôles
12. permissions fines sur les documents RAG
13. migration OllamaEmbeddings vers langchain-ollama
```

---

## 50. Résumé exécutif actualisé

MEFai est maintenant une plateforme RH IA multi-flux avec :

```text
React / TypeScript
        +
Firebase Auth / RBAC
        +
FastAPI
        +
LangGraph
        +
MCP
        +
RAG / ChromaDB
        +
Ollama / Qwen3:8b
        +
SQLite
        +
n8n
```

Le projet ne se limite plus à un assistant conversationnel.

Il supporte maintenant un workflow métier transactionnel réel accessible depuis :

```text
Page Demande de congé
        +
Chat IA
```

avec :

```text
résolution manager
→ orchestration n8n
→ persistance SQLite
→ validation manager
→ notification employé
→ audit
```

Le projet dispose désormais d'une base solide pour une phase de hardening sécurité, DevOps et industrialisation.

---

## 51. Mise à jour — Historique Chat persistant et isolé par utilisateur

### 51.1 Bugs corrigés

Deux problèmes ont été corrigés :

1. Une conversation créée par un employee pouvait rester visible après logout/login avec un manager.
2. L'historique pouvait disparaître après refresh ou redémarrage de localhost.

La cause était l'utilisation d'un historique uniquement conservé dans l'état React de `useChat`, sans persistance serveur ni isolation stricte par Firebase UID.

### 51.2 Persistance SQLite

Un nouveau modèle a été ajouté :

```text
Backend/chat_models.py
```

avec :

```text
ConversationModel
- id
- user_uid
- title
- created_at
- updated_at

ChatMessageModel
- id
- conversation_id
- role
- content
- created_at
```

La base SQLite existante reste la source de vérité.

### 51.3 Endpoints conversations

Les endpoints suivants ont été ajoutés :

```http
GET    /api/conversations
POST   /api/conversations
GET    /api/conversations/{conversation_id}
DELETE /api/conversations/{conversation_id}
POST   /api/chat
```

`POST /api/chat` accepte désormais `conversation_id`.

### 51.4 Isolation par Firebase UID

Toutes les conversations sont filtrées côté serveur via :

```python
user_uid = user["uid"]
```

Un utilisateur ne peut pas lire, supprimer ou écrire dans une conversation appartenant à un autre UID.

Un accès direct à une conversation étrangère retourne `404` afin de ne pas révéler inutilement son existence.

### 51.5 Frontend

`Frontend/src/hooks/useChat.ts` charge maintenant l'historique depuis le backend.

Au changement d'utilisateur ou au logout :

```text
[x] état Chat vidé immédiatement
[x] historique du nouvel utilisateur rechargé
[x] garde anti-race basée sur user.uid
[x] ancienne réponse réseau empêchée de réinjecter l'historique précédent
```

Le backend SQLite est désormais la source de vérité.

### 51.6 Chat + congé

La demande de congé depuis le Chat continue d'utiliser le workflow métier existant.

Le message utilisateur et la réponse assistant sont persistés dans la conversation.

### 51.7 Validation

Après cette implémentation :

```text
113 tests passed
```

Frontend :

```text
npm run build -> OK
npm run lint  -> OK
```

Les tests couvrent notamment :

- création de conversation ;
- isolation employee / manager / admin ;
- accès direct à une conversation étrangère refusé ;
- suppression étrangère refusée ;
- ordre des messages ;
- ordre des conversations par `updated_at DESC` ;
- persistance après nouvelle session DB ;
- persistance user + assistant via `POST /api/chat` ;
- compatibilité avec le workflow congé ;
- accès non authentifié `401`.

---

## 52. Mise à jour — RBAC strict des décisions de congé

### 52.1 Règle métier finale

La règle finale est désormais :

```text
Seul role="manager" peut accepter ou refuser une demande de congé.
```

L'admin ne peut plus agir comme manager.

### 52.2 Backend

Une dépendance stricte a été ajoutée :

```python
require_manager
```

Elle autorise uniquement :

```text
role == "manager"
```

Elle protège :

```http
GET   /api/manager/conges
PATCH /api/manager/conges/{demande_id}
```

Comportement :

```text
Manager          -> 200
Admin            -> 403
Employee         -> 403
Non authentifié  -> 401
```

### 52.3 Frontend

Navigation finale :

Employee :

```text
Chat IA
Demande de congé
Mes demandes
Paramètres
```

Manager :

```text
Chat IA
Demande de congé
Mes demandes
Espace Manager
Paramètres
```

Admin :

```text
Tableau de bord
Chat IA
Demande de congé
Mes demandes
Administration
Documents
Audit Logs
Paramètres
```

`Espace Manager` n'apparaît plus pour l'admin.

Dans `App.tsx`, la page manager est rendue uniquement si :

```text
role === "manager"
```

Si employee ou admin se retrouve avec `activePage="manager"`, fallback vers le Chat.

Le Dashboard admin n'appelle plus les endpoints manager.

### 52.4 Audit

Les événements restent :

```text
LEAVE_ACCEPTED
LEAVE_REJECTED
```

mais ils sont désormais générés uniquement lorsqu'un vrai manager prend la décision.

### 52.5 Validation

Après cette mise à jour :

```text
115 tests passed
```

Frontend :

```text
npm run build -> OK
npm run lint  -> OK
```

Les tests valident notamment :

```text
GET /api/manager/conges:
- unauthenticated -> 401
- employee -> 403
- admin -> 403
- manager -> 200

PATCH /api/manager/conges/{id}:
- unauthenticated -> 401
- employee -> 403
- admin -> 403
- manager -> 200
```

Les accès admin existants restent valides :

```text
Dashboard
Documents
Activity
Audit Logs
System Status
Administration
```

---

## 53. État global actualisé — 16 août 2026

### Fonctionnalités validées

```text
[x] React + TypeScript + Tailwind CSS
[x] Firebase Authentication
[x] Firebase Admin SDK
[x] Firebase Custom Claims
[x] RBAC employee / manager / admin
[x] require_admin
[x] require_manager

[x] FastAPI
[x] SQLite
[x] LangGraph ReAct
[x] MCP
[x] Ollama
[x] Qwen3:8b
[x] ChromaDB
[x] nomic-embed-text

[x] Chat RH grounded par RAG
[x] conversations persistantes SQLite
[x] historique isolé par Firebase UID
[x] restauration après refresh / restart
[x] changement d'utilisateur sans fuite de conversation

[x] ingestion TXT / PDF / DOCX
[x] lecture DOCX structurée
[x] routing training / procedure renforcé
[x] fallback RAG global category=None
[x] query originale préservée pour le retrieval
[x] questions de suivi contextualisées
[x] reranking lexical générique codes / montants / durées / matériel
[x] candidate pool RAG élargi avant reranking
[x] chemin ChromaDB absolu et centralisé
[x] upload document immédiatement interrogeable sans restart
[x] suppression document immédiatement répercutée dans le RAG

[x] demande de congé depuis la page
[x] demande de congé depuis le Chat IA
[x] service commun de soumission
[x] manager dynamique Firebase
[x] manager_email injecté uniquement côté serveur
[x] n8n email manager
[x] demande_id dynamique
[x] statut pending
[x] Mes demandes
[x] Espace Manager réservé au manager
[x] accept / reject réservé au manager
[x] notification employé accept / reject validée réellement
[x] template email décision MEFai final validé
[x] Audit Log LEAVE_CREATED / ACCEPTED / REJECTED

[x] Documents admin-only
[x] upload / ingestion / suppression ciblée
[x] Dashboard admin
[x] System Status
[x] Activity Logs
[x] Audit Logs admin-only
[x] pagination / filtres / redaction

[x] backend : 138 tests passed
[x] frontend build OK
[x] frontend lint OK
```

---

## 54. Priorités suivantes

La prochaine priorité technique reste :

```text
Durcissement sécurité des webhooks n8n
```

Puis :

```text
1. Docker / Docker Compose
2. CI/CD
3. Monitoring / observabilité
4. Gestion avancée des utilisateurs et rôles
5. Permissions fines sur les documents RAG
6. Gestion éventuelle de plusieurs managers / affectation explicite
7. Migration OllamaEmbeddings -> langchain-ollama
8. Réduction des warnings de dépréciation
```

---

## 55. Résumé exécutif actualisé

MEFai dispose désormais de plusieurs caractéristiques de niveau application professionnelle :

```text
Authentification multi-rôles
+
Isolation des données par utilisateur
+
Historique conversationnel persistant
+
RAG documentaire
+
Agent transactionnel
+
Workflow congé multi-entry
+
Manager dynamique
+
RBAC strict des décisions
+
Audit Logs
+
Administration
+
Tests automatisés
```

Le Chat IA n'est plus un simple chatbot stateless.

Il possède maintenant un historique persistant, isolé par utilisateur Firebase, et peut déclencher un workflow métier réel de demande de congé tout en respectant les règles RBAC.

L'admin conserve ses fonctions d'administration et d'audit, tandis que les décisions de congé sont maintenant strictement réservées au rôle manager.

État de validation actuel :

```text
138 tests backend passés
Frontend build OK
Frontend lint OK
```

Le projet est prêt pour une phase de durcissement sécurité et d'industrialisation DevOps.

---

## 56. Mise à jour — Robustesse RAG générique après upload dynamique

### 56.1 Problème observé

Après l'ajout de nouveaux documents depuis la page `Documents`, l'upload et l'indexation pouvaient réussir alors que le Chat IA retournait encore :

```text
Les documents internes actuels ne précisent pas cette information.
```

Le problème n'était pas limité à un document particulier.

Des tests avec des documents de mobilité interne puis d'équipement informatique ont montré que les chunks existaient bien dans ChromaDB, mais pouvaient être exclus ou classés trop bas lors du retrieval.

### 56.2 Correction du fallback de catégorie

Le pipeline RAG est désormais moins dépendant d'un filtre de catégorie trop strict.

Comportement générique :

```text
Question utilisateur
    ↓
Recherche avec catégorie pertinente si elle est fiable
    ↓
Si résultat vide ou insuffisamment pertinent
    ↓
Recherche globale category=None
    ↓
Fusion / déduplication
    ↓
Reranking lexical léger
    ↓
Contexte RAG
```

Les catégories telles que :

```text
other
general
unknown
```

ne bloquent plus l'accès à un document nouvellement indexé.

### 56.3 Paramètres génériques

Pour les recherches documentaires génériques :

```text
top_k catégorisé : minimum 8
fallback global  : minimum 10
similarity_threshold générique : 0.35
```

Les cas `training/procedure` conservent leur comportement spécialisé à `0.5`.

### 56.4 Candidate pool élargi

Un problème important a été détecté avec le document :

```text
politique_equipement_informatique_test.txt
```

Les bons chunks pouvaient apparaître aux rangs :

```text
13
18
20
```

dans la recherche vectorielle brute.

Un `top_k=10` les rendait donc invisibles.

`RAGService.search()` récupère maintenant un pool de candidats plus large :

```text
max(top_k, 30)
```

puis effectue le reranking avant de retourner les meilleurs résultats.

Cette correction évite de dépendre uniquement du classement vectoriel brut.

### 56.5 Reranking lexical générique

Le reranking a été renforcé pour les questions factuelles contenant notamment des marqueurs comme :

```text
code
référence
identifiant
montant
MAD
plafond
maximum
durée
jours
mois
ordinateur
matériel
équipement
accessoire
panne
support
vol
perte
renouvellement
```

Les valeurs elles-mêmes ne sont jamais hardcodées.

Le reranking sert uniquement à favoriser le chunk contenant les termes discriminants pertinents.

---

## 57. Mise à jour — Centralisation du chemin ChromaDB

### 57.1 Risque détecté

La configuration utilisait auparavant :

```text
CHROMA_PERSIST_DIR=./chroma_db
```

Ce chemin relatif dépendait du working directory du processus.

Deux bases ont été observées :

```text
C:\Users\erram\Desktop\Cortex_AI_Minist-re\chroma_db
C:\Users\erram\Desktop\Cortex_AI_Minist-re\Backend\chroma_db
```

La seconde contenait une collection stale.

### 57.2 Correction

`Backend/core/config.py` normalise désormais `CHROMA_PERSIST_DIR` en chemin absolu depuis la racine du projet.

La base active validée est :

```text
C:\Users\erram\Desktop\Cortex_AI_Minist-re\chroma_db
```

Collection :

```text
rh_documents
```

Cela garantit que :

```text
Upload
RAGService
MCP
ChatService
```

travaillent sur la même collection persistante.

### 57.3 Importance du reload backend

Un incident runtime a également montré qu'un backend lancé sans `--reload` pouvait continuer d'utiliser une ancienne version de `ChatService`.

Pendant le développement, il est donc préférable de lancer :

```powershell
python -m uvicorn app.main:app --app-dir Backend --host 127.0.0.1 --port 8000 --reload
```

afin que les corrections backend soient effectivement prises en compte.

---

## 58. Mise à jour — Questions de suivi et valeurs précises

### 58.1 Contexte conversationnel

Les questions courtes telles que :

```text
Quel est le code de référence de cette politique ?
Quel montant peut être accordé ?
Et quel est le délai ?
```

peuvent perdre le sujet métier si elles sont envoyées seules au retrieval.

`ChatService` conserve maintenant le contexte récent pertinent.

Exemple :

```text
Q1 : Combien de mois d'ancienneté faut-il avant une mobilité interne ?
Q2 : Quel est le code de référence de cette politique ?
```

La seconde recherche conserve le sujet :

```text
mobilité interne
```

Si l'historique récent contient une référence de fichier du type :

```text
[File: test_mobilite.txt]
```

le nom du fichier peut également être utilisé pour enrichir le retrieval.

### 58.2 Questions factuelles précises

Le système a été renforcé pour les recherches portant sur :

```text
codes de référence
identifiants
montants
nombres
pourcentages
dates
durées
limites
plafonds
```

Si Qwen retourne à tort un fallback alors qu'un bon chunk est disponible, un garde-fou grounded peut s'appuyer sur le meilleur résultat RAG sans inventer une valeur.

### 58.3 Nettoyage de génération

Les réponses du type :

```text
Ce délai est mentionné dans plusieurs sources :
-
-
```

ont été nettoyées.

Les puces vides ne doivent plus être générées.

---

## 59. Validation runtime — Documents dynamiques

### 59.1 Mobilité interne

Le document :

```text
test_mobilite.txt
```

a permis de valider le retrieval de :

```text
17 jours ouvrés
9 mois d'ancienneté
manager actuel puis service RH
MOB-TEST-917
1 850 MAD
```

Le runtime réel a confirmé :

```text
tools_used=['search_documents']
```

et les réponses provenaient du bon fichier.

### 59.2 Équipement informatique

Le document :

```text
politique_equipement_informatique_test.txt
```

contenait notamment :

```text
renouvellement : 4 ans
plafond accessoire : 950 MAD
panne : 24 heures
vol/perte : manager + service informatique
code : IT-EQP-2026-44
```

Avant correction, les bons chunks étaient parfois classés trop loin.

Après élargissement du candidate pool et reranking :

```text
RAGService direct -> fichier équipement rang 1
MCP réel          -> fichier équipement rang 1
ChatService réel  -> réponses correctes
```

### 59.3 Test final upload / indexation / suppression

Un document final :

```text
test_rag_final.txt
```

a été uploadé puis indexé depuis l'interface.

Valeurs de test :

```text
délai : 13 jours ouvrés
plafond accessoire ergonomique : 1 275 MAD
validation : manager puis service informatique
code : RAG-FINAL-813
renouvellement : 5 ans
```

Le Chat IA a correctement retrouvé :

```text
13 jours ouvrés
1 275 MAD
manager puis service informatique
RAG-FINAL-813
5 ans
```

La paraphrase :

```text
Combien de temps prend la demande pour du matériel spécialisé ?
```

a également retourné :

```text
13 jours ouvrés
```

Après suppression de `test_rag_final.txt`, le système ne retrouvait plus :

```text
RAG-FINAL-813
13 jours ouvrés
```

Le pipeline suivant est donc validé end-to-end :

```text
Upload fichier
    ↓
Extraction
    ↓
Chunking
    ↓
Embeddings
    ↓
Upsert ChromaDB
    ↓
Retrieval Chat IA
    ↓
Paraphrase
    ↓
Delete fichier
    ↓
Suppression ciblée Chroma
    ↓
Ancienne information non retrouvée
```

### 59.4 Point restant : contamination multi-source

Un cas a montré qu'une question sur :

```text
plafond accessoire ergonomique
```

pouvait retourner à la fois :

```text
1 275 MAD
```

depuis `test_rag_final.txt` et :

```text
950 MAD
```

depuis un autre document d'équipement.

Le retrieval du bon document fonctionne, mais la synthèse multi-source peut encore être rendue plus stricte lorsqu'une source précise suffit.

Ce point est une amélioration de qualité de réponse, pas un problème d'indexation.

---

## 60. Mise à jour — Notifications employé après décision manager

### 60.1 Diagnostic

Le workflow de congé fonctionnait jusqu'à la décision manager :

```text
création demande
→ pending
→ Espace Manager
→ accept / reject
```

mais l'email employé n'était plus visible dans la boîte de réception.

Les exécutions n8n montraient pourtant :

```text
accepted: [adresse_employe]
response: 250 2.0.0 OK ... gsmtp
messageId présent
```

Cela confirmait :

```text
Backend -> n8n -> SMTP/Gmail = OK
```

### 60.2 Cause isolée

Un email de test minimal utilisant le même node et les mêmes credentials arrivait correctement.

Le problème était donc lié à l'ancien template `Subject/HTML` de notification, et non :

```text
au webhook
au backend
au destinataire
aux credentials SMTP
```

### 60.3 Template final

Le template a été reconstruit sur une base simple et validée, avec :

```text
header MEFai violet
statut dynamique
vert pour accepted
rouge pour rejected
référence demande
texte Mes demandes
footer notification automatique
```

Le subject final reste de type :

```text
[MEFai] Mise à jour de votre demande — <demande_id>
```

Les tests réels `accepted` et `rejected` ont confirmé la réception des emails.

La notification employé après décision manager est donc de nouveau validée end-to-end.

---

## 61. Mise à jour — Conversations persistantes et Swagger

### 61.1 Contrat GET conversations

`GET /api/conversations` retourne désormais des résumés clairs appartenant uniquement au user Firebase connecté.

Exemple :

```json
[
  {
    "id": 12,
    "title": "Questions RH",
    "created_at": "2026-08-16T10:12:00Z",
    "updated_at": "2026-08-16T10:15:00Z",
    "message_count": 2
  }
]
```

Le `conversation_id` réel à utiliser est l'`id` retourné par :

```text
GET  /api/conversations
POST /api/conversations
POST /api/chat
```

### 61.2 GET par id

Comportement validé :

```text
owner correct       -> 200
conversation autre  -> 404
id inexistant       -> 404
non authentifié     -> 401
```

Le `404` cross-user évite de révéler l'existence de ressources appartenant à un autre utilisateur.

### 61.3 DELETE

`DELETE /api/conversations/{conversation_id}` retourne :

```json
{
  "message": "Conversation supprimée",
  "conversation_id": 12
}
```

Les messages associés sont supprimés via cascade SQLAlchemy.

Comportement :

```text
owner            -> 200
autre user       -> 404
id inexistant    -> 404
non authentifié  -> 401
```

Le bouton de suppression est maintenant branché dans la sidebar React.

### 61.4 Swagger Firebase Bearer

Firebase Bearer est déclaré via `HTTPBearer`.

Swagger dispose donc du bouton global :

```text
Authorize
```

avec le schéma :

```text
FirebaseBearer
```

Les anciens exemples trompeurs du type :

```text
"id": 0
"title": "string"
```

ont été remplacés par des exemples plus réalistes.

### 61.5 Isolation et persistance

Les tests valident :

```text
User A -> 2 conversations
User B -> 1 conversation
```

Chaque utilisateur ne voit que ses propres données.

L'historique reste persistant après :

```text
refresh
nouvelle session DB
restart applicatif
logout/login
```

Le frontend recharge les conversations depuis `/api/conversations` au changement d'utilisateur.

---

## 62. Validation globale actualisée — 16 août 2026

Dernier état automatisé communiqué :

```text
Backend : 138 tests passed
Frontend : npm run build -> OK
```

Les tests successifs ont évolué ainsi au fil des corrections :

```text
115 -> 119 -> 122 -> 126 -> 132 -> 138 tests passed
```

Les validations manuelles récentes couvrent notamment :

```text
[x] RAG multi-documents
[x] upload dynamique
[x] indexation immédiate
[x] retrieval sans restart
[x] paraphrases
[x] codes / montants / durées
[x] questions de suivi contextualisées
[x] suppression ciblée document
[x] RBAC employee / manager / admin
[x] workflow congé
[x] accept / reject
[x] email employé après décision
[x] historique conversationnel
[x] isolation utilisateur
[x] suppression conversation
```

Point de qualité restant identifié :

```text
[ ] rendre la synthèse multi-source plus stricte
    lorsqu'un seul document répond clairement à la question
```

Les priorités techniques de fond restent :

```text
1. Durcissement sécurité des webhooks n8n
2. Docker / Docker Compose
3. CI/CD
4. Monitoring / observabilité
5. Gestion avancée des utilisateurs et rôles
6. Permissions fines sur les documents RAG
7. Migration OllamaEmbeddings -> langchain-ollama
8. Réduction des warnings de dépréciation
```

---

## 63. Résumé exécutif final — version 8

MEFai est maintenant validé sur un périmètre fonctionnel plus large qu'en version 7.

Le système combine :

```text
React / TypeScript / Tailwind
+
Firebase Authentication / Custom Claims / RBAC
+
FastAPI
+
LangGraph ReAct
+
MCP
+
RAG / ChromaDB
+
Ollama / Qwen3:8b
+
nomic-embed-text
+
SQLite
+
n8n
```

Les deux axes récemment renforcés sont :

```text
1. RAG documentaire dynamique réellement générique
2. Persistance / isolation conversationnelle complète
```

Le RAG accepte maintenant un document nouveau, même hors catégories métier connues, l'indexe immédiatement, le retrouve via recherche globale et reranking, puis le supprime proprement de Chroma lors d'un delete.

Les conversations sont persistantes, isolées par Firebase UID, supprimables depuis l'UI, et documentées clairement dans Swagger.

Le workflow de congé reste complet :

```text
Employee
→ création demande
→ manager dynamique
→ email manager
→ pending SQLite
→ décision manager
→ accepted / rejected
→ email employé
→ statut visible
```

État final communiqué :

```text
138 tests backend passés
Frontend build OK
RBAC validé manuellement
RAG upload/index/delete validé manuellement
Notification employé accept/reject validée réellement
```

Le projet est désormais prêt pour la phase suivante de durcissement sécurité et d'industrialisation.

