#!/usr/bin/env python3
"""
Test Syntaxe - Vérification rapide sans imports lourds
"""

import sys
import ast
from pathlib import Path

print("🔍 " + "═" * 58)
print("🔍 VALIDATION SYNTAXE SERVICES URBANFIX AI")
print("🔍 " + "═" * 58)
print()

# Services à vérifier
services = [
    "app/services/detection.py",
    "app/services/image_generation.py",
    "app/services/cost_estimation.py",
    "app/services/audio_generation.py",
    "app/services/video_generation.py",
    "app/services/pdf_report.py",
    "app/services/orchestrator.py",
    "app/services/__init__.py",
]

errors = []
warnings = []

for service_path in services:
    service_file = Path(service_path)
    service_name = service_file.name
    
    if not service_file.exists():
        errors.append(f"{service_name}: Fichier non trouvé")
        print(f"   ❌ {service_name}: Fichier non trouvé")
        continue
    
    try:
        # Lire et parser le code
        with open(service_file, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Vérifier syntaxe Python
        ast.parse(code)
        
        # Compter lignes
        lines = len(code.split('\n'))
        
        # Vérifier présence éléments clés
        has_class = 'class' in code
        has_init = '__init__' in code
        has_docstring = '"""' in code
        
        print(f"   ✅ {service_name}: OK ({lines} lignes, "
              f"{'classe' if has_class else 'module'}, "
              f"{'docs✓' if has_docstring else 'docs✗'})")
        
        if not has_docstring:
            warnings.append(f"{service_name}: Manque documentation")
            
    except SyntaxError as e:
        errors.append(f"{service_name}: Erreur syntaxe ligne {e.lineno}")
        print(f"   ❌ {service_name}: Erreur syntaxe ligne {e.lineno}")
    except Exception as e:
        errors.append(f"{service_name}: {str(e)}")
        print(f"   ⚠️  {service_name}: {str(e)}")

print()

# Vérifier fichiers config
print("📋 Configuration...")

config_files = [
    "app/core/config.py",
    "requirements.txt",
    ".env.example",
]

for config_file in config_files:
    if Path(config_file).exists():
        size_kb = Path(config_file).stat().st_size / 1024
        print(f"   ✅ {config_file} ({size_kb:.1f} KB)")
    else:
        print(f"   ❌ {config_file}: Manquant")

print()

# Scripts test
print("🧪 Scripts test...")

test_scripts = [
    "test_pipeline.py",
    "test_imports.py",
    "SERVICES_README.md",
]

for script in test_scripts:
    if Path(script).exists():
        size_kb = Path(script).stat().st_size / 1024
        print(f"   ✅ {script} ({size_kb:.1f} KB)")
    else:
        print(f"   ⚠️  {script}: Manquant")

print()

# Résumé
print("═" * 60)
print(f"📊 STATISTIQUES:")
print(f"   Services validés: {len(services) - len(errors)}/{len(services)}")
print(f"   Erreurs: {len(errors)}")
print(f"   Avertissements: {len(warnings)}")
print()

if errors:
    print("❌ ERREURS TROUVÉES:")
    for error in errors:
        print(f"   • {error}")
    print()
    sys.exit(1)

if warnings:
    print("⚠️  AVERTISSEMENTS:")
    for warning in warnings:
        print(f"   • {warning}")
    print()

print("✅ VALIDATION SYNTAXE RÉUSSIE!")
print()
print("📝 Tous les fichiers sont syntaxiquement corrects.")
print("   Pour tester le fonctionnement complet:")
print("   1. Installer: pip install -r requirements.txt")
print("   2. Configurer: éditer .env avec vos API keys")
print("   3. Tester: python test_imports.py")

print("═" * 60)
