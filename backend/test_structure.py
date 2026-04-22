#!/usr/bin/env python3
"""
Test Simple - Validation structure SANS dépendances IA lourdes
Vérifie que le code est bien écrit sans installer torch/ultralytics/etc.
"""

import sys
from pathlib import Path

print("🔍 " + "═" * 58)
print("🔍 TEST STRUCTURE URBANFIX AI (sans dépendances lourdes)")
print("🔍 " + "═" * 58)
print()

# Test 1: Configuration de base
print("1️⃣  Test configuration...")
try:
    from app.core.config import settings
    print(f"   ✅ Configuration OK")
    print(f"   📋 {settings.APP_NAME} v{settings.VERSION}")
    print(f"   📋 Environment: {settings.ENVIRONMENT}")
    print(f"   📋 Classes détection: {len(settings.DETECTION_CLASSES)}")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    sys.exit(1)

print()

# Test 2: Structure fichiers services
print("2️⃣  Test structure services (fichiers Python)...")

services = {
    "app/services/detection.py": "Detection (YOLOv8)",
    "app/services/image_generation.py": "Image Generation (SDXL)",
    "app/services/cost_estimation.py": "Cost Estimation (Llama)",
    "app/services/audio_generation.py": "Audio (Bark TTS)",
    "app/services/video_generation.py": "Video (SVD)",
    "app/services/pdf_report.py": "PDF Report",
    "app/services/orchestrator.py": "Orchestrator",
    "app/services/__init__.py": "Services __init__",
}

all_ok = True
for path, name in services.items():
    if Path(path).exists():
        size_kb = Path(path).stat().st_size / 1024
        print(f"   ✅ {name:<30} ({size_kb:.1f} KB)")
    else:
        print(f"   ❌ {name:<30} MANQUANT")
        all_ok = False

print()

# Test 3: Vérifier syntaxe Python (sans importer)
print("3️⃣  Test syntaxe Python (parsing AST)...")
import ast

syntax_ok = True
for path in services.keys():
    if not Path(path).exists():
        continue
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        # Compter fonctions/classes
        tree = ast.parse(code)
        classes = sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
        functions = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
        
        service_name = Path(path).stem
        print(f"   ✅ {service_name:<25} {classes} classe(s), {functions} fonction(s)")
    except SyntaxError as e:
        print(f"   ❌ {Path(path).stem:<25} Erreur ligne {e.lineno}")
        syntax_ok = False

print()

# Test 4: Répertoires
print("4️⃣  Test répertoires projet...")

dirs = ["models", "outputs", "uploads", "temp", 
        "outputs/detections", "outputs/scenarios", 
        "outputs/audio", "outputs/videos", "outputs/reports"]

for d in dirs:
    status = "✅" if Path(d).exists() else "⚠️"
    print(f"   {status} {d}/")

print()

# Test 5: Configuration minimale
print("5️⃣  Test configuration APIs...")

config_checks = [
    ("Groq API (Llama)", settings.GROQ_API_KEY is not None),
    ("HuggingFace Token", settings.HUGGINGFACE_TOKEN is not None),
    ("Secret Key configuré", settings.SECRET_KEY != "changez-cette-cle-secrete-en-production-utilisez-openssl-rand-hex-32"),
]

for name, configured in config_checks:
    status = "✅" if configured else "⚠️"
    state = "OK" if configured else "Non configuré (optionnel)"
    print(f"   {status} {name:<25} {state}")

print()

# Test 6: Vérifier contenu clés des services
print("6️⃣  Test contenu services (éléments clés)...")

required_patterns = {
    "app/services/detection.py": ["YOLOv8", "detect_problems", "DetectionService"],
    "app/services/image_generation.py": ["SDXL", "generate_scenarios", "ImageGenerationService"],
    "app/services/cost_estimation.py": ["Llama", "estimate_costs", "CostEstimationService"],
    "app/services/orchestrator.py": ["process_complete_pipeline", "OrchestratorService"],
}

for path, patterns in required_patterns.items():
    if not Path(path).exists():
        continue
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    service_name = Path(path).stem
    found = sum(1 for p in patterns if p in content)
    total = len(patterns)
    
    if found == total:
        print(f"   ✅ {service_name:<25} {found}/{total} éléments clés trouvés")
    else:
        print(f"   ⚠️  {service_name:<25} {found}/{total} éléments clés")

print()

# Résumé
print("═" * 60)
if all_ok and syntax_ok:
    print("✅ STRUCTURE VALIDÉE - Code bien formé!")
    print()
    print("💡 NOTE IMPORTANTE:")
    print("   Les services IA nécessitent des dépendances lourdes:")
    print("   • PyTorch, Ultralytics, Diffusers, etc.")
    print()
    print("   ⚡ CUDA/GPU est OPTIONNEL (accélération)")
    print("   ✅ Le code fonctionne aussi sur CPU")
    print()
    print("📋 Pour installer les dépendances complètes:")
    print("   pip install -r requirements.txt")
    print()
    print("   OU pour installation rapide (léger):")
    print("   pip install fastapi pydantic python-dotenv groq")
    print()
else:
    print("⚠️  Problèmes détectés dans la structure")

print("═" * 60)
