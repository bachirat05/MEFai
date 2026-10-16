# Cortex AI — Assistant RH Intelligent

Cortex AI est une plateforme RH intelligente conçue comme un PoC professionnel combinant IA locale, RAG, workflows métier, authentification et administration.

## Stack technique

- React + TypeScript + Vite
- FastAPI
- Firebase Authentication
- Firebase Admin SDK
- SQLite
- LangGraph
- MCP
- Ollama
- Qwen3:8b
- ChromaDB
- nomic-embed-text
- n8n

## Fonctionnalités principales

- Chat RH intelligent basé sur les documents internes
- RAG avec ingestion TXT / PDF / DOCX
- Authentification Firebase
- RBAC multi-rôles:
  - employee
  - manager
  - admin
- Demandes de congé
- Validation manager
- Notifications via n8n
- Gestion des documents
- Dashboard administrateur
- System status
- Activity Logs
- Audit Logs
- Tests backend automatisés

---

# Installation

## 1. Cloner le projet

```bash
git clone <URL_DU_REPOSITORY>
cd Cortex_AI_Minist-re
```

Pour utiliser la branche de développement actuelle:

```bash
git fetch origin
git switch zouhair
git pull
```

## 2. Créer l'environnement Python

Sous Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Installer les dépendances:

```powershell
pip install -r requirements.txt
```

## 3. Configuration Backend

Créer le fichier `.env` utilisé par FastAPI:

```powershell
copy .env.example Backend\.env
```

Puis compléter:

```env
OPENROUTER_API_KEY=
OPENROUTER_MODEL=poolside/laguna-s-2.1:free
LLM_BASE_URL=https://openrouter.ai/api/v1

OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_BASE_URL=http://localhost:11434

CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION_NAME=rh_documents

N8N_WEBHOOK_URL=
N8N_SECRET_TOKEN=
N8N_TIMEOUT_SECONDS=15
N8N_STATUS_NOTIFICATION_WEBHOOK_URL=

SERVER_PORT=8000
```

Ne jamais commit le fichier:

```text
Backend/.env
```

## 4. Firebase Admin

Le backend utilise un Service Account Firebase.

Le fichier attendu est:

```text
Backend/firebase_admin_key.json
```

Ce fichier contient des credentials sensibles et ne doit jamais être envoyé sur GitHub.

Il doit être récupéré via une méthode sécurisée auprès d'un membre autorisé du projet.

## 5. Installer Ollama

Installer Ollama puis vérifier qu'il fonctionne.

Les modèles utilisés sont:

```bash
ollama pull qwen3:8b
ollama pull nomic-embed-text
```

Vérifier:

```bash
ollama list
```

Ollama doit être accessible sur:

```text
http://localhost:11434
```

## 6. Lancer le Backend

Depuis la racine du projet:

```powershell
python -m uvicorn app.main:app --app-dir Backend --host 127.0.0.1 --port 8000
```

API disponible sur:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## 7. Lancer le Frontend

Dans un second terminal:

```powershell
cd Frontend
npm install
npm run dev
```

Le frontend sera généralement disponible sur:

```text
http://localhost:5173
```

## 8. Lancer n8n

Le projet utilise n8n pour les workflows de congé et les notifications.

Le workflow doit être démarré séparément avec les webhooks configurés dans:

```text
Backend/.env
```

Exemple:

```env
N8N_WEBHOOK_URL=http://localhost:5678/webhook/conge-test
```

Les secrets n8n ne doivent jamais être commit.

---

# RAG

Les documents de démonstration se trouvent dans:

```text
Backend/data/documents/
```

Formats supportés:

- `.txt`
- `.pdf`
- `.docx`

La collection ChromaDB utilisée est:

```text
rh_documents
```

Pour les embeddings:

```text
nomic-embed-text
```

---

# Tests Backend

Depuis la racine:

```powershell
pytest Backend/tests
```

État de référence actuel:

```text
84 passed
```

---

# Validation Frontend

Depuis:

```powershell
cd Frontend
```

Build:

```powershell
npm run build
```

Lint:

```powershell
npm run lint
```

---

# Rôles

## Employee

Accès:

- Chat IA
- Demande de congé
- Mes demandes
- Paramètres

## Manager

Accès:

- Chat IA
- Demande de congé
- Mes demandes
- Espace Manager
- Paramètres

## Admin

Accès:

- Tableau de bord
- Chat IA
- Demande de congé
- Mes demandes
- Espace Manager
- Administration
- Documents
- Audit Logs
- Paramètres

---

# Sécurité

Ne jamais commit:

```text
.env
Backend/.env
firebase_admin_key.json
*.db
chroma_db/
.venv/
node_modules/
```

Ne jamais exposer dans le repository:

- mots de passe
- Firebase tokens
- Service Account keys
- secrets n8n
- Authorization headers
- données RH sensibles

---

# Workflow général

```text
React Frontend
      ↓
Firebase Authentication
      ↓
FastAPI Backend
      ↓
LangGraph / MCP
      ↓
RAG / ChromaDB
      ↓
Ollama / Qwen
```

Workflow congé:

```text
Employee
   ↓
FastAPI
   ↓
n8n
   ↓
SQLite
   ↓
Manager
   ↓
Accept / Reject
   ↓
Notification Employee
```

---

# Structure simplifiée

```text
Cortex_AI_Minist-re/
│
├── Backend/
│   ├── api/
│   ├── app/
│   ├── core/
│   ├── data/
│   ├── services/
│   ├── tests/
│   └── ...
│
├── Frontend/
│   ├── src/
│   ├── public/
│   └── ...
│
├── chroma_db/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

# Branche de développement

Branche actuelle de référence:

```text
zouhair
```

Pour récupérer les dernières modifications:

```bash
git switch zouhair
git pull
```

---

# Statut du projet

Le projet est actuellement dans une phase avancée de PoC professionnel.

Les prochaines améliorations prévues concernent principalement:

- sécurisation des webhooks n8n
- Docker / Docker Compose
- CI/CD
- monitoring
- gestion avancée des utilisateurs et rôles
- permissions fines sur les documents RAG
