# API Documentation - UrbanFix AI

## 📋 Vue d'ensemble

L'API UrbanFix AI fournit des endpoints REST et WebSocket pour l'analyse intelligente des espaces urbains tunisiens.

### Technologies
- **Framework**: FastAPI 0.109.0
- **Documentation**: Swagger UI + ReDoc
- **Protocol**: REST + WebSocket
- **Format**: JSON

### Base URL
```
http://localhost:8000/api/v1
```

### Format standard des réponses (ApiResponse)
Toutes les routes HTTP v1 retournent le format suivant :

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-03-15T10:00:00.000000+00:00",
    "pagination": null
  }
}
```

En cas d'erreur :

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Données de requête invalides",
    "details": []
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-03-15T10:00:00.000000+00:00",
    "pagination": null
  }
}
```

### Authentification (JWT)
Header requis sur les endpoints protégés :

```http
Authorization: Bearer <access_token>
```

### Codes d'erreur fréquents
- `400 BAD_REQUEST`: payload invalide
- `401 UNAUTHORIZED`: token manquant/invalide/expiré
- `403 FORBIDDEN`: rôle insuffisant ou ressource non autorisée
- `404 NOT_FOUND`: ressource inexistante
- `409 CONFLICT`: conflit métier (email déjà utilisé, etc.)
- `413 REQUEST_ENTITY_TOO_LARGE`: upload trop volumineux (>10MB)
- `422 VALIDATION_ERROR`: validation de schéma
- `429 RATE_LIMITED`: limite de requêtes atteinte (dev)
- `500 INTERNAL_ERROR`: erreur serveur

### Endpoints principaux (exemples)

#### POST `/api/v1/auth/register`
Request:
```json
{
  "email": "user@test.tn",
  "username": "user1",
  "password": "Secret123!",
  "full_name": "User One",
  "role": "citizen"
}
```

Response (201):
```json
{
  "success": true,
  "data": {
    "id": 1,
    "email": "user@test.tn",
    "username": "user1",
    "role": "citizen"
  },
  "error": null,
  "meta": {"request_id": "...", "timestamp": "...", "pagination": null}
}
```

#### POST `/api/v1/auth/login`
Request: `application/x-www-form-urlencoded`
- `username`
- `password`

Response (200):
```json
{
  "success": true,
  "data": {
    "access_token": "<jwt>",
    "refresh_token": "<jwt>",
    "token_type": "bearer"
  },
  "error": null,
  "meta": {"request_id": "...", "timestamp": "...", "pagination": null}
}
```

#### POST `/api/v1/signalements/`
Request: `multipart/form-data`
- `image`: fichier image
- `title`, `description`, `latitude`, `longitude`, `address`, `city`, `region`, `metadata`

Response (201):
```json
{
  "success": true,
  "data": {
    "id": 10,
    "status": "pending",
    "progress": 0,
    "current_stage": "queued"
  },
  "error": null,
  "meta": {"request_id": "...", "timestamp": "...", "pagination": null}
}
```

#### POST `/api/v1/process/{signalement_id}`
Déclenche le pipeline IA asynchrone.

Response (202):
```json
{
  "success": true,
  "data": {
    "signalement_id": 10,
    "queued": true,
    "status": "pending",
    "queue_mode": "background_tasks",
    "task_id": null
  },
  "error": null,
  "meta": {"request_id": "...", "timestamp": "...", "pagination": null}
}
```

#### GET `/api/v1/process/{signalement_id}/status`
Retourne l'état live (polling/websocket-friendly).

Response (200):
```json
{
  "success": true,
  "data": {
    "signalement_id": 10,
    "status": "processing",
    "progress": 35,
    "stage": "images",
    "last_error": null,
    "completed_at": null,
    "outputs": {
      "annotated_image": "/outputs/detections/xxx.jpg",
      "scenario_image": "/outputs/scenarios/yyy.png",
      "audio": null,
      "video": null,
      "pdf": null
    },
    "ws_channel": "/api/v1/ws/analysis/10"
  },
  "error": null,
  "meta": {"request_id": "...", "timestamp": "...", "pagination": null}
}
```

#### POST `/api/v1/estimation/{signalement_id}`
Request:
```json
{
  "signalement_id": 10,
  "scenario_types": ["minimal", "moderate", "premium"],
  "generate_images": true
}
```

Response (200):
```json
{
  "success": true,
  "data": {
    "minimal": {"total_cost_avg": 1000.0},
    "moderate": {"total_cost_avg": 1500.0},
    "premium": {"total_cost_avg": 2000.0},
    "recommended": "moderate"
  },
  "error": null,
  "meta": {"request_id": "...", "timestamp": "...", "pagination": null}
}
```

