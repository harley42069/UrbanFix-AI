# UrbanFix AI - Services Backend IA

## Vue d'ensemble

Backend complet pour **UrbanFix AI**, plateforme intelligente de diagnostic et réaménagement d'espaces urbains tunisiens par IA générative multimodale.

###  Fonctionnalités

Citoyen tunisien upload photo espace urbain → reçoit automatiquement:

1. **DÉTECTION IA** : YOLOv8 identifie 6 types problèmes urbains
2. **GÉNÉRATION IMAGES** : 3 scénarios photoréalistes (SDXL + LoRA)
3. **ESTIMATION COÛTS** : Prix détaillés TND via Llama 3.1 (Groq)
4. **NARRATION AUDIO** : Description projet vocale (Bark TTS)
5.  **VIDÉO TRANSFORMATION** : Animation avant/après (Stable Video Diffusion)
6. **RAPPORT PDF** : Document complet 20-30 pages

### Règle de langue du contenu généré

- La langue du contenu généré suit le user_prompt (FR/EN).
- Si le user_prompt est vide, la langue est détectée depuis title + description.
- Fallback robuste: en cas d'incertitude ou langue hors FR/EN, la langue retenue est FR.
- Cette règle s'applique au texte d'estimation, narration_text, et sections textuelles du PDF.

---

## Stack Technique

### IA/ML
- **Détection** : YOLOv8n (Ultralytics)
- **Génération images** : Stable Diffusion XL 1.0 + LoRA custom Tunisie
- **Génération texte** : Llama 3.1 70B via Groq API (gratuit)
- **Génération audio** : Bark TTS (Suno AI)
- **Génération vidéo** : Stable Video Diffusion + MoviePy
- **Export PDF** : ReportLab

### Backend
- **Framework** : FastAPI
- **Base de données** : SQLAlchemy + PostgreSQL/SQLite
- **Authentification** : JWT (python-jose)
- **Deep Learning** : PyTorch, Transformers, Diffusers

---

##  Installation

### 1. Prérequis

```bash
# Python 3.10+
python --version

# CUDA (optionnel mais recommandé pour GPU)
nvidia-smi
```

### 2. Cloner et installer dépendances

```bash
cd backend

# Créer environnement virtuel
python -m venv venv

# Activer
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Installer dépendances
pip install -r requirements.txt
```

### 3. Configuration variables environnement

```bash
# Copier template
cp .env.example .env

# Éditer .env et ajouter vos clés API
```

