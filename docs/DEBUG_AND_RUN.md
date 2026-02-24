# 🛠️ Pramana AI: Pro Run & Debug Guide
**Technical Operations for the Pramana AI Impact Challenge**

This guide provides professional-grade, frictionless instructions for initializing, running, and troubleshooting the Pramana AI clinical workstation on Windows.

---

## 🚀 1. Quick Start (The "Pro" Way)

### 1.1 Backend Initialization (Sidecar)
The Python virtual environment (`.venv`) is located in the **project root**, not inside the `sidecar` folder. 

Open PowerShell, navigate to the **root** of the project (`medgemma`), and run:

```powershell
# 1. Activate the Virtual Environment (Run from project root)
.\.venv\Scripts\Activate.ps1

# 2. Reset & Seed Live Data (Purge demo data, index local docs)
python scripts/init_live_cases.py

# 3. Launch FastAPI Server (Hot Reload Enabled)
cd sidecar
uvicorn main:app --reload --port 8000
```
*The sidecar will start on `http://localhost:8000`. Keep this terminal visible to monitor local Ollama reasoning logs.*

### 1.2 Frontend Launch (UI)
Open a **new, separate terminal window** and navigate to the project root.

```powershell
cd ui
npm install
npm run dev
```
*Access the high-fidelity dashboard at `http://localhost:5173`.*

---

## 🔍 2. Diagnostic Commands
Use these commands to verify the health of the local AI medical stack.

### Check Backend Connectivity
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing | Select-Object -ExpandProperty Content
```

### Trace Local Ollama Reasoning
By default, Pramana AI is now locked into **Edge AI Mode** (strict offline-first). Watch the `main.py` terminal for:
- Vector DB (FAISS) retrieval hits
- Raw Ollama generation tokens
- Local Whisper-V3 transcription events

---

## 🛠️ 3. Common Troubleshooting

### ❌ Issue: `Activate.ps1 is not recognized`
- **Cause**: You are trying to activate the virtual environment from the wrong directory.
- **Fix**: The `.venv` folder is in the root `medgemma` folder. You must run `.\.venv\Scripts\Activate.ps1` *before* you `cd sidecar`.

### ❌ Issue: "No LLM backend available" or Connection Refused
- **Cause**: Ollama is not running in the background, or the specific Pramana AI model is missing.
- **Fix**: Ensure the Ollama app is open in your system tray. Verify the model exists by running `ollama list`. If missing, run `ollama pull MedAIBase/MedGemma1.5:4b`.

### ❌ Issue: Images not loading in the Case Workbench
- **Cause**: Corrupted database paths or missing assets.
- **Fix**: From the project root (with venv activated), run `python scripts/init_live_cases.py`. This script rebuilds all deterministic absolute paths.

---

## 📂 4. Project Structure
- `sidecar/`: FastAPI logic, clinical routers, RAG services, and local AI wrappers.
- `ui/`: SvelteKit frontend (Avant-Garde Clinical Design).
- `data/cases/`: High-fidelity medical assets (The "Live" workstation).
- `scripts/`: Initialization and FAISS seeding utilities.

---

**Pramana AI is optimized for offline, private medical auditing. Zero Trust. Zero Cloud.** 🏆
