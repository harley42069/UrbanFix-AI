# app/core/config.py

"""
Configuration centralisée application
Variables chargées depuis .env
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List


class Settings(BaseSettings):
    """
    Paramètres configuration
    
    Toutes les variables peuvent être surchargées via fichier .env
    """
    
    # APPLICATION

    APP_NAME: str = "UrbanFix AI"
    PROJECT_NAME: str = "UrbanFix AI"  # Alias pour APP_NAME
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True  # Mode debug (mettre False en production)  
    
   
    # API
    
    API_V1_PREFIX: str = "/api/v1"
    BASE_URL: str = "http://localhost:8000"
    
    # CORS - Origines autorisées (Frontend)
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    
    # ═══════════════════════════════════════════════════════
    # BASE DE DONNÉES
    # ═══════════════════════════════════════════════════════
    
    # URL connexion PostgreSQL
    # Format: postgresql://user:password@host:port/database
    DATABASE_URL: str = "sqlite:///./urbanfix.db"  # SQLite par défaut (dev)
    
    # Pool connexions
    DB_POOL_SIZE: int = 5       
    DB_MAX_OVERFLOW: int = 10

    # Background processing
    ENABLE_CELERY: bool = False
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    EXTERNAL_SERVICE_RETRIES: int = 3
    EXTERNAL_SERVICE_BACKOFF_SECONDS: float = 2.0
    
    # ═══════════════════════════════════════════════════════
    # SÉCURITÉ & AUTHENTIFICATION
    # ═══════════════════════════════════════════════════════
    
    # Clé secrète JWT (CHANGER EN PRODUCTION !)
    SECRET_KEY: str = "changez-cette-cle-secrete-en-production-utilisez-secrets-generator"
    
    # Algorithme signature JWT
    ALGORITHM: str = "HS256"
    
    # Durée validité token (minutes)

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 heures
    ALLOW_GUEST: bool = False
    
    # ═══════════════════════════════════════════════════════
    # SERVICES EXTERNES (APIs)
    # ═══════════════════════════════════════════════════════
    
    # Groq (Llama 3.1) - Estimation coûts
    GROQ_API_KEY: Optional[str] = None
    
    # OpenAI (optionnel - GPT-4 Vision)
    OPENAI_API_KEY: Optional[str] = None
    
    # Replicate (SDXL génération images)
    REPLICATE_API_KEY: Optional[str] = None
    
    # Mapbox (cartes)
    MAPBOX_TOKEN: Optional[str] = None
    
    # Cloudinary (stockage images)
    CLOUDINARY_CLOUD_NAME: Optional[str] = None
    CLOUDINARY_API_KEY: Optional[str] = None
    CLOUDINARY_API_SECRET: Optional[str] = None
    
    # Hugging Face (modèles IA)
    HUGGINGFACE_TOKEN: Optional[str] = None
    
    # ═══════════════════════════════════════════════════════
    # MODÈLES IA / ML
    # ═══════════════════════════════════════════════════════
    
    # YOLOv8 Detection
    YOLO_MODEL_PATH: str = "./models/yolo_road_damage_best.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.25
    YOLO_IOU_THRESHOLD: float = 0.45
    
    # Classes détection (6 types problèmes urbains tunisiens)
    DETECTION_CLASSES: List[str] = [
        "route_degradee",       # Routes/chaussées endommagées
        "dechet",               # Déchets/ordures
        "eclairage_defectueux", # Éclairage public cassé
        "vegetation_envahissante", # Végétation à élaguer
        "mobilier_casse",       # Mobilier urbain cassé/vandalisme
        "graffiti"              # Tags/graffitis
    ]
    
    # SDXL Génération Images
    SDXL_MODEL_ID: str = "stabilityai/stable-diffusion-xl-base-1.0"
    SDXL_LORA_PATH: Optional[str] = "./models/lora_tunisia_urban.safetensors"
    SDXL_NUM_INFERENCE_STEPS: int = 30
    SDXL_GUIDANCE_SCALE: float = 7.5
    SDXL_NUM_SCENARIOS: int = 3  # Nombre scénarios à générer
    
    # Prompts SDXL pour contexte tunisien
    SDXL_BASE_PROMPT: str = "modern tunisian urban space, mediterranean architecture, clean streets, palm trees, sunny day, high quality, photorealistic, 4k"
    SDXL_NEGATIVE_PROMPT: str = "blurry, low quality, distorted, ugly, disfigured, oversaturated"
    
    # Llama 3.3 (Groq) - Estimation coûts
    GROQ_MODEL_ID: str = "llama-3.3-70b-versatile"
    GROQ_TEMPERATURE: float = 0.3  # Plus précis pour estimations
    GROQ_MAX_TOKENS: int = 2000
    
    # Base de données coûts Tunisie (TND)
    COST_DATABASE: dict = {
        "route_degradee": {"min": 150, "max": 500, "unit": "m²"},
        "dechet": {"min": 50, "max": 200, "unit": "tonne"},
        "eclairage_defectueux": {"min": 300, "max": 800, "unit": "unité"},
        "vegetation_envahissante": {"min": 80, "max": 250, "unit": "m²"},
        "mobilier_casse": {"min": 200, "max": 1500, "unit": "unité"},
        "graffiti": {"min": 50, "max": 300, "unit": "m²"}
    }
    
    # Bark TTS (Audio)
    BARK_MODEL_ID: str = "suno/bark"
    BARK_VOICE_PRESET: str = "v2/fr_speaker_6"  # Voix française
    BARK_SAMPLE_RATE: int = 24000
    
    # Stable Video Diffusion
    SVD_MODEL_ID: str = "stabilityai/stable-video-diffusion-img2vid-xt"
    SVD_NUM_FRAMES: int = 25  # ~1 seconde à 25 fps
    SVD_FPS: int = 25
    SVD_MOTION_BUCKET_ID: int = 127
    
    # MoviePy (montage vidéo)
    VIDEO_OUTPUT_FPS: int = 25
    VIDEO_OUTPUT_CODEC: str = "libx264"
    VIDEO_OUTPUT_AUDIO_CODEC: str = "aac"
    VIDEO_TRANSITION_DURATION: float = 1.0  # secondes
    
    # PDF Generation
    PDF_PAGE_SIZE: str = "A4"
    PDF_FONT_FAMILY: str = "Helvetica"
    PDF_INCLUDE_IMAGES: bool = True
    PDF_INCLUDE_COSTS: bool = True
    PDF_LANGUAGE: str = "fr"
    
    # Stockage modèles et sorties
    MODELS_DIR: str = "./models"
    OUTPUT_DIR: str = "./outputs"
    OUTPUTS_DIR: str = "./outputs"  # Alias pour OUTPUT_DIR
    TEMP_DIR: str = "./temp"
    
    # ═══════════════════════════════════════════════════════
    # UPLOAD FICHIERS
    # ═══════════════════════════════════════════════════════
    
    # Taille max upload (bytes) - 10MB par défaut
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024

    # Rate limiting (dev)
    DEV_RATE_LIMIT_ENABLED: bool = True
    DEV_RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    
    # Extensions autorisées
    ALLOWED_IMAGE_EXTENSIONS: List[str] = [".jpg", ".jpeg", ".png", ".webp"]
    
    # Dossier uploads local (dev)
    UPLOAD_DIR: str = "./uploads"
    UPLOADS_DIR: str = "./uploads"  # Alias pour UPLOAD_DIR
    
    # ═══════════════════════════════════════════════════════
    # CONFIGURATION PYDANTIC
    # ═══════════════════════════════════════════════════════
    
    model_config = SettingsConfigDict(
        env_file=".env",           # Charge variables depuis .env
        case_sensitive=True,       # Sensible à la casse
        extra="ignore"             # Ignore variables inconnues
    )


# ═══════════════════════════════════════════════════════
# INSTANCE GLOBALE (Singleton)
# ═══════════════════════════════════════════════════════

settings = Settings()
 

# ═══════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════

def get_settings() -> Settings:
    """
    Retourne instance settings
    Utile pour dependency injection FastAPI
    """
    return settings




























