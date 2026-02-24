# 🏆 Pramana AI Impact Challenge: Hackathon Strategy Guide

This document is your definitive guide to winning the **Edge AI Track ($5,000)** and the **Agentic Workflow Track ($10,000)**. Use this narrative in your Devpost submission and live demo.

## The Core Value Proposition
Pramana AI is not a simple LLM wrapper. It is a **dual-engine, privacy-first architectural marvel**.
1.  **Safety First (Deterministic):** It uses hard rules and vision AI to guarantee no hallucinations on medical score calculations. 
2.  **Intelligence Second (Agentic):** It uses a fully localized, multi-agent RAG pipeline (Pramana AI + FAISS + Whisper) to write brilliant, human-in-the-loop justifications.

---

## 🎯 Track 1: Winning "Edge AI" ($5,000)

**The Judging Criteria:** *Runs locally, respects data privacy, works in low-bandwidth environments.*

### What to highlight in your write-up:
*   **Zero-Cloud Footprint:** Explain that hospitals **cannot** upload patient data to OpenAI or HuggingFace due to HIPAA/GDPR. Pramana AI solves this by running 100% of its inference on the literal edge (the local machine).
*   **Local Whisper V3:** Highlight that your dictation feature uses Python `whisper` running directly on the CPU/GPU, ensuring highly sensitive doctor notes never leave the device.
*   **The "King Mode" UI Flex:** During your demo, show the **Policy Library** page. Do not just talk about it—*show it*. Upload the `ICICI_Orthopedic_Joint_Guidelines_2026.pdf`. The UI will stream local terminal logs showing `nomic-embed-text` parsing paragraphs and generating high-dimensional vectors in real-time. This visibly proves the Edge AI is working hard in the background.

---

## 🤖 Track 2: Winning "Agentic Workflow" ($10,000)

**The Judging Criteria:** *AI acts as an agent, iterating, validating, and interacting with tools/data.*

### What to highlight in your write-up:
*   **The "Amber to Green" Loop (Tool Use):** Show the judges Case 1 (The Ortho Knee for ICICI Lombard). It gets an AMBER score (70/100) because the deterministic engine caught a missing Implant Sticker. Upload the sticker, click Re-Analyze, and watch the system *agentically* update its own assessment to GREEN.
*   **The Ultimate RAG Agent:** Open Case 2 (Star Health). Record an audio dictation saying: *"Patient had complications, needed 4 days in ICU. Review policy to justify."*
*   **The Big Reveal:** When you click "Generate AI Draft", Pramana AI doesn't just guess. It acts as an **Agent** by:
    1.  Taking the transcribed audio.
    2.  Querying the local FAISS semantic database you built in Act 1.
    3.  Retrieving the specific paragraph about "extended ICU stays for complications" from the Star Health policy.
    4.  Drafting a letter that explicitly cites the policy guidelines.
*   **King Mode (Human-in-the-Loop):** Emphasize that the AI *drafts* it, but the human *approves* it before sending it to the Payer. This is the definition of a safe, enterprise-grade Agentic Workflow.

## The Demo Script (3 Minutes to Win)

1.  **[0:00 - 0:45] The Setup & Edge Flex:** Open the "Policy Library". Upload the ICICI PDF. Let them watch the cinematic terminal logs build the FAISS vectors locally. "This is 100% offline, preserving HIPAA."
2.  **[0:45 - 1:30] The Deterministic Safety Net:** Open an AMBER case. Show them *why* it failed (missing sticker). "An LLM might hallucinate a score, so we use strict Python rules and Vision AI for scoring parity."
3.  **[1:30 - 2:30] The Agentic Drafting:** Open a RED case. Click the microphone. Dictate clinical reasoning. Hit 'Generate'. Watch Pramana AI pull from the FAISS database and write a perfect, cited appeal.
4.  **[2:30 - 3:00] The Close:** Show the Editable Draft. "The AI does the heavy lifting, the human reviews it, we submit to the Payer faster than ever before. Pramana AI."