#### POST `/api/v1/reports/generate`
Protégé RBAC: `municipality|admin`.

#### DELETE `/api/v1/reports/{report_id}`
Protégé RBAC: `admin`.

### One-liner qualité (format/lint/tests)
Si `ruff` et `black` sont installés:

```powershell
ruff check backend ; black --check backend ; pytest backend/tests -q
```

Mode minimal offline (sans ruff/black):

```powershell
pytest backend/tests -q
```

---

## 🚀 Démarrage

### 1. Installer les dépendances
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configuration
Créer un fichier `.env`:
```env
# API Keys
GROQ_API_KEY=your_groq_api_key_here
HUGGINGFACE_TOKEN=your_hf_token_here  # Optionnel

# Configuration
DEBUG=True
PROJECT_NAME="UrbanFix AI"
VERSION="1.0.0"
```

### 3. Lancer le serveur
```bash
uvicorn app.main:app --reload
```

Le serveur démarre sur: http://localhost:8000

### 4. Documentation interactive
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## 📡 Endpoints

### 🏠 Root Endpoints

#### GET `/`
Informations sur l'API

**Réponse**:
```json
{
  "success": true,
  "data": {
    "name": "UrbanFix AI",
    "version": "1.0.0",
    "status": "online",
    "endpoints": {...}
  }
}
```

#### GET `/health`
Health check du système

**Réponse**:
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "directories_ok": true,
    "debug_mode": true
  }
}
```

---

### 📤 Upload Endpoints

#### POST `/api/v1/upload/image`
Upload une image pour analyse

**Paramètres**:
- `file` (multipart/form-data): Fichier image (JPG, PNG, BMP, TIFF, WebP)
- Max 10MB

**Réponse**:
```json
{
  "success": true,
  "message": "Image uploadée avec succès",
  "data": {
    "file_id": "uuid-here",
    "filename": "20260302_123456_uuid.jpg",
    "file_path": "/uploads/...",
    "file_size": 1234567
  }
}
```

**Exemple cURL**:
```bash
curl -X POST "http://localhost:8000/api/v1/upload/image" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/image.jpg"
```

#### POST `/api/v1/upload/images/batch`
Upload multiple images (max 10)

#### GET `/api/v1/upload/info/{file_id}`
Récupère les informations d'un fichier

#### DELETE `/api/v1/upload/{file_id}`
Supprime un fichier uploadé

---

### 🔍 Analysis Endpoints

#### POST `/api/v1/analysis/detect-only`
Détection seule (YOLOv8)

**Paramètres**:
- `file_id` (query): ID du fichier
- `confidence_threshold` (query, default=0.25): Seuil de confiance
- `visualize` (query, default=true): Créer image annotée

**Réponse**:
```json
{
  "success": true,
  "data": {
    "detections": [...],
    "statistics": {...},
    "annotated_image_path": "..."
  }
}
```

**Exemple**:
```bash
curl -X POST "http://localhost:8000/api/v1/analysis/detect-only?file_id=xxx&confidence_threshold=0.3"
```

#### POST `/api/v1/analysis/quick`
Analyse rapide (détection + estimation coûts)

**Body**:
```json
{
  "file_id": "uuid-here",
  "confidence_threshold": 0.25,
  "region": "Tunis"
}
```

**Réponse**:
```json
{
  "success": true,
  "data": {
    "detection": {...},
    "cost_estimation": {...}
  }
}
```

#### POST `/api/v1/analysis/full`
Analyse complète (asynchrone) - Pipeline complet

**Body**:
```json
{
  "file_id": "uuid-here",
  "project_name": "Rénovation Place Tahrir",
  "location": "Tunis, Medina",
  "region": "Tunis",
  "scenario_type": "moderate",
  "num_scenarios": 3,
  "confidence_threshold": 0.25,
  "generate_audio": true,
  "generate_video": true,
  "generate_report": true
}
```

**Paramètres**:
- `scenario_type`: `conservative`, `moderate`, `innovative`
- `num_scenarios`: 1-5
- `confidence_threshold`: 0.1-0.9

**Réponse**:
```json
{
  "success": true,
  "message": "Analyse démarrée",
  "data": {
    "analysis_id": "uuid-here",
    "status": "pending",
    "estimated_time": "5-30 minutes"
  }
}
```

**Exemple**:
```bash
curl -X POST "http://localhost:8000/api/v1/analysis/full" \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "xxx",
    "project_name": "Test",
    "location": "Tunis",
    "scenario_type": "moderate"
  }'