**Clés requises minimum** :
- `GROQ_API_KEY` : [Gratuit sur groq.com](https://console.groq.com/keys)
- `HUGGINGFACE_TOKEN` : [Gratuit sur huggingface.co](https://huggingface.co/settings/tokens)

### 4. Créer répertoires

```bash
mkdir -p models outputs uploads temp
mkdir -p outputs/detections outputs/scenarios outputs/audio outputs/videos outputs/reports
```

---

## 🚀 Utilisation

### Test Pipeline Complet

```bash
# Placer une image test
mkdir test_data
# Copier image espace urbain dans test_data/urban_space.jpg

# Exécuter pipeline
python test_pipeline.py --mode full
```

### Test Services Individuels

```python
from app.services import (
    get_detection_service,
    get_image_generation_service,
    get_cost_estimation_service,
    get_orchestrator_service
)

# 1. Détection seule
detection_svc = get_detection_service()
results = detection_svc.detect_problems("image.jpg")
print(f"Problèmes: {results['total_problems']}")

# 2. Pipeline complet orchestré
orchestrator = get_orchestrator_service()
final_results = orchestrator.process_complete_pipeline(
    image_path="image.jpg",
    project_info={"title": "Mon projet", "location": "Tunis"}
)
```

---

## Services Détaillés

###  Service Détection (`detection.py`)

**Détecte 6 types de problèmes urbains:**

- Routes/chaussées dégradées
- Déchets/ordures
- Éclairage public défectueux
- Végétation envahissante
- Mobilier urbain cassé
- Graffitis/tags

```python
from app.services import get_detection_service

detection_svc = get_detection_service()

# Analyser image
results = detection_svc.detect_problems(
    image_path="urban_space.jpg",
    confidence=0.25,
    visualize=True  # Génère image annotée
)

print(results)
# {
#     "detections": [...],
#     "summary": {"route_degradee": 2, "dechet": 3, ...},
#     "total_problems": 5,
#     "annotated_image": "outputs/detections/urban_space_annotated.jpg",
#     "statistics": {...}
# }
```

**Modèle utilisé**: YOLOv8n (léger, rapide)

**Chemin stable recommandé (production)**:
- `backend/models/yolo_road_damage_best.pt`
- variable backend: `YOLO_MODEL_PATH=./models/yolo_road_damage_best.pt`

Si le modèle est absent, le service log un warning et retourne un fallback
compatible API (`boxes=[]`, `warnings=[...]`) au lieu de casser le pipeline.

**Sortie image annotée (stable par process)**:
- `<outputs_root>/process/<process_id>/annotated.jpg`
- exposée dans status via `outputs.annotated_image` et `outputs.annotated_image_path`

**Note importante**: Le modèle YOLOv8 standard détecte 80 classes COCO. Pour détecter vos 6 classes spécifiques, vous devez **entraîner un modèle custom** avec dataset annoté d'espaces urbains tunisiens.

---

###  Service Génération Images (`image_generation.py`)

**Génère 3 scénarios photoréalistes avec SDXL:**

- **Conservateur** : Préserve architecture, améliorations minimales
- **Modéré** : Équilibre moderne/traditionnel (recommandé)
- **Innovant** : Vision futuriste, smart city

```python
from app.services import get_image_generation_service

image_gen_svc = get_image_generation_service()

# Générer scénarios basés sur détections
scenarios = image_gen_svc.generate_scenarios(
    detection_results=detection_results,
    base_image_path="original.jpg",  # Optionnel pour img2img
    num_scenarios=3
)

for scenario in scenarios:
    print(f"{scenario['type']}: {scenario['image_path']}")
```

**Modèle**: Stable Diffusion XL 1.0
**LoRA custom**: Entraîner avec images architecture tunisienne
**Résolution**: 1024x1024px

---

### Service Estimation Coûts (`cost_estimation.py`)

**Estime coûts travaux en TND avec Llama 3.1:**

```python
from app.services import get_cost_estimation_service

cost_svc = get_cost_estimation_service()

estimation = cost_svc.estimate_costs(
    detection_results=detection_results,
    scenario_type="moderate",
    region="Tunis"
)

print(f"Coût total: {estimation['total_cost_tnd']:,.2f} TND")
print(estimation['ai_analysis']['recommendations'])
```

**Base de données coûts** (TND/unité):
- Route dégradée: 150-500 TND/m²
- Déchets: 50-200 TND/tonne
- Éclairage: 300-800 TND/unité
- Végétation: 80-250 TND/m²
- Mobilier: 200-1500 TND/unité
- Graffiti: 50-300 TND/m²

**Llama 3.1** : Enrichit estimation avec analyse contextuelle via Groq API (gratuit).

---

###  Service Audio (`audio_generation.py`)

**Génère narration vocale française avec Bark TTS:**

```python
from app.services import get_audio_generation_service

audio_svc = get_audio_generation_service()

audio_result = audio_svc.generate_narration(
    detection_results=detection_results,
    cost_estimation=cost_estimation,
    scenario_info=selected_scenario
)

print(f"Audio: {audio_result['audio_path']}")
print(f"Durée: {audio_result['duration_seconds']}s")
```

**Voix**: Français (v2/fr_speaker_6)
**Format**: WAV 24kHz

---

### 5️Service Vidéo (`video_generation.py`)

**Crée animation transformation avant/après:**

```python
from app.services import get_video_generation_service

video_svc = get_video_generation_service()

video_result = video_svc.create_transformation_video(
    before_image_path="original.jpg",
    after_image_path="scenario_moderate.png",
    audio_path="narration.wav",  # Optionnel
    include_text=True
)

print(f"Vidéo: {video_result['video_path']}")
```

**Pipeline**:
1. Génère frames SVD depuis image avant
2. Génère frames SVD depuis image après
3. Crée transition crossfade
4. Ajoute overlays texte
5. Synchronise audio
6. Export MP4

**Résolution**: 1024x576 @ 25fps

---

### 6️⃣ Service PDF (`pdf_report.py`)

**Génère rapport professionnel 20-30 pages:**

```python
from app.services import get_pdf_report_service

pdf_svc = get_pdf_report_service()

pdf_result = pdf_svc.generate_complete_report(
    project_data={
        "title": "Réaménagement Place X",
        "location": "Tunis",
        "date": "2024-02-21"
    },
    detection_results=detection_results,
    scenarios=scenarios,
    cost_estimation=cost_estimation
)

print(f"PDF: {pdf_result['pdf_path']}")
```

**Contenu**:
- Page couverture
- Sommaire
- Résumé exécutif
- Analyse détections avec images
- 3 scénarios visualisés
- Estimation budgétaire détaillée
- Recommandations IA
- Annexes techniques

---

### 7️ Orchestrateur (`orchestrator.py`)

**Coordonne pipeline complet:**

```python
from app.services import get_orchestrator_service

orchestrator = get_orchestrator_service()

# Pipeline complet
results = orchestrator.process_complete_pipeline(
    image_path="urban_space.jpg",
    project_info={"title": "Mon projet", "location": "Tunis"},
    scenario_type="moderate",
    generate_all=True
)

# Ou analyse rapide (détection + coûts seulement)
quick_results = orchestrator.process_quick_analysis("urban_space.jpg")
```

---

##  Variables Environnement

Fichier `.env` requis:

```bash
# APIs essentielles
GROQ_API_KEY=gsk_...           # Groq API (Llama) - GRATUIT
HUGGINGFACE_TOKEN=hf_...       # Hugging Face - GRATUIT

# Optionnelles
OPENAI_API_KEY=sk-...          # GPT-4 Vision (payant)
REPLICATE_API_KEY=r8_...       # SDXL cloud (payant)

# Sécurité
SECRET_KEY=your-secret-key-here

# Base de données
DATABASE_URL=sqlite:///./urbanfix.db
```

---

##  Entraîner Modèles Custom

### YOLOv8 Custom (6 classes urbaines)

```bash
# 1. Créer dataset annotations (format YOLO)
# Structure:
# dataset/
#   images/train/
#   images/val/
#   labels/train/
#   labels/val/
#   data.yaml

# 2. Entraîner
from ultralytics import YOLO

model = YOLO('yolov8n.pt')
model.train(
    data='dataset/data.yaml',
    epochs=100,
    imgsz=640,
    batch=16
)

# 3. Sauvegarder
model.save('models/yolov8n_urbanfix.pt')
```

### SDXL LoRA Tunisie

```bash
# Entraîner LoRA avec dataset architecture tunisienne
# Utiliser kohya_ss ou SimpleTuner
# Dataset: 50-200 images espaces urbains tunisiens

# Résultat: lora_tunisia_urban.safetensors
# Placer dans: models/lora_tunisia_urban.safetensors
```

---

##  Dépannage

### Erreur CUDA Out of Memory

```python
# Dans config.py, réduire:
SDXL_NUM_INFERENCE_STEPS=20  # au lieu de 30
SVD_NUM_FRAMES=14            # au lieu de 25

# Ou activer CPU offload:
# Dans image_generation.py:
self.pipe.enable_model_cpu_offload()
```

### Groq API Rate Limit

```python
# Groq gratuit: 30 requêtes/minute
# Ajouter retry avec backoff:

import time
from groq import RateLimitError

try:
    response = client.chat.completions.create(...)
except RateLimitError:
    time.sleep(5)
    response = client.chat.completions.create(...)
```

### Bark TTS lent

```python
# Bark génère ~10-15 secondes de parole à la fois
# Pré-charger modèles au démarrage:

from bark import preload_models
preload_models()  # Une seule fois au lancement
```

---

## Performance

**Temps d'exécution typique** (GPU RTX 3060):

| Étape | Durée |
|-------|-------|
| Détection YOLOv8 | ~1-2s |
| SDXL 3 scénarios | ~90-120s |
| Estimation Llama | ~5-10s |
| Audio Bark | ~30-60s |
| Vidéo SVD | ~120-180s |
| PDF Report | ~5s |
| **TOTAL** | **~5-8 minutes** |

**Mode CPU** : ~3-5x plus lent

---

##  TODO / Améliorations

- [ ] Entraîner YOLOv8 custom avec dataset tunisien
- [ ] Créer LoRA SDXL architecture tunisienne
- [ ] Ajouter cache résultats Redis
- [ ] API endpoints FastAPI
- [ ] WebSockets pour progression temps réel
- [ ] Multi-langues (arabe, anglais)
- [ ] Intégration Celery pour tasks async
- [ ] Authentification utilisateurs
- [ ] Dashboard admin
- [ ] Tests unitaires complets

---

## Licence

MIT License - Voir LICENSE

---

##  Contribution

1. Fork le projet
2. Créer branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. Pull Request

---


