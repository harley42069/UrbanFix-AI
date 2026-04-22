import base64, json
from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

with open("../test_data/rdd_with_detections.jpg", "rb") as f:
    image_data = base64.b64encode(f.read()).decode()

prompt = """Analyse cette image de rue/route et reponds UNIQUEMENT en JSON:
{
  "type_espace": "route/rue_etroite/boulevard/autoroute/banlieue",
  "longueur_estimee_m": 100,
  "largeur_rue_m": 6,
  "nb_poteaux_existants": 0,
  "surface_trottoirs_m2": 0,
  "surface_espaces_verts_m2": 0,
  "problemes_visibles": ["fissures"],
  "contexte": "description courte"
}"""

response = client.chat.completions.create(
    model="meta-llama/llama-4-scout-17b-16e-instruct",
    messages=[{
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
            {"type": "text", "text": prompt}
        ]
    }],
    max_tokens=300,
    temperature=0.1,
)
print(response.choices[0].message.content)
