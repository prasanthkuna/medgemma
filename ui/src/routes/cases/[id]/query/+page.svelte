<script lang="ts">
    import { onMount, onDestroy } from "svelte";
    import { generateDraft, approveDraft } from "$lib/api";
    import type { PageData } from "./$types";

    export let data: PageData;

    let caseData: any = null;
    let loading = true;
    let queryText = "";
    let generating = false;
    let transcribing = false;
    let draft: any = null;
    let transcript = "";
    let approved = false;
    let streamLogs: {
        level: string;
        message: string;
        timestamp: string;
        icon?: string;
    }[] = [];

    // Mic recording
    let isRecording = false;
    let mediaRecorder: MediaRecorder | null = null;
    let audioChunks: Blob[] = [];
    let audioBlob: Blob | null = null;
    let recordingDuration = 0;
    let recordingTimer: any = null;

    onMount(async () => {
        try {
            const res = await fetch(`/api/cases/${data.caseId}`);
            if (res.ok) {
                const c = await res.json();
                caseData = {
                    ...c,
                    patient: c.patient_alias || "Unknown",
                    score: c.readiness_score || 0,
                    band: c.readiness_band || null,
                };
            }
            // Load persisted draft if available
            const draftRes = await fetch(
                `/api/cases/${data.caseId}/query/latest`,
            );
            if (draftRes.ok) {
                const saved = await draftRes.json();
                if (saved.draft) {
                    draft =
                        typeof saved.draft === "string"
                            ? JSON.parse(saved.draft)
                            : saved.draft;
                    transcript = saved.transcript || "";
                    approved = saved.approved || false;
                }
            }
        } catch (e) {
            console.error(e);
        } finally {
            loading = false;
        }
    });

    onDestroy(() => {
        if (recordingTimer) clearInterval(recordingTimer);
        if (mediaRecorder && mediaRecorder.state === "recording") {
            mediaRecorder.stop();
        }
    });

    async function toggleRecording() {
        if (isRecording) {
            // Stop recording
            mediaRecorder?.stop();
            isRecording = false;
            if (recordingTimer) {
                clearInterval(recordingTimer);
                recordingTimer = null;
            }
        } else {
            // Start recording
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    audio: true,
                });
                audioChunks = [];
                audioBlob = null;
                recordingDuration = 0;
                mediaRecorder = new MediaRecorder(stream, {
                    mimeType: "audio/webm",
                });
                mediaRecorder.ondataavailable = (e) => {
                    if (e.data.size > 0) audioChunks.push(e.data);
                };
                mediaRecorder.onstop = async () => {
                    audioBlob = new Blob(audioChunks, { type: "audio/webm" });
                    stream.getTracks().forEach((t) => t.stop());

                    // Auto-transcribe immediately after capture
                    if (audioBlob) {
                        transcribing = true;
                        try {
                            const file = new File(
                                [audioBlob],
                                "dictation.webm",
                                { type: "audio/webm" },
                            );
                            const tRes = await import("$lib/api").then((m) =>
                                m.transcribeAudio(data.caseId, file),
                            );
                            transcript = tRes.transcript || "";
                        } catch (e) {
                            console.error("Transcription failed", e);
                            transcript =
                                "[Transcription failed. Please type your notes manually.]";
                        } finally {
                            transcribing = false;
                            audioBlob = null; // Clear blob since we have the text
                        }
                    }
                };
                mediaRecorder.start();
                isRecording = true;
                recordingTimer = setInterval(() => {
                    recordingDuration++;
                }, 1000);
            } catch (e) {
                console.error("Mic access denied:", e);
                alert(
                    "Microphone access is required for voice dictation. Please allow mic access in your browser settings.",
                );
            }
        }
    }

    function formatDuration(sec: number) {
        const m = Math.floor(sec / 60)
            .toString()
            .padStart(2, "0");
        const s = (sec % 60).toString().padStart(2, "0");
        return `${m}:${s}`;
    }

    function removeRecording() {
        audioBlob = null;
        audioChunks = [];
        recordingDuration = 0;
    }

    async function handleGenerate() {
        if ((!queryText.trim() && !transcript.trim()) || generating) return;
        generating = true;
        approved = false; // Reset approval state on new run
        draft = null;
        streamLogs = [];
        try {
            const formData = new FormData();
            formData.append(
                "query_text",
                queryText || "Justify this procedure",
            );
            if (transcript) formData.append("transcript", transcript);

            const response = await fetch(
                `/api/cases/${data.caseId}/query/draft-stream`,
                {
                    method: "POST",
                    body: formData,
                },
            );

            if (!response.ok) {
                throw new Error("Draft stream failed to connect");
            }

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            if (reader) {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const chunks = buffer.split("\n\n");
                    buffer = chunks.pop() || "";

                    for (const chunk of chunks) {
                        if (!chunk.trim()) continue;
                        const lines = chunk.split("\n");
                        let eventType = "message";
                        let eventData = "";

                        for (const line of lines) {
                            if (line.startsWith("event: ")) {
                                eventType = line.slice(7).trim();
                            } else if (line.startsWith("data: ")) {
                                eventData = line.slice(6).trim();
                            }
                        }

                        if (eventData) {
                            try {
                                const parsed = JSON.parse(eventData);
                                if (eventType === "log") {
                                    streamLogs = [
                                        ...streamLogs,
                                        {
                                            level: parsed.level,
                                            message: parsed.message,
                                            icon: parsed.icon,
                                            timestamp:
                                                new Date().toLocaleTimeString(
                                                    "en-US",
                                                    {
                                                        hour12: false,
                                                        hour: "numeric",
                                                        minute: "numeric",
                                                        second: "numeric",
                                                    },
                                                ),
                                        },
                                    ];
                                    // Auto-scroll terminal (handled loosely via CSS flex or similar if needed)
                                } else if (
                                    eventType === "stage" &&
                                    parsed.status === "done"
                                ) {
                                    draft =
                                        typeof parsed.draft === "string"
                                            ? JSON.parse(parsed.draft)
                                            : parsed.draft;
                                    if (parsed.transcript) {
                                        transcript = parsed.transcript;
                                    }
                                }
                            } catch (e) {
                                console.error("Failed to parse SSE data", e);
                            }
                        }
                    }
                }
            }
        } catch (e) {
            console.error(e);
            alert(
                "Draft generation failed. Ensure the Pramana AI sidecar is running with Whisper + Ollama.",
            );
        } finally {
            generating = false;
        }
    }

    async function handleApprove() {
        try {
            await import("$lib/api").then((m) =>
                m.approveDraft(data.caseId, draft),
            );
            approved = true;
            // Also update case caseData status locally for UI consistency
            if (caseData) {
                caseData.status = "query_drafted";
            }
        } catch (e) {
            console.error(e);
        }
    }

    function getBandColor(band: string, status?: string) {
        if (!band) return "var(--n-500)";
        if (band === "GREEN") return "var(--status-green)";
        if (band === "AMBER") return "var(--status-amber)";
        return "var(--status-red)";
    }

    const formatDocName = (str: string) => {
        if (!str) return "Unclassified";
        return str.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
    };
