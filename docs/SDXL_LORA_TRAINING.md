# SDXL LoRA Training Guide - UrbanFix AI (tnrenovation)

This guide explains how to build and train a SDXL LoRA for Tunisian Urban Renovation using trigger token:

tnrenovation

Target usage after training:
- img2img generation in UrbanFix AI
- optional ControlNet canny guidance

## 1) Dataset organization (local, outside git)

Expected local structure:

C:/Dev/Urbanfix-ai/data/tnrenovation/
  images/
    style_after/
    before_degraded/
    pairs/<case_id>/before.jpg and after.jpg (optional)
  captions/
  metadata.jsonl

Notes:
- Do not commit images or LoRA weights.
- Keep dataset private.

## 2) Windows PowerShell commands (prepare -> caption -> metadata -> sanity)

From repository root C:/Dev/Urbanfix-ai:

python training/sdxl_lora/scripts/01_prepare_dataset.py --data_dir C:/Dev/Urbanfix-ai/data/tnrenovation --max_side 1536
python training/sdxl_lora/scripts/02_caption_blip2.py --data_dir C:/Dev/Urbanfix-ai/data/tnrenovation --device cuda
python training/sdxl_lora/scripts/03_make_metadata.py --data_dir C:/Dev/Urbanfix-ai/data/tnrenovation
python training/sdxl_lora/scripts/04_sanity_check_dataset.py --data_dir C:/Dev/Urbanfix-ai/data/tnrenovation

If CUDA is unavailable locally, use:

python training/sdxl_lora/scripts/02_caption_blip2.py --data_dir C:/Dev/Urbanfix-ai/data/tnrenovation --device cpu

Important:
- metadata.jsonl uses relative file paths only.
- sanity check exits non-zero when dataset is invalid.

## 3) Upload dataset to Kaggle (private)

Recommended approach:
1. Create a private Kaggle dataset.
2. Upload the full folder tnrenovation including:
   - images/
   - captions/
   - metadata.jsonl
3. Attach that dataset to your Kaggle notebook.

Example mounted path in Kaggle:

/kaggle/input/tnrenovation/tnrenovation

## 4) Run training on Kaggle

In Kaggle notebook terminal:

bash training/sdxl_lora/kaggle/train_kaggle.sh

The script will:
- install requirements from training/sdxl_lora/kaggle/requirements.txt
- download official diffusers SDXL LoRA training script
- train with SDXL base model stabilityai/stable-diffusion-xl-base-1.0
- use resolution 1024 first
- fallback to 768 if 1024 run fails (for memory constraints)
- save outputs to /kaggle/working/tnrenovation_lora_out
- list generated safetensors files

## 5) Retrieve trained LoRA file

Expected artifact location (example):

/kaggle/working/tnrenovation_lora_out/*.safetensors

Download the best .safetensors file and place it in project backend:

backend/models/lora/tnrenovation.safetensors

## 6) Enable LoRA in diffusers inference

Recommended LoRA scale range:
- 0.6 to 0.9

Typical usage pattern (conceptual):
1. Load SDXL img2img pipeline
2. Load LoRA weights from backend/models/lora/tnrenovation.safetensors
3. Set adapter scale to 0.6-0.9
4. Prompt includes trigger token tnrenovation

Example prompt pattern:

tnrenovation, renovated tunisian urban street, white plaster, ochre walls, arched facade, clean sidewalk, greenery, modern public lighting

## 7) Inference settings for 6GB VRAM

For constrained GPU environments, prefer:
- enable_model_cpu_offload
- enable_attention_slicing
- generation size around 768 (instead of 1024)
- ControlNet canny for structure preservation

Recommended practical setup:
- img2img strength around 0.45 to 0.65
- LoRA scale 0.6 to 0.9
- canny conditioning to preserve road and facade geometry

## 8) UrbanFix deployment checklist

1. LoRA file exists at:
   backend/models/lora/tnrenovation.safetensors
2. Prompt includes trigger token:
   tnrenovation
3. Inference path configured for img2img + optional ControlNet canny
4. For 6GB cards, keep 768 default and only use 1024 when stable
