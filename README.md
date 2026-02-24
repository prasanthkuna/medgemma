# Pramana AI: Offline-First Medical Audit Aide 🏥

[![Pramana AI](https://img.shields.io/badge/Model-Pramana AI-blueviolet)](https://huggingface.co/google/medgemma-2b)
[![Whisper](https://img.shields.io/badge/ASR-Whisper--V3-teal)](https://huggingface.co/openai/whisper-large-v3)
[![Docker](https://img.shields.io/badge/Orchestration-Docker--Compose-blue)](docker-compose.yml)

**Pramana AI** is a production-grade, offline-first clinical copilot designed to solve the **₹26,000 Crore medical claim crisis in India**. In a landscape where 11-13% of health claims are rejected—often due to missing documentation—Pramana AI provides a transparent, AI-driven pre-audit layer that runs entirely on hospital hardware.

---

## 🏛️ System Architecture

Pramana AI runs as a multi-tier local stack, ensuring that sensitive medical data never leaves the hospital's intranet.

```mermaid
graph TD
    User((Clinical Auditor)) -->|UI Interaction| UI[SvelteKit Frontend]
    UI -->|Agentic Transparency Logs| UI
    UI -->|REST API| Sidecar[FastAPI Sidecar]
    
    subgraph "Local Clinical AI Pipeline"
        Sidecar -->|Computer Vision| Vision[Blur & Resolution Check]
        Sidecar -->|Voice-to-Text| Whisper[Local Whisper-V3]
        Sidecar -->|Policy RAG| FAISS[FAISS Vector Search]
        Sidecar -->|Inference| Pramana AI[Pramana AI-2B / Llama 3.2]
    end
    
    FAISS -.->|Context| PolicyDocs[(Clinical Policy PDFs)]
    Pramana AI -->|Decision| AuditResult[Structured Justification]
    
    subgraph "Data Layer"
        Sidecar <--> DB[(SQLite: pramana.sqlite)]
        Sidecar <--> Store[(Local Data Volume)]
    end
```

---

## ✨ Clinical Transparency & Trust

Pramana AI eliminates the "Black Box" of medical auditing by providing **High-Fidelity Telemetry** into every step of the clinical reasoning process.

- **High-Fidelity Logs**: Replaces standard loading bars with granular data streams showing Vision confidence scores (Blur/Resolution), RAG similarity distances, and real-time indexing stages.
- **Brutalist Professional Design**: A specialized utilitarian interface using **JetBrains Mono** typography, designed for high-density technical review.
- **Agentic Reasoning**: The system reveals the AI's internal "Clinical Auditor" thoughts as it parses patient records against insurance policy rules (Star Health, ICICI Lombard, etc.).

---

## 🌎 Impact: The Professional Intervention

While the **Clinical Administrator (TPA)** is the user, the **Indian Family** is the beneficiary. Pramana AI bridges the ₹26,000 Cr trust gap by:
- **Zero Privacy Leakage**: All clinical evidence stays local, ensuring 100% compliance with NHA and HIPAA medical privacy standards.
- **Physician-First Justification**: TPAs use **Whisper-V3** to accurately capture the doctor's clinical "why" and map it to policy language, reducing arbitrary denials.
- **Audit Vigilance**: Automatically detects documentation gaps (missing bills, blurry labs) so administrators can plan the case submission with 100% readiness.

---

## 🏗️ TPA / Administrator Workflow

1. **Intake & Scan**: Upload clinical records (PDFs/Images). The system auto-classifies the documents.
2. **Readiness Audit**: The Agentic Pipeline cross-references files with indexed clinical policies.
3. **Clinical Justification**: Review the generated draft, synthesized from physician dictation and policy matches.
4. **Rescan & Plan**: If docs are missing ("Red/Amber" ring), the TPA can prompt for missing evidence and rescan to reach "Green" readiness.

## 🚀 Quick Start (Docker)

### 1. Prerequisites
- Docker & Docker Compose.
- **Ollama** running on the host (for GPU-accelerated Pramana AI inference).

### 2. Launch the Stack
```bash
cp .env.template .env
docker-compose up --build
```
- **UI**: [http://localhost](http://localhost)
- **API**: [http://localhost:8000](http://localhost:8000)

---
© 2026 Pramana AI. Created for the Pramana AI Impact Challenge.
