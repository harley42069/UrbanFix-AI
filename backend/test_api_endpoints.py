"""
Test des API Endpoints
Script de test des endpoints REST de l'API UrbanFix AI
"""

import requests
import json
import time
import os
from pathlib import Path

import pytest

# Configuration
BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_API_ENDPOINT_TESTS") != "1",
    reason="Manual live-server API smoke tests; set RUN_API_ENDPOINT_TESTS=1 to run.",
)


@pytest.fixture
def file_id():
    return test_upload_endpoint()


@pytest.fixture
def analysis_id(file_id: str):
    return test_analysis_endpoints(file_id)


def print_section(title: str):
    """Affiche un titre de section"""
    print("\n" + "=" * 70)
    print(f"📋 {title}")
    print("=" * 70)


def print_result(name: str, response):
    """Affiche le résultat d'un test"""
    status = "✅" if response.status_code < 400 else "❌"
    print(f"{status} {name}: {response.status_code}")
    if response.status_code < 400:
        try:
            data = response.json()
            print(f"   Réponse: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
        except:
            print(f"   Réponse: {response.text[:200]}...")
    else:
        print(f"   Erreur: {response.text[:200]}")
    print()


def test_root_endpoints():
    """Test des endpoints racine"""
    print_section("Tests Endpoints Racine")
    
    # Root
    response = requests.get(f"{BASE_URL}/")
    print_result("GET /", response)
    
    # Health
    response = requests.get(f"{BASE_URL}/health")
    print_result("GET /health", response)
    
    # Version
    response = requests.get(f"{BASE_URL}/version")
    print_result("GET /version", response)


def test_upload_endpoint():
    """Test de l'endpoint upload"""
    print_section("Tests Upload")
    
    # Créer une image de test
    test_image_path = Path("test_data/test_image.jpg")
    
    if not test_image_path.exists():
        print("⚠️  Image de test non trouvée. Créez test_data/test_image.jpg")
        return None
    
    # Upload d'une image
    with open(test_image_path, "rb") as f:
        files = {"file": ("test_image.jpg", f, "image/jpeg")}
        response = requests.post(f"{API_V1}/upload/image", files=files)
    
    print_result("POST /upload/image", response)
    
    if response.status_code < 400:
        data = response.json()
        file_id = data.get("data", {}).get("file_id")
        
        # Info fichier
        if file_id:
            response = requests.get(f"{API_V1}/upload/info/{file_id}")
            print_result(f"GET /upload/info/{file_id}", response)
        
        return file_id
    
    return None


def test_analysis_endpoints(file_id: str):
    """Test des endpoints d'analyse"""
    print_section("Tests Analyse")
    
    if not file_id:
        print("⚠️  Pas de file_id, skip des tests d'analyse")
        return None
    
    # Détection seule
    response = requests.post(
        f"{API_V1}/analysis/detect-only",
        params={
            "file_id": file_id,
            "confidence_threshold": 0.25,
            "visualize": True
        }
    )
    print_result("POST /analysis/detect-only", response)
    
    # Analyse rapide
    quick_request = {
        "file_id": file_id,
        "confidence_threshold": 0.25,
        "region": "Tunis"
    }
    response = requests.post(f"{API_V1}/analysis/quick", json=quick_request)
    print_result("POST /analysis/quick", response)
    
    # Analyse complète (asynchrone)
    full_request = {
        "file_id": file_id,
        "project_name": "Test UrbanFix",
        "location": "Tunis, La Marsa",
        "region": "Tunis",
        "scenario_type": "moderate",
        "num_scenarios": 2,
        "confidence_threshold": 0.25,
        "generate_audio": False,  # Skip audio pour test rapide
        "generate_video": False,  # Skip video pour test rapide
        "generate_report": True
    }
    response = requests.post(f"{API_V1}/analysis/full", json=full_request)
    print_result("POST /analysis/full", response)
    
    analysis_id = None
    if response.status_code < 400:
        data = response.json()
        analysis_id = data.get("data", {}).get("analysis_id")
        print(f"   Analysis ID: {analysis_id}")
        
        # Attendre un peu et vérifier le statut
        print("\n   ⏳ Attente de 5 secondes pour la progression...")
        time.sleep(5)
        
        if analysis_id:
            response = requests.get(f"{API_V1}/analysis/status/{analysis_id}")
            print_result(f"GET /analysis/status/{analysis_id}", response)
    
    # Liste des analyses
    response = requests.get(f"{API_V1}/analysis/list")
    print_result("GET /analysis/list", response)
    
    # Statut système
    response = requests.get(f"{API_V1}/analysis/system/status")
    print_result("GET /analysis/system/status", response)
    
    return analysis_id


def test_reports_endpoints(analysis_id: str):
    """Test des endpoints de rapports"""
    print_section("Tests Rapports")
    
    if not analysis_id:
        print("⚠️  Pas d'analysis_id, skip des tests de rapports")
        return
    
    # Attendre que l'analyse soit terminée (timeout 60s)
    print("⏳ Attente de la fin de l'analyse (max 60s)...")
    for i in range(12):
        response = requests.get(f"{API_V1}/analysis/status/{analysis_id}")
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            progress = data.get("progress", 0)
            print(f"   Statut: {status} - Progression: {progress*100:.1f}%")
            
            if status == "completed":
                break
            elif status == "failed":
                print(f"   ❌ Analyse échouée: {data.get('error')}")
                return
        
        time.sleep(5)
    
    # Générer un rapport
    report_request = {
        "analysis_id": analysis_id,
        "include_executive_summary": True,
        "include_detailed_costs": True,
        "include_technical_specs": True,
        "include_timeline": True,
        "language": "fr"
    }
    response = requests.post(f"{API_V1}/reports/generate", json=report_request)
    print_result("POST /reports/generate", response)
    
    if response.status_code < 400:
        data = response.json()
        report_id = data.get("data", {}).get("report_id")
        
        if report_id:
            # Attendre la génération
            print("⏳ Attente de la génération du rapport (max 30s)...")
            for i in range(6):
                time.sleep(5)
                response = requests.get(f"{API_V1}/reports/status/{report_id}")
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("data", {}).get("status")
                    print(f"   Statut: {status}")
                    if status == "completed":
                        break
            
            # Statut du rapport
            response = requests.get(f"{API_V1}/reports/status/{report_id}")
            print_result(f"GET /reports/status/{report_id}", response)
            
            # Preview
            response = requests.get(f"{API_V1}/reports/preview/{report_id}")
            print_result(f"GET /reports/preview/{report_id}", response)
    
    # Liste des rapports
    response = requests.get(f"{API_V1}/reports/list")
    print_result("GET /reports/list", response)


def test_websocket_info():
    """Affiche les infos sur les WebSockets"""
    print_section("Informations WebSocket")
    
    print("""
    Les WebSockets ne peuvent pas être testés avec requests.
    Utilisez un client WebSocket ou le script test_websocket.py
    
    Endpoints WebSocket disponibles:
    - ws://localhost:8000/api/v1/ws/analysis/{analysis_id}
    - ws://localhost:8000/api/v1/ws/global
    
    Commandes supportées:
    - {"type": "ping"} → réponse pong
    - {"type": "get_status"} → statut de l'analyse
    - {"type": "get_all_status"} → statut de toutes les analyses
    """)
    
    # Compter les connexions
    response = requests.get(f"{API_V1}/ws/connections/count")
    print_result("GET /ws/connections/count", response)


def main():
    """Fonction principale"""
    print("\n" + "🚀" * 35)
    print("Test des API Endpoints - UrbanFix AI")
    print("🚀" * 35)
    
    # Vérifier que le serveur est démarré
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("❌ Serveur non accessible. Démarrez-le avec: uvicorn app.main:app --reload")
            return
    except:
        print("❌ Serveur non accessible. Démarrez-le avec: uvicorn app.main:app --reload")
        return
    
    print("✅ Serveur accessible\n")
    
    # Tests
    test_root_endpoints()
    file_id = test_upload_endpoint()
    analysis_id = test_analysis_endpoints(file_id)
    test_reports_endpoints(analysis_id)
    test_websocket_info()
    
    print("\n" + "=" * 70)
    print("✅ Tests terminés!")
    print("=" * 70)
    print("\n📚 Documentation complète: http://localhost:8000/docs")
    print()


if __name__ == "__main__":
    main()