```

#### GET `/api/v1/analysis/status/{analysis_id}`
Récupère le statut d'une analyse

**Réponse**:
```json
{
  "analysis_id": "uuid",
  "status": "processing",
  "progress": 0.45,
  "current_step": "Génération de scénarios",
  "message": "Création des visualisations..."
}
```

**Status possibles**: `pending`, `processing`, `completed`, `failed`

#### GET `/api/v1/analysis/results/{analysis_id}`
Récupère les résultats complets (quand status=completed)

**Réponse**:
```json
{
  "success": true,
  "data": {
    "results": {
      "detection": {...},
      "scenarios": [...],
      "cost_estimation": {...},
      "audio_path": "...",
      "video_path": "...",
      "pdf_path": "..."
    }
  }
}
```

#### GET `/api/v1/analysis/list`
Liste toutes les analyses

**Paramètres**:
- `status_filter` (query): Filtrer par statut
- `limit` (query, default=50): Nombre max de résultats

#### DELETE `/api/v1/analysis/{analysis_id}`
Supprime une analyse

#### GET `/api/v1/analysis/system/status`
Statut du système (mémoire, GPU, modèles)

#### POST `/api/v1/analysis/system/unload-models`
Décharge les modèles de la mémoire

---

### 📄 Reports Endpoints

#### POST `/api/v1/reports/generate`
Génère un rapport PDF depuis une analyse

**Body**:
```json
{
  "analysis_id": "uuid-here",
  "include_executive_summary": true,
  "include_detailed_costs": true,
  "include_technical_specs": true,
  "include_timeline": true,
  "language": "fr"
}
```

**Réponse**:
```json
{
  "success": true,
  "data": {
    "report_id": "uuid",
    "status": "pending",
    "estimated_time": "30-60 secondes"
  }
}
```

#### POST `/api/v1/reports/generate/custom`
Génère un rapport personnalisé

**Body**:
```json
{
  "project_name": "Mon Projet",
  "location": "Tunis",
  "detection_results": {...},
  "scenarios": [...],
  "cost_estimation": {...},
  "additional_notes": "Notes..."
}
```

#### GET `/api/v1/reports/status/{report_id}`
Statut de génération du rapport

#### GET `/api/v1/reports/download/{report_id}`
Télécharge le PDF (quand status=completed)

**Exemple**:
```bash
curl -O "http://localhost:8000/api/v1/reports/download/{report_id}"
```

#### GET `/api/v1/reports/preview/{report_id}`
Aperçu du rapport (métadonnées)

#### GET `/api/v1/reports/list`
Liste tous les rapports

#### DELETE `/api/v1/reports/{report_id}`
Supprime un rapport

---

### 🔌 WebSocket Endpoints

#### WS `/api/v1/ws/analysis/{analysis_id}`
WebSocket pour suivre une analyse spécifique

**Messages reçus**:
```json
{
  "type": "analysis_update",
  "analysis_id": "uuid",
  "status": "processing",
  "progress": 0.45,
  "current_step": "Génération de scénarios",
  "message": "Création des visualisations...",
  "timestamp": "2026-03-02T10:30:00"
}
```

**Commandes client**:
```json
{"type": "ping"}
{"type": "get_status"}
```

**Exemple JavaScript**:
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/ws/analysis/uuid-here');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Progression: ${data.progress * 100}%`);
  console.log(`Étape: ${data.current_step}`);
};

ws.send(JSON.stringify({type: "get_status"}));
```

#### WS `/api/v1/ws/global`
WebSocket pour suivre toutes les analyses

**Commandes**:
```json
{"type": "get_all_status"}
```

#### GET `/api/v1/ws/connections/count`
Nombre de connexions WebSocket actives

---

## 🔄 Workflow Complet

### Scénario 1: Analyse rapide

```bash
# 1. Upload image
UPLOAD_RESPONSE=$(curl -X POST "http://localhost:8000/api/v1/upload/image" \
  -F "file=@image.jpg")
FILE_ID=$(echo $UPLOAD_RESPONSE | jq -r '.data.file_id')

# 2. Analyse rapide
curl -X POST "http://localhost:8000/api/v1/analysis/quick" \
  -H "Content-Type: application/json" \
  -d "{\"file_id\": \"$FILE_ID\", \"region\": \"Tunis\"}"
```

### Scénario 2: Pipeline complet

```bash
# 1. Upload
FILE_ID=$(curl -X POST "http://localhost:8000/api/v1/upload/image" \
  -F "file=@image.jpg" | jq -r '.data.file_id')

