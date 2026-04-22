#!/usr/bin/env python3
"""
Test Rapide - Imports et Configuration
Vérifie que tous les services peuvent être importés
"""

import sys
from pathlib import Path

print("🧪 " + "═" * 58)
print("🧪 TEST IMPORTS URBANFIX AI")
print("🧪 " + "═" * 58)
print()

# Test 1: Imports configuration
print("1️⃣  Test import configuration...")
try:
    from app.core.config import settings, get_settings
    print(f"   ✅ Configuration chargée")
    print(f"   📋 APP_NAME: {settings.APP_NAME}")
    print(f"   📋 Version: {settings.VERSION}")
    print(f"   📋 Environment: {settings.ENVIRONMENT}")
    print(f"   📋 YOLO Model: {settings.YOLO_MODEL_PATH}")
    print(f"   📋 Detection Classes: {len(settings.DETECTION_CLASSES)} classes")
except Exception as e:
    print(f"   ❌ Erreur: {e}")
    sys.exit(1)

print()

# Test 2: Imports services
print("2️⃣  Test import services...")

services_to_test = [
    ("Detection", "app.services", "get_detection_service"),
    ("Image Generation", "app.services", "get_image_generation_service"),
    ("Cost Estimation", "app.services", "get_cost_estimation_service"),
    ("Audio Generation", "app.services", "get_audio_generation_service"),
    ("Video Generation", "app.services", "get_video_generation_service"),
    ("PDF Report", "app.services", "get_pdf_report_service"),
    ("Orchestrator", "app.services", "get_orchestrator_service"),
]

failed = []
for service_name, module_path, func_name in services_to_test:
    try:
        module = __import__(module_path, fromlist=[func_name])
        func = getattr(module, func_name)
        service = func()
        print(f"   ✅ {service_name}: OK")
    except Exception as e:
        print(f"   ❌ {service_name}: {e}")
        failed.append(service_name)

print()

# Test 3: Structure répertoires
print("3️⃣  Test structure répertoires...")

required_dirs = [
    "models",
    "outputs",
    "outputs/detections",
    "outputs/scenarios",
    "outputs/audio",
    "outputs/videos",
    "outputs/reports",
    "uploads",
    "temp",
]

for dir_path in required_dirs:
    if Path(dir_path).exists():
        print(f"   ✅ {dir_path}/")
    else:
        print(f"   ⚠️  {dir_path}/ - manquant")

print()

# Test 4: Configuration API
print("4️⃣  Test configuration APIs...")

api_checks = [
    ("Groq API Key", settings.GROQ_API_KEY is not None),
    ("Hugging Face Token", settings.HUGGINGFACE_TOKEN is not None),
    ("Secret Key", settings.SECRET_KEY != "changez-cette-cle-secrete-en-production-utilisez-openssl-rand-hex-32"),
]

for check_name, is_configured in api_checks:
    if is_configured:
        print(f"   ✅ {check_name}")
    else:
        print(f"   ⚠️  {check_name} - non configuré")

print()

# Test 5: Orchestrateur status
print("5️⃣  Test statut système...")
try:
    from app.services import get_orchestrator_service
    orchestrator = get_orchestrator_service()
    status = orchestrator.get_system_status()
    
    print(f"   Services: {len(status['services'])} disponibles")
    print(f"   CUDA: {status['system']['cuda_available']}")
    if status['system']['cuda_device']:
        print(f"   GPU: {status['system']['cuda_device']}")
    print(f"   Groq configuré: {status['config']['groq_configured']}")
except Exception as e:
    print(f"   ⚠️  Erreur statut: {e}")

print()

# Résumé
print("═" * 60)
if failed:
    print(f"❌ Tests ÉCHOUÉS: {len(failed)} service(s)")
    for service in failed:
        print(f"   • {service}")
    sys.exit(1)
else:
    print("✅ TOUS LES TESTS RÉUSSIS!")
    print()
    print("📝 Prochaines étapes:")
    print("   1. Configurer GROQ_API_KEY dans .env")
    print("   2. Configurer HUGGINGFACE_TOKEN dans .env")
    print("   3. Placer une image test dans test_data/urban_space.jpg")
    print("   4. Exécuter: python test_pipeline.py --mode status")
    print("   5. Exécuter: python test_pipeline.py --mode full")

print("═" * 60)
