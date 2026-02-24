# ULTRATHINK: Draft Generation & UI/UX Architecture Rethink

## 1. The Placeholder Mystery (And the Pro Fix)
**Why is Pramana AI hallucinating placeholders like `[Date of Surgery]`?**

I tracked the execution path in `sidecar/routers/query.py`. Here is the critical flaw in the current architecture:
When the `generate_draft()` API is called, it builds a `doc_list` to send to the LLM. However, **it is only sending the filenames** of the patient's records, not the actual patient data! 

Because you are using local Pramana AI 1.5 4B, the model recognizes it is supposed to write a clinical summary, but because it has absolutely zero patient data in its context window, it intelligently generates a complete template filled with `[Date]` and `[Insert Findings Here]` tags rather than hallucinating fake medical data.

### The Architect Fix (Data Re-use)
*You are completely right.* We already ran a massive, heavy extraction during the initial "Analyze Case" phase! That data is sitting perfectly structured inside the `case_analysis` SQLite table (`missing_items`, `quality_issues`, `citations`).

Instead of blindly re-opening PDFs and burning CPU cycles, we must modify `query.py` to simply query the `case_analysis` table for the current `case_id`, and immediately inject that highly-distilled clinical summary straight into the `DRAFT_PROMPT`. This is instantaneous, requires zero PDF parsing on the draft step, and gives Pramana AI exactly what it needs to replace the placeholders with real data! 

---

## 2. Editable Drafts (Doctor-in-the-Loop)
You are 100% correct. An AI Clinical Copilot should *never* automatically lock decisions without human oversight.

### Architecture Plan:
1. **Backend**: We will create a new endpoint `PUT /api/cases/{case_id}/query/draft`. This will accept a modified JSON payload and update the `case_drafts` table where `status = 'draft'`.
2. **Frontend UI**: In the Draft Panel, if the status is `'draft'`, the text fields (Clinical Summary, Justification, Next Steps) will be rendered as editable `textarea` blocks. 
3. **Approval**: The "Approve & Lock Draft" button will save the final edits *and* lock the status in one fluid network call.

---

## 3. Dictation Review Pipeline
Sending the audio straight to the LLM generation pipeline is a black-box UX. We need to insert a "Confirmation Stage".

### Architecture Plan:
1. **Break the API into Two Steps**:
   - `POST /api/transcribe`: Only processes the Whisper audio and returns raw text.
   - `POST /api/cases/{id}/query/draft`: Only accepts text (the final query), no audio upload.
2. **Frontend UX**: 
   - When the doctor stops recording, the UI shows a "Transcribing..." spinner.
   - The text appears in a chat box: *"You dictated: [text]"*.
   - The doctor can manually edit the text (e.g., fixing a misheard drug name) before clicking a final **"Generate AI Analytics"** button.

## Next Steps
Since you explicitly asked me not to code, I have paused execution. If you approve this strategic plan, let me know and I will execute all three architectural fixes across the SvelteKit frontend and FastAPI backend!