# 2. Lancer analyse complète
ANALYSIS_ID=$(curl -X POST "http://localhost:8000/api/v1/analysis/full" \
  -H "Content-Type: application/json" \
  -d "{
    \"file_id\": \"$FILE_ID\",
    \"project_name\": \"Rénovation Place\",
    \"location\": \"Tunis\"
  }" | jq -r '.data.analysis_id')

# 3. Suivre la progression (WebSocket ou polling)
# Polling:
while true; do
  STATUS=$(curl -s "http://localhost:8000/api/v1/analysis/status/$ANALYSIS_ID" \
    | jq -r '.status')
  echo "Status: $STATUS"
  [[ "$STATUS" == "completed" ]] && break
  sleep 5
done

# 4. Récupérer les résultats
curl "http://localhost:8000/api/v1/analysis/results/$ANALYSIS_ID"

# 5. Générer le rapport
REPORT_ID=$(curl -X POST "http://localhost:8000/api/v1/reports/generate" \
  -H "Content-Type: application/json" \
  -d "{\"analysis_id\": \"$ANALYSIS_ID\"}" \
  | jq -r '.data.report_id')

# 6. Télécharger le PDF
sleep 30  # Attendre génération
curl -O "http://localhost:8000/api/v1/reports/download/$REPORT_ID"
```

---

## 🐍 Exemple Python

```python
import requests
import time

BASE_URL = "http://localhost:8000/api/v1"

# 1. Upload
with open("urban_space.jpg", "rb") as f:
    files = {"file": ("image.jpg", f, "image/jpeg")}
    response = requests.post(f"{BASE_URL}/upload/image", files=files)
    file_id = response.json()["data"]["file_id"]

# 2. Analyse complète
analysis_request = {
    "file_id": file_id,
    "project_name": "Rénovation Place",
    "location": "Tunis, Medina",
    "scenario_type": "moderate",
    "num_scenarios": 3
}
response = requests.post(f"{BASE_URL}/analysis/full", json=analysis_request)
analysis_id = response.json()["data"]["analysis_id"]

# 3. Attendre completion
while True:
    response = requests.get(f"{BASE_URL}/analysis/status/{analysis_id}")
    status_data = response.json()
    print(f"Progression: {status_data['progress']*100:.1f}%")
    
    if status_data["status"] == "completed":
        break
    elif status_data["status"] == "failed":
        print(f"Erreur: {status_data['error']}")
        break
    
    time.sleep(5)

# 4. Récupérer résultats
response = requests.get(f"{BASE_URL}/analysis/results/{analysis_id}")
results = response.json()["data"]["results"]

print(f"Problèmes détectés: {len(results['detection']['detections'])}")
print(f"Coût estimé: {results['cost_estimation']['total_cost']} TND")
```

---

## 📊 Codes de Statut HTTP

- `200 OK`: Requête réussie
- `201 Created`: Ressource créée
- `202 Accepted`: Requête acceptée (traitement asynchrone)
- `400 Bad Request`: Paramètres invalides
- `404 Not Found`: Ressource non trouvée
- `500 Internal Server Error`: Erreur serveur

---

## 🔒 Sécurité (Production)

Pour la production, ajouter:

1. **Authentification JWT**
2. **Rate limiting**
3. **CORS restrictif**
4. **HTTPS obligatoire**
5. **Validation renforcée**

---

## 📞 Support

- Documentation interactive: http://localhost:8000/docs
- GitHub: [UrbanFix AI Repository]
- Email: support@urbanfix.tn

---

## 🎯 Classes de Détection

Les 6 classes de problèmes urbains détectées:

1. **route_degradee** - Routes dégradées, nids-de-poule
2. **dechet** - Déchets, accumulation d'ordures
3. **eclairage_defectueux** - Éclairage public défaillant
4. **vegetation_envahissante** - Végétation non entretenue
5. **mobilier_casse** - Mobilier urbain cassé/vandalisé
6. **graffiti** - Tags, graffitis non autorisés

---

## 💰 Estimation des Coûts

Les coûts sont calculés en **Dinars Tunisiens (TND)** avec:

- Base de données de coûts par type de problème
- Variation par région (Tunis, Sfax, Sousse, etc.)
- Analyse IA pour ajustements contextuels
- Recommandations de priorisation

---

## 🎨 Types de Scénarios

3 types de scénarios de rénovation:

- **Conservative**: Réparations minimales, budget réduit
- **Moderate**: Équilibre qualité/coût, recommandé
- **Innovative**: Solutions modernes, budget élevé

Chaque scénario génère des visualisations SDXL adaptées.
