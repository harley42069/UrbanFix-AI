#!/usr/bin/env python3
"""
Script Test Pipeline UrbanFix AI
Démontre utilisation complète des services
"""

import sys
import os
from pathlib import Path

# Ajouter backend au path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.services import get_orchestrator_service


def test_complete_pipeline():
    """
    Test pipeline complet UrbanFix AI
    
    Pré-requis:
    - Image test dans ./test_data/urban_space.jpg
    - Variables environnement configurées (.env)
    - Dépendances installées (requirements.txt)
    """
    
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "TEST PIPELINE URBANFIX AI" + " " * 23 + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    # Vérifier image test
    test_image = "./test_data/urban_space.jpg"
    
    if not os.path.exists(test_image):
        print("❌ Erreur: Image test non trouvée!")
        print(f"   Placez une image dans: {test_image}")
        print()
        print("   Vous pouvez utiliser n'importe quelle photo d'espace urbain.")
        return
    
    # Infos projet
    project_info = {
        "title": "Réaménagement Place de la République",
        "location": "Tunis, Tunisie",
        "client": "Municipalité de Tunis",
        "date": "2024-02-21"
    }
    
    # Récupérer orchestrateur
    orchestrator = get_orchestrator_service()
    
    # Option 1: Analyse rapide (détection + coûts uniquement)
    print("📊 Mode disponible:")
    print("  1. Analyse rapide (détection + coûts)")
    print("  2. Pipeline complet (tous services IA)")
    print()
    
    mode = input("Choisissez mode [1/2]: ").strip()
    
    if mode == "1":
        # Mode rapide
        print("\n⚡ Exécution analyse rapide...\n")
        results = orchestrator.process_quick_analysis(test_image)
        
    else:
        # Pipeline complet
        print("\n🚀 Exécution pipeline complet...\n")
        results = orchestrator.process_complete_pipeline(
            image_path=test_image,
            project_info=project_info,
            scenario_type="moderate",  # conservative | moderate | innovative
            generate_all=True
        )
    
    # Afficher résultats
    print("\n" + "═" * 60)
    print("RÉSULTATS FINAUX")
    print("═" * 60)
    
    if results["status"] == "success":
        print("✅ Statut: SUCCÈS")
        print(f"⏱️  Durée: {results.get('duration_seconds', 0):.1f}s")
        print()
        
        # Détection
        if "detection" in results["steps"]:
            det = results["steps"]["detection"]
            print(f"🔍 Détection: {det['total_problems']} problème(s)")
            print(f"   Image annotée: {det.get('annotated_image', 'N/A')}")
        
        # Scénarios
        if "scenarios" in results["steps"]:
            scenarios = results["steps"]["scenarios"]
            print(f"🎨 Scénarios: {len(scenarios)} générés")
            for sc in scenarios:
                if "image_path" in sc:
                    print(f"   {sc['type']}: {sc['image_path']}")
        
        # Coûts
        if "cost_estimation" in results["steps"]:
            cost = results["steps"]["cost_estimation"]
            print(f"💰 Coût total: {cost['total_cost_tnd']:,.2f} TND")
        
        # Audio
        if "audio" in results["steps"]:
            audio = results["steps"]["audio"]
            if audio.get("success"):
                print(f"🔊 Audio: {audio['audio_path']} ({audio['duration_seconds']}s)")
        
        # Vidéo
        if "video" in results["steps"]:
            video = results["steps"]["video"]
            if video.get("success"):
                print(f"🎥 Vidéo: {video['video_path']} ({video['duration_seconds']}s)")
        
        # PDF
        if "pdf_report" in results["steps"]:
            pdf = results["steps"]["pdf_report"]
            if pdf.get("success"):
                print(f"📄 Rapport: {pdf['pdf_path']} ({pdf['file_size_mb']} MB)")
        
    else:
        print("❌ Statut: ÉCHEC")
        print(f"   Erreur: {results.get('error', 'Inconnue')}")
    
    print()
    
    # Décharger modèles
    print("🗑️  Nettoyage mémoire...")
    orchestrator.unload_all_models()
    
    print("\n✅ Test terminé!")


def test_individual_services():
    """Test services individuellement"""
    
    from app.services import (
        get_detection_service,
        get_cost_estimation_service
    )
    
    print("🧪 Test services individuels\n")
    
    test_image = "./test_data/urban_space.jpg"
    
    if not os.path.exists(test_image):
        print(f"❌ Image test non trouvée: {test_image}")
        return
    
    # Test 1: Détection
    print("1️⃣  Test détection YOLOv8...")
    detection_svc = get_detection_service()
    
    results = detection_svc.detect_problems(test_image)
    print(f"   ✅ {results['total_problems']} problèmes détectés")
    print(f"   Résumé: {results['summary']}")
    print()
    
    # Test 2: Estimation coûts
    print("2️⃣  Test estimation coûts Llama...")
    cost_svc = get_cost_estimation_service()
    
    estimation = cost_svc.estimate_costs(results)
    print(f"   ✅ Coût estimé: {estimation['total_cost_tnd']:,.2f} TND")
    print()


def check_system_status():
    """Vérifie statut système"""
    
    from app.services import get_orchestrator_service
    
    print("🔧 Statut système UrbanFix AI\n")
    
    orchestrator = get_orchestrator_service()
    status = orchestrator.get_system_status()
    
    print("Services:")
    for service, state in status["services"].items():
        print(f"  • {service}: {state}")
    
    print("\nSystème:")
    print(f"  • CUDA disponible: {status['system']['cuda_available']}")
    if status['system']['cuda_device']:
        print(f"  • GPU: {status['system']['cuda_device']}")
    
    print("\nConfiguration:")
    print(f"  • Groq configuré: {status['config']['groq_configured']}")
    print(f"  • Classes détection: {len(status['config']['detection_classes'])}")
    
    print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test UrbanFix AI Services")
    parser.add_argument(
        "--mode",
        choices=["full", "individual", "status"],
        default="full",
        help="Mode de test"
    )
    
    args = parser.parse_args()
    
    if args.mode == "full":
        test_complete_pipeline()
    elif args.mode == "individual":
        test_individual_services()
    elif args.mode == "status":
        check_system_status()
