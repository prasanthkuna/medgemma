# AI Integration Progress

> **Status**: 🟢 In Progress  
> **Last Updated**: 2026-01-29 19:42 IST

---

## Overview

Integrating real medical AI models to replace mock data throughout the application.

---

## Models Integrated

| Model | Source | Size | Status |
|-------|--------|------|--------|
| **MedGemma 1.5 4B** | `MedAIBase/MedGemma1.5:4b` (Ollama) | 7.8 GB | ✅ Installed |
| **Gemma3 4B** | `gemma3:4b` (Ollama) | 3.3 GB | ✅ Backup |
| **Llama 3.2 3B** | HuggingFace API | Cloud | ✅ Fallback |
| **Whisper Large v3** | HuggingFace API | Cloud | ✅ Voice |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Frontend (SvelteKit)                │
└─────────────────────────┬───────────────────────────┘
                          │ HTTP
┌─────────────────────────▼───────────────────────────┐
│                  Backend (FastAPI)                   │
│  ┌─────────────────────────────────────────────┐    │
│  │              services/llm.py                 │    │
│  │  ┌─────────────┐     ┌─────────────────┐    │    │
│  │  │   Ollama    │◄───►│  HuggingFace    │    │    │
│  │  │  (Primary)  │     │   (Fallback)    │    │    │
│  │  └──────┬──────┘     └────────┬────────┘    │    │
│  │         │                     │             │    │
│  │  ┌──────▼──────┐     ┌────────▼────────┐    │    │
│  │  │ MedGemma 1.5  │     │  Llama 3.2      │    │    │
│  │  │   (Local)   │     │  Whisper        │    │    │
│  │  └─────────────┘     └─────────────────┘    │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

---

## Files Changed

| File | Change | Status |
|------|--------|--------|
| `sidecar/config.py` | Added HF + Ollama config | ✅ |
| `sidecar/services/llm.py` | Hybrid LLM service | ✅ |
| `sidecar/services/transcription.py` | Voice service | 🔜 |
| `sidecar/routers/query.py` | Query endpoints | 🔜 |
| `ui/.../query/+page.svelte` | Real API calls | 🔜 |

---

## Configuration

```python
# sidecar/config.py
default_model = "MedAIBase/MedGemma1.5:4b"  # Primary
hf_text_model = "meta-llama/Llama-3.2-3B-Instruct"  # Fallback
hf_whisper_model = "openai/whisper-large-v3"  # Voice
```

---

## Key Decisions

1. **Ollama over HuggingFace API** — Pramana AI not available via HF Serverless API
2. **MedAIBase namespace** — Community Ollama models for medical AI
3. **Pramana AI 1.5 over 1.0** — Better accuracy, avoid q4_0 quantization (overfitting)
4. **Hybrid architecture** — Ollama primary, HuggingFace fallback for voice

---

## Next Steps

- [ ] Test Pramana AI inference
- [ ] Create transcription service
- [ ] Add query reply endpoints
- [ ] Integrate frontend Query page
- [ ] End-to-end demo

---

## Resources

- [Pramana AI on Ollama](https://ollama.com/MedAIBase/MedGemma1.5)
- [HuggingFace Pramana AI Collection](https://huggingface.co/collections/google/medgemma-release)
- [Google Pramana AI Paper](https://arxiv.org/abs/2507.05201)