</script>

<div class="flex flex-col gap-5" style="max-width: 56rem; margin: 0 auto;">
    <!-- Header -->
    <div
        class="flex items-center justify-between animate-fade-up"
        style="padding-bottom: 1.25rem; border-bottom: 1px solid var(--border-subtle);"
    >
        <div class="flex items-center gap-4">
            <a
                href="/cases/{data.caseId}"
                aria-label="Back"
                style="padding: 0.5rem; border-radius: var(--radius-md); color: var(--n-500);"
            >
                <svg
                    class="w-5 h-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    ><path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M10 19l-7-7m0 0l7-7m-7 7h18"
                    /></svg
                >
            </a>
            <div>
                <div
                    class="flex items-center gap-2"
                    style="margin-bottom: 0.25rem;"
                >
                    <span
                        style="font-size: 0.65rem; font-weight: 700; color: var(--teal-400); text-transform: uppercase; letter-spacing: 0.15em;"
                        >Query Reply Copilot</span
                    >
                    {#if caseData}
                        <span style="color: var(--n-600);">/</span>
                        <span
                            style="font-size: 0.7rem; font-weight: 600; color: var(--n-400); font-family: 'Space Grotesk', monospace;"
                            >{caseData.case_number}</span
                        >
                    {/if}
                </div>
                <h1
                    style="font-size: 1.5rem; font-weight: 700; color: var(--n-50); letter-spacing: -0.02em;"
                >
                    {loading
                        ? "Loading..."
                        : caseData?.patient || "Unknown Patient"}
                </h1>
            </div>
        </div>
    </div>

    {#if loading}
        <div
            class="flex items-center justify-center"
            style="height: 20rem; background: var(--bg-card); border-radius: var(--radius-xl); border: 1px solid var(--border-subtle);"
        >
            <div
                style="width: 2rem; height: 2rem; border-radius: 50%; border: 3px solid var(--border-subtle); border-top-color: var(--teal-400); animation: spin 0.8s linear infinite;"
            ></div>
        </div>
    {:else}
        <div class="flex gap-5" style="min-height: 500px;">
            <!-- Left: Query + Voice Input -->
            <div
                style="width: 50%; display: flex; flex-direction: column; gap: 1.25rem;"
            >
                <!-- AI Pipeline Badge -->
                <div
                    class="animate-fade-up"
                    style="display: flex; gap: 0.5rem;"
                >
                    {#each [{ label: "Whisper ASR", icon: "🎙️", desc: "Voice → Text", active: isRecording || transcribing || transcript.length > 0 }, { label: "Policy RAG", icon: "📚", desc: "FAISS Search", active: false }, { label: "Pramana AI", icon: "🧠", desc: "Clinical Draft", active: false }] as pillar}
                        <div
                            style="flex: 1; padding: 0.6rem; background: {pillar.active
                                ? 'rgba(45,212,191,0.08)'
                                : 'var(--bg-card)'}; border: 1px solid {pillar.active
                                ? 'rgba(45,212,191,0.3)'
                                : 'var(--border-subtle)'}; border-radius: var(--radius-md); text-align: center; transition: all 0.3s;"
                        >
                            <div
                                style="font-size: 1.1rem; margin-bottom: 0.15rem;"
                            >
                                {pillar.icon}
                            </div>
                            <div
                                style="font-size: 0.55rem; font-weight: 700; color: {pillar.active
                                    ? 'var(--teal-400)'
                                    : 'var(--n-300)'}; text-transform: uppercase; letter-spacing: 0.1em;"
                            >
                                {pillar.label}
                            </div>
                            <div
                                style="font-size: 0.5rem; color: var(--n-600);"
                            >
                                {pillar.desc}
                            </div>
                        </div>
                    {/each}
                </div>

                <!-- Voice Dictation -->
                <div
                    class="animate-fade-up stagger-1"
                    style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-xl); padding: 1.25rem;"
                >
                    <span
                        style="display: block; font-size: 0.65rem; font-weight: 700; color: var(--n-500); text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 0.75rem;"
                    >
                        🎙️ Doctor Voice Dictation <span
                            style="font-weight: 400; color: var(--n-600);"
                            >(Optional)</span
                        >
                    </span>

                    <div class="flex items-center gap-3">
                        <button
                            on:click={toggleRecording}
                            style="width: 3.5rem; height: 3.5rem; border-radius: 50%; display: flex; align-items: center; justify-content: center; transition: all 0.3s;
                                {isRecording
                                ? 'background: rgba(248,113,113,0.15); border: 2px solid rgba(248,113,113,0.5); animation: micPulse 1.5s ease infinite;'
                                : 'background: rgba(45,212,191,0.08); border: 2px solid rgba(45,212,191,0.2);'}"
                        >
                            {#if isRecording}
                                <svg
                                    style="width: 1.5rem; height: 1.5rem; color: var(--status-red);"
                                    fill="currentColor"
                                    viewBox="0 0 24 24"
                                    ><rect
                                        x="6"
                                        y="6"
                                        width="12"
                                        height="12"
                                        rx="2"
                                    /></svg
                                >
                            {:else}
                                <svg
                                    style="width: 1.5rem; height: 1.5rem; color: var(--teal-400);"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2"
                                    ><path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                                    /></svg
                                >
                            {/if}
                        </button>

                        <div style="flex: 1;">
                            {#if isRecording}
                                <div class="flex items-center gap-2">
                                    <div
                                        style="width: 0.5rem; height: 0.5rem; border-radius: 50%; background: var(--status-red); animation: pulse 1s ease infinite;"
                                    ></div>
                                    <span
                                        style="font-size: 0.85rem; font-weight: 700; color: var(--status-red);"
                                        >Recording</span
                                    >
                                    <span
                                        style="font-size: 0.85rem; font-family: 'Space Grotesk', monospace; color: var(--n-300);"
                                        >{formatDuration(
                                            recordingDuration,
                                        )}</span
                                    >
                                </div>
                                <p
                                    style="font-size: 0.7rem; color: var(--n-500); margin-top: 0.2rem;"
                                >
                                    Speak your clinical justification... Click
                                    stop when finished.
                                </p>
                            {:else if transcribing}
                                <div class="flex items-center gap-2">
                                    <div
                                        style="width: 1rem; height: 1rem; border-radius: 50%; border: 2px solid var(--border-subtle); border-top-color: var(--teal-400); animation: spin 0.8s linear infinite;"
                                    ></div>
                                    <span
                                        style="font-size: 0.85rem; font-weight: 600; color: var(--n-200);"
                                        >Transcribing Dictation...</span
                                    >
                                </div>
                                <p
                                    style="font-size: 0.7rem; color: var(--n-500); margin-top: 0.2rem;"
                                >
                                    Running local Whisper ASR instance
                                </p>
                            {:else if transcript}
                                <div
                                    class="flex items-center justify-between"
                                    style="margin-bottom: 0.5rem;"
                                >
                                    <div class="flex items-center gap-2">
                                        <svg
                                            style="width: 0.75rem; height: 0.75rem; color: var(--status-green);"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            stroke="currentColor"
                                            stroke-width="2.5"
                                            ><path
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                                d="M5 13l4 4L19 7"
                                            /></svg
                                        >
                                        <span
                                            style="font-size: 0.85rem; font-weight: 600; color: var(--n-200);"
                                            >Dictation Captured & Editable</span
                                        >
                                    </div>
                                    <button
                                        on:click={() => (transcript = "")}
                                        style="padding: 0.3rem 0.6rem; font-size: 0.65rem; color: var(--n-500); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); transition: all 0.2s; cursor: pointer;"
                                        on:mouseover={(e) =>
                                            ((
                                                e.target as HTMLElement
                                            ).style.background =
                                                "rgba(239,68,68,0.1)")}
                                        on:mouseout={(e) =>
                                            ((
                                                e.target as HTMLElement
                                            ).style.background = "transparent")}
                                        on:focus={(e) =>
                                            ((
                                                e.target as HTMLElement
                                            ).style.background =
                                                "rgba(239,68,68,0.1)")}
                                        on:blur={(e) =>
                                            ((
                                                e.target as HTMLElement
                                            ).style.background = "transparent")}
                                        >Clear</button
                                    >
                                </div>
                                <textarea
                                    bind:value={transcript}
                                    style="width: 100%; padding: 0.75rem; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); color: var(--n-200); font-size: 0.8rem; outline: none; resize: vertical; min-height: 80px;"
                                ></textarea>
                            {:else}
                                <p
                                    style="font-size: 0.85rem; color: var(--n-400);"
                                >
                                    Click the mic to record doctor's voice
                                    dictation
                                </p>
                                <p
                                    style="font-size: 0.7rem; color: var(--n-600); margin-top: 0.15rem;"
                                >
                                    Whisper ASR will transcribe speech so you
                                    can review before drafting.
                                </p>
                            {/if}
                        </div>
                    </div>
                </div>

                <!-- Payer Query Text -->
                <div
                    class="animate-fade-up stagger-2"
                    style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-xl); padding: 1.25rem; flex: 1; display: flex; flex-direction: column;"
                >
                    <label
                        for="payerQuery"
                        style="display: block; font-size: 0.65rem; font-weight: 700; color: var(--n-500); text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 0.75rem;"
                        >Payer Query / Audit Request</label
                    >
                    <textarea
                        id="payerQuery"
                        bind:value={queryText}
                        placeholder="e.g. Justify the medical necessity of emergency PCI with stent placement for this patient. Provide supporting clinical evidence and relevant policy citations."
                        style="flex: 1; width: 100%; padding: 1rem; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); color: var(--n-100); font-size: 0.875rem; outline: none; resize: none; font-family: 'DM Sans', sans-serif; line-height: 1.6; min-height: 100px;"
                    ></textarea>

                    <div
                        class="flex items-center gap-3"
                        style="margin-top: 1rem;"
                    >
                        <button
                            on:click={handleGenerate}
                            disabled={generating ||
                                (!queryText.trim() && !transcript.trim())}
                            style="flex: 1; display: flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 0.75rem; background: linear-gradient(135deg, var(--teal-500), var(--teal-600)); color: white; border-radius: var(--radius-md); font-size: 0.9rem; font-weight: 700; box-shadow: var(--shadow-glow-teal); opacity: {generating ||
                            (!queryText.trim() && !transcript.trim())
                                ? 0.5
                                : 1}; transition: all 0.2s;"
                        >
                            {#if generating}
                                <div
                                    style="width: 1rem; height: 1rem; border-radius: 50%; border: 2px solid rgba(255,255,255,0.3); border-top-color: white; animation: spin 0.8s linear infinite;"
                                ></div>
                                Generating Draft...
                            {:else}
                                <svg
                                    class="w-5 h-5"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2"
                                    ><path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M13 10V3L4 14h7v7l9-11h-7z"
                                    /></svg
                                >
                                Generate AI Draft
                            {/if}
                        </button>
                    </div>
                </div>
            </div>

            <!-- Right: Draft Output -->
            <div
                style="width: 50%; display: flex; flex-direction: column; gap: 1.25rem;"
            >
                {#if !draft && !generating}
                    <div
                        class="animate-fade-up stagger-3"
                        style="flex: 1; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-xl); display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 3rem;"
                    >
                        <svg
                            style="width: 4rem; height: 4rem; color: var(--n-700); margin-bottom: 1rem;"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            stroke-width="1"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                            />
                        </svg>
                        <h3
                            style="font-size: 1rem; font-weight: 700; color: var(--n-400); margin-bottom: 0.25rem;"
                        >
                            No draft yet
                        </h3>
                        <p style="font-size: 0.8rem; color: var(--n-600);">
                            Record doctor dictation or type a payer query, then
                            click "Generate AI Draft".
                        </p>
                    </div>
                {:else if generating}
                    <!-- King Mode Streaming Terminal -->
                    <div
                        class="animate-fade-up"
                        style="flex: 1; background: #0f172a; border: 1px solid rgba(255,255,255,0.1); border-radius: var(--radius-xl); display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255,255,255,0.1);"
                    >
                        <!-- Terminal Header -->
                        <div
                            style="padding: 1rem 1.25rem; background: #1e293b; border-bottom: 1px solid rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: space-between;"
                        >
                            <div class="flex items-center gap-2">
                                <div
                                    style="width: 3px; height: 16px; background: var(--teal-500); border-radius: 2px;"
                                ></div>
                                <span
                                    style="color: #e2e8f0; font-size: 0.8rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;"
                                    >Agentic RAG Pipeline</span
                                >
                            </div>
                            <div class="flex items-center gap-2">
                                <div
                                    style="width: 1rem; height: 1rem; border-radius: 50%; border: 2px solid rgba(20, 184, 166, 0.2); border-top-color: var(--teal-500); animation: spin 1s linear infinite;"
                                ></div>
                                <span
                                    style="font-size: 0.7rem; color: var(--teal-400); font-family: 'Space Grotesk', monospace;"
                                    >STREAM_ACTIVE</span
                                >
                            </div>
                        </div>

                        <!-- Terminal Body -->
                        <div
                            style="flex: 1; padding: 1.5rem; overflow-y: auto; font-family: 'Space Grotesk', monospace; display: flex; flex-direction: column; gap: 0.75rem; background: radial-gradient(circle at center, rgba(30,41,59,0.3) 0%, rgba(15,23,42,1) 100%);"
                        >
                            {#each streamLogs as log}
                                <div
                                    class="animate-fade-up"
                                    style="display: flex; gap: 1rem; font-size: 0.8rem; line-height: 1.5;"
                                >
                                    <span
                                        style="color: #64748b; flex-shrink: 0; user-select: none;"
                                        >[{log.timestamp}]</span
                                    >
                                    <span style="min-width: 1.25rem;"
                                        >{log.icon || "❯"}</span
                                    >
                                    <div style="flex: 1;">
                                        {#if log.level === "info"}
                                            <span
                                                style="color: #94a3b8; font-family: 'JetBrains Mono', monospace;"
                                                >{@html log.message.replace(
                                                    /FAISS|Pramana AI|Semantic Search|LLM|Llama 3\.2|RAG|Match|Dist:/g,
                                                    (match) =>
                                                        `<span style="color: var(--teal-400); font-weight: 700;">${match}</span>`,
                                                )}</span
                                            >
                                        {:else if log.level === "success"}
                                            <span
                                                style="color: #34d399; font-weight: 600;"
                                                >✓ {@html log.message.replace(
                                                    /Score:|Readiness Score/g,
                                                    (match) =>
                                                        `<span style="color: white;">${match}</span>`,
                                                )}</span
                                            >
                                        {:else if log.level === "warning"}
                                            <span
                                                style="color: #f59e0b; font-weight: 600;"
                                                >⚠ {log.message}</span
                                            >
                                        {:else if log.level === "error"}
                                            <span
                                                style="color: #ef4444; font-weight: 600;"
                                                >✖ {log.message}</span
                                            >
                                        {:else}
                                            <span style="color: #e2e8f0;"
                                                >{log.message}</span
                                            >
                                        {/if}
                                    </div>
                                </div>
                            {/each}
                            {#if streamLogs.length > 0}
                                <div
                                    style="display: flex; gap: 1rem; font-size: 0.8rem; margin-top: 0.5rem; opacity: 0.7; animation: pulse 1.5s infinite;"
                                >
                                    <span style="color: #64748b;">[System]</span
                                    >
                                    <span style="color: var(--teal-400);"
                                        >Processing parameters... █</span
                                    >
                                </div>
                            {/if}
                        </div>
                    </div>
                {:else}
                    <!-- Draft Result -->
                    <div
                        class="animate-fade-up"
                        style="flex: 1; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-xl); overflow: auto;"
                    >
                        <div
                            style="padding: 1rem 1.25rem; border-bottom: 1px solid var(--border-subtle); display: flex; align-items: center; justify-content: space-between;"
                        >
                            <div class="flex items-center gap-2">
                                <div
                                    style="width: 0.5rem; height: 0.5rem; border-radius: 50%; background: var(--status-green); animation: pulse 2s ease infinite;"
                                ></div>
                                <span
                                    style="font-size: 0.75rem; font-weight: 700; color: var(--n-200);"
                                    >AI Draft Generated</span
                                >
                            </div>
                        </div>

                        <div style="padding: 1.25rem;">
                            <!-- Transcript if from voice -->
                            {#if transcript}
                                <div
                                    style="margin-bottom: 1.25rem; padding: 0.75rem; background: rgba(45,212,191,0.04); border: 1px solid rgba(45,212,191,0.15); border-radius: var(--radius-md);"
                                >
                                    <h4
                                        style="font-size: 0.6rem; font-weight: 700; color: var(--teal-400); text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 0.35rem;"
                                    >
                                        🎙️ Doctor's Dictation (Transcribed)
                                    </h4>
                                    <p
                                        style="font-size: 0.8rem; color: var(--n-300); line-height: 1.5; font-style: italic;"
                                    >
                                        "{transcript}"
                                    </p>
                                </div>
                            {/if}

                            <!-- Clinical Summary -->
                            <div style="margin-bottom: 1.25rem;">
                                <h4
                                    style="font-size: 0.6rem; font-weight: 700; color: var(--teal-400); text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 0.5rem;"
                                >
                                    Clinical Summary
                                </h4>
                                {#if !approved}
                                    <textarea
                                        bind:value={draft.clinicalSummary}
                                        style="width: 100%; padding: 0.75rem; background: rgba(0,0,0,0.2); border: 1px dashed var(--border-subtle); border-radius: var(--radius-md); color: var(--n-100); font-size: 0.85rem; line-height: 1.6; outline: none; resize: vertical; min-height: 120px; transition: all 0.2s;"
                                        on:focus={(e) =>
                                            ((
                                                e.target as HTMLElement
                                            ).style.borderColor =
                                                "var(--teal-500)")}
                                        on:blur={(e) =>
                                            ((
                                                e.target as HTMLElement
                                            ).style.borderColor =
                                                "var(--border-subtle)")}
                                    ></textarea>
                                {:else}
                                    <p
                                        style="font-size: 0.85rem; color: var(--n-200); line-height: 1.6;"
                                    >
                                        {draft?.clinicalSummary ||
                                            draft?.clinical_summary ||
                                            JSON.stringify(draft).substring(
                                                0,
                                                300,
                                            )}
                                    </p>
                                {/if}
                            </div>

                            <!-- Justification -->
                            <div style="margin-bottom: 1.25rem;">
                                <h4
                                    style="font-size: 0.6rem; font-weight: 700; color: var(--teal-400); text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 0.5rem;"
                                >
                                    Medical Necessity Justification
                                </h4>
                                {#if !approved}
                                    <textarea
                                        bind:value={draft.justification}
                                        style="width: 100%; padding: 0.75rem; background: rgba(0,0,0,0.2); border: 1px dashed var(--border-subtle); border-radius: var(--radius-md); color: var(--n-100); font-size: 0.85rem; line-height: 1.6; outline: none; resize: vertical; min-height: 120px; transition: all 0.2s;"
                                        on:focus={(e) =>
                                            ((
                                                e.target as HTMLElement
                                            ).style.borderColor =
                                                "var(--teal-500)")}
                                        on:blur={(e) =>
                                            ((
                                                e.target as HTMLElement
                                            ).style.borderColor =
                                                "var(--border-subtle)")}
                                    ></textarea>
                                {:else}
                                    <p
                                        style="font-size: 0.85rem; color: var(--n-200); line-height: 1.6;"
                                    >
                                        {draft?.justification ||
                                            draft?.medical_justification ||
                                            ""}
                                    </p>
                                {/if}
                            </div>

                            <!-- Attachments -->
                            {#if draft?.attachments?.length || draft?.supporting_documents?.length}
                                <div style="margin-bottom: 1.25rem;">
                                    <h4
                                        style="font-size: 0.6rem; font-weight: 700; color: var(--teal-400); text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 0.5rem;"
                                    >
                                        Supporting Documents
                                    </h4>
                                    <div class="flex flex-wrap gap-2">
                                        {#each draft.attachments || draft.supporting_documents || [] as att}
                                            <span
                                                style="display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.3rem 0.6rem; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); font-size: 0.7rem; font-weight: 600; color: var(--n-300);"
                                            >
                                                📄 {formatDocName(att)}
                                            </span>
                                        {/each}
                                    </div>
                                </div>
                            {/if}

                            <!-- Next Steps -->
                            {#if draft?.nextSteps || draft?.next_steps}
                                <div
                                    style="padding: 0.75rem; background: rgba(251,191,36,0.04); border: 1px solid rgba(251,191,36,0.1); border-radius: var(--radius-md);"
                                >
                                    <h4
                                        style="font-size: 0.6rem; font-weight: 700; color: var(--amber-400); text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 0.35rem;"
                                    >
                                        Next Steps
                                    </h4>
                                    {#if !approved}
                                        <input
                                            type="text"
                                            bind:value={draft.nextSteps}
                                            style="width: 100%; padding: 0.5rem; background: transparent; border: 1px dashed var(--border-subtle); border-radius: var(--radius-sm); color: var(--n-200); font-size: 0.8rem; line-height: 1.5; outline: none; transition: all 0.2s;"
                                            on:focus={(e) =>
                                                ((
                                                    e.target as HTMLElement
                                                ).style.borderColor =
                                                    "var(--amber-500)")}
                                            on:blur={(e) =>
                                                ((
                                                    e.target as HTMLElement
                                                ).style.borderColor =
                                                    "var(--border-subtle)")}
                                        />
                                    {:else}
                                        <p
                                            style="font-size: 0.8rem; color: var(--n-300); line-height: 1.5;"
                                        >
                                            {draft.nextSteps ||
                                                draft.next_steps}
                                        </p>
                                    {/if}
                                </div>
                            {/if}
                        </div>

                        <!-- Actions -->
                        <div
                            style="padding: 1rem 1.25rem; border-top: 1px solid var(--border-subtle); display: flex; gap: 0.75rem;"
                        >
                            {#if approved}
                                <div
                                    style="flex: 1; display: flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 0.75rem; background: rgba(52,211,153,0.08); border: 1px solid rgba(52,211,153,0.2); border-radius: var(--radius-md); color: var(--status-green); font-size: 0.85rem; font-weight: 700;"
                                >
                                    <svg
                                        class="w-5 h-5"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        stroke="currentColor"
                                        stroke-width="2.5"
                                        ><path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            d="M5 13l4 4L19 7"
                                        /></svg
                                    >
                                    Draft Approved & Locked
                                </div>
                            {:else}
                                <button
                                    on:click={handleGenerate}
                                    style="padding: 0.65rem 1rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); font-size: 0.8rem; font-weight: 600; color: var(--n-400);"
                                >
                                    ↻ Regenerate
                                </button>
                                <button
                                    on:click={handleApprove}
                                    style="flex: 1; display: flex; align-items: center; justify-content: center; gap: 0.5rem; padding: 0.65rem; background: linear-gradient(135deg, var(--status-green), #059669); color: white; border-radius: var(--radius-md); font-size: 0.85rem; font-weight: 700;"
                                >
                                    <svg
                                        class="w-4 h-4"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        stroke="currentColor"
                                        stroke-width="2.5"
                                        ><path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            d="M5 13l4 4L19 7"
                                        /></svg
                                    >
                                    Approve & Lock Draft
                                </button>
                            {/if}
                        </div>
                    </div>
                {/if}
            </div>
        </div>
    {/if}
</div>

<style>
    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }
    @keyframes pulse {
        0%,
        100% {
            opacity: 1;
        }
        50% {
            opacity: 0.4;
        }
    }
    @keyframes micPulse {
        0%,
        100% {
            box-shadow: 0 0 0 0 rgba(248, 113, 113, 0.4);
        }
        50% {
            box-shadow: 0 0 0 12px rgba(248, 113, 113, 0);
        }
    }
</style>
