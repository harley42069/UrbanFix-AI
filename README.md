# UrbanFix AI

UrbanFix AI est une plateforme web d'analyse et de renovation intelligente des espaces urbains. Le projet combine un backend FastAPI, un frontend Next.js et plusieurs services IA pour detecter les problemes urbains, generer des scenarios de renovation, estimer les couts, produire de l'audio, de la video et des rapports PDF.

## Fonctionnalites principales

- Detection automatique des problemes urbains avec YOLOv8.
- Generation de scenarios visuels avec SDXL + LoRA.
- Estimation des couts en TND via Llama 3.1 sur Groq.
- Generation d'une narration audio.
- Generation d'une video avant/apres.
- Production de rapports PDF complets.
- Suivi du pipeline en temps reel via API et WebSocket.

## Architecture du projet

- `backend/` : API FastAPI, services IA, modeles, tests et documentation technique.
- `frontend/` : application Next.js pour l'interface utilisateur.
- `docs/` : documentation LoRA et autres notes de projet.
- `scripts/` : scripts PowerShell et utilitaires de demo.
- `datasets/`, `data/`, `uploads/`, `outputs/`, `temp/` : donnees locales, artefacts et sorties generees.

## Prerequis

- Windows 10/11 avec PowerShell 5.1+.
- Python 3.10 ou plus recent.
- Node.js 18+ et npm.
- Git.
- Optionnel: GPU NVIDIA pour les taches IA lourdes.

## Installation rapide

### 1. Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Creer ensuite un fichier `.env` dans `backend/` avec au minimum les variables utiles a votre configuration:

```env
APP_NAME=UrbanFix AI
PROJECT_NAME=UrbanFix AI
VERSION=1.0.0
DEBUG=True
DATABASE_URL=sqlite:///./urbanfix.db
SECRET_KEY=changez-cette-cle-secrete-en-production-utilisez-secrets-generator
GROQ_API_KEY=your_groq_api_key_here
HUGGINGFACE_TOKEN=your_hf_token_here
```

### 2. Frontend

```powershell
cd frontend
npm install
```

Le frontend utilise les variables du fichier `frontend/.env.local`.

Exemple:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

## Lancement en local

La facon la plus simple sur Windows est d'utiliser les scripts fournis a la racine du projet:

```powershell
.\scripts\run_backend.ps1
.\scripts\run_frontend.ps1
```

Ensuite, ouvrez:

- Frontend: `http://localhost:3000`
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Pipeline de demo

Pour remplir des donnees de demo, vous pouvez lancer:

```powershell
python .\scripts\seed_demo_data.py
```

Pour declencher un traitement offline de demo sur un signalement:

```powershell
python .\scripts\seed_demo_data.py --run-process
```

## Tests

### Backend

```powershell
cd backend
pytest -q
```

### Frontend

```powershell
cd frontend
npm run build
```

### Verification rapide

```powershell
curl http://localhost:8000/health
```

## Documentation utile

- [API backend](backend/API_DOCUMENTATION.md)
- [Services backend](backend/SERVICES_README.md)
- [Guide LoRA SDXL](docs/SDXL_LORA_TRAINING.md)
- [Checklist de demo](DEMO_CHECKLIST.md)
- [Correction WinError 32](WINDOWS_WINERROR32_FIX.md)

## Gestion des fichiers locaux

Les dossiers `data/`, `datasets/`, `uploads/`, `outputs/`, `temp/`, `runs/` et les poids de modeles doivent rester locaux et ne pas etre commits.

## Notes LoRA

Le projet contient une base pour le fine-tuning SDXL LoRA autour du trigger token `tnrenovation`. Le guide de reference est dans `docs/SDXL_LORA_TRAINING.md`.

## Licence

Ce projet est fourni dans le cadre du developpement UrbanFix AI. Ajoutez ici la licence officielle si elle est definie pour votre depot.