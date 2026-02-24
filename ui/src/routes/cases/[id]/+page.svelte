<script lang="ts">
    import { onMount } from "svelte";
    import type { PageData } from "./$types";
    import { uploadFile, generatePack, getAnalysisResults } from "$lib/api";

    export let data: PageData;

    let caseData: any = null;
    let documents: any[] = [];
    let checklist: any[] = [];
    let riskFlags: any[] = [];
    let loading = true;
    let analyzing = false;
    let selectedDoc: string | null = null;
    let zoomLevel = 1.0;
    let isDragOver = false;
    let uploading = false;
    let uploadProgress = "";
    let fileInput: HTMLInputElement;
    let generatingPack = false;
    let analysisResults: any = null;
    let lastAnalyzedAt: string | null = null;
    let lastUploadedAt: string | null = null;
    let hasNewDocsSinceAnalysis = false;
    let approvedDraft: any = null;
    let isSendingPayer = false;

    // Upload Tracking State for Checklist
    let newlyUploadedItems: Set<string> = new Set();
    let uploadingForItem: string | null = null;

    // Modals
    let confirmingSendToPayer = false;

    const formatDocName = (str: string) => {
        if (!str) return "Unclassified";
        return str.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
    };
    let viewingPolicy: string | null = null;

    // Derived flags
    $: isAnalyzed = caseData?.status !== "new" && !!caseData?.readiness_score;

    // Pipeline overlay state
    let pipelineActive = false;
    let pipelineStages: Record<string, "pending" | "active" | "done"> = {
        classify: "pending",
        quality: "pending",
        score: "pending",
    };
    let pipelineResults: Array<{
        type: string;
        icon: string;
        message: string;
        elapsed?: number;
        level?: string;
    }> = [];
    let finalScore: number | null = null;
    let finalBand: string | null = null;
    let showScoreReveal = false;

    function getDocUrl(path: string) {
        if (!path) return "";
        const parts = path.split(/[\\/]/);
        const dataIdx = parts.lastIndexOf("data");
        if (dataIdx !== -1) {
            const relativePath = parts.slice(dataIdx + 1).join("/");
            return `http://localhost:8000/docs/${relativePath}`;
        }
        return `http://localhost:8000/docs/${parts.pop()}`;
    }

    function isImage(mimeType: string) {
        return mimeType?.startsWith("image/");
    }

    function isPdf(mimeType: string) {
        return mimeType === "application/pdf";
    }

    async function loadCase() {
        loading = true;
        try {
            const res = await fetch(`/api/cases/${data.caseId}`);
            if (!res.ok) throw new Error("Case fetch failed");
            const json = await res.json();

            caseData = {
                ...json,
                patient: json.patient_alias || "Unknown Patient",
                score: json.readiness_score || 0,
                band: json.readiness_band || null,
            };

            const resultsRes = await fetch(
                `/api/analysis/${data.caseId}/results`,
            );
            if (resultsRes.ok) {
                const results = await resultsRes.json();
                documents = results.files || [];
                checklist = results.missing_items || [];
                riskFlags = results.quality_issues || [];
                analysisResults = results;
                lastAnalyzedAt = results.created_at || null;
                if (documents.length > 0 && !selectedDoc) {
                    selectedDoc = documents[0].id;
                }
            }
            // Check if new docs uploaded since last analysis
            let lastAnalysisTime = lastAnalyzedAt
                ? new Date(lastAnalyzedAt).getTime()
                : 0;
            let lastFileUpdate = documents.reduce((latest: number, d: any) => {
                const uploadTime = new Date(d.created_at || 0).getTime();
                return Math.max(latest, uploadTime);
            }, 0);
            // Check if there are new files since the last analysis
            hasNewDocsSinceAnalysis = lastFileUpdate > lastAnalysisTime;

            // Load approved draft if available
            try {
                const draftRes = await fetch(
                    `/api/cases/${data.caseId}/query/latest`,
                );
                if (draftRes.ok) {
                    const saved = await draftRes.json();
                    if (saved.draft && saved.status === "approved") {
                        approvedDraft =
                            typeof saved.draft === "string"
                                ? JSON.parse(saved.draft)
                                : saved.draft;
                    }
                }
            } catch (e) {
                console.error("Failed to load approved draft", e);
            }
        } catch (e) {
            console.error("Failed to load case:", e);
        } finally {
            loading = false;
        }
    }

    onMount(() => {
        loadCase();
    });

    async function runAnalysis() {
        if (analyzing) return;
        analyzing = true;
        pipelineActive = true;
        pipelineStages = {
            classify: "pending",
            quality: "pending",
            score: "pending",
        };
        pipelineResults = [];
        finalScore = null;
        finalBand = null;
        showScoreReveal = false;

        try {
            const response = await fetch(
                `/api/analysis/${data.caseId}/analyze-stream`,
                { method: "POST" },
            );
            if (!response.ok) throw new Error("Analysis failed");
            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            while (reader) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() || "";

                let eventType = "";
                for (const line of lines) {
                    if (line.startsWith("event: ")) {
                        eventType = line.slice(7).trim();
                    } else if (line.startsWith("data: ") && eventType) {
                        try {
                            const payload = JSON.parse(line.slice(6));
                            handleSSE(eventType, payload);
                        } catch {}
                        eventType = "";
                    }
                }
            }
            await loadCase();
        } catch (e) {
            console.error("Stream error, falling back:", e);
            // Fallback: try the non-streaming endpoint
            try {
                await fetch(`/api/analysis/${data.caseId}/analyze`, {
                    method: "POST",
                });
            } catch {}
            await loadCase();
            // If we got a score from loadCase, show it
            if (caseData?.score && caseData?.band) {
                finalScore = caseData.score;
                finalBand = caseData.band;
                pipelineStages = {
                    classify: "done",
                    quality: "done",
                    score: "done",
                };
                showScoreReveal = true;
                setTimeout(() => {
                    pipelineActive = false;
                }, 3000);
            } else {
                pipelineActive = false;
            }
        } finally {
            analyzing = false;
        }
    }

    function handleSSE(event: string, data: any) {
        if (event === "stage") {
            pipelineStages[data.stage] = data.status;
            pipelineStages = pipelineStages; // trigger reactivity
            if (data.status === "active") {
                pipelineResults = [
                    ...pipelineResults,
                    { type: "stage", icon: data.icon, message: data.message },
                ];
            }
        } else if (event === "log") {
            pipelineResults = [
                ...pipelineResults,
                {
                    type: "log",
                    icon: data.icon || "❯",
                    message: data.message,
                    level: data.level || "info",
                },
            ];
        } else if (event === "classify_result" || event === "quality_result") {
            pipelineResults = [
                ...pipelineResults,
                {
                    type: event,
                    icon: data.icon,
                    message: data.message,
                    elapsed: data.elapsed,
                },
            ];
        } else if (event === "complete") {
            finalScore = data.score;
            finalBand = data.band;
            // Trigger score reveal animation
            setTimeout(() => {
                showScoreReveal = true;
            }, 400);
            // Auto-close pipeline after the reveal
            setTimeout(() => {
                pipelineActive = false;
            }, 4000);
        }
    }

    function getBandColor(band: string, status?: string) {
        if (!band) return "var(--n-500)";
        if (band === "GREEN") return "var(--status-green)";
        if (band === "AMBER") return "var(--status-amber)";
        return "var(--status-red)";
    }

    function getBandGlow(band: string) {
        if (band === "GREEN") return "var(--shadow-glow-teal)";
        if (band === "AMBER") return "var(--shadow-glow-amber)";
        return "var(--shadow-glow-red)";
    }

    async function handleDrop(e: DragEvent) {
        e.preventDefault();
        isDragOver = false;
        if (!e.dataTransfer?.files?.length || !caseData) return;
        uploading = true;
        const files = e.dataTransfer.files;
        try {
            for (let i = 0; i < files.length; i++) {
                uploadProgress = `Uploading ${i + 1}/${files.length}: ${files[i].name}`;
                await uploadFile(caseData.id, files[i]);
            }
            if (uploadingForItem) {
                newlyUploadedItems = new Set([
                    ...newlyUploadedItems,
                    uploadingForItem,
                ]);
                uploadingForItem = null;
            }
            hasNewDocsSinceAnalysis = true;
            await loadCase();
        } catch (e) {
            console.error(e);
            alert("Upload failed");
        } finally {
            uploadProgress = "";
            uploading = false;
        }
    }

    async function handleDeleteFile(fileId: string) {
        if (!confirm("Are you sure you want to delete this file?")) return;
        try {
            const res = await fetch(
                `/api/cases/${data.caseId}/files/${fileId}`,
                {
                    method: "DELETE",
                },
            );
            if (res.ok) {
                // If a file is deleted, it changes the case state, warranting a re-analysis
                hasNewDocsSinceAnalysis = true;
                await loadCase();
            } else {
                alert("Failed to delete file.");
            }
        } catch (e) {
            console.error(e);
            alert("Error deleting file.");
        }
    }

    let isCopied = false;

    function handleDragOver(e: DragEvent) {
        e.preventDefault();
        isDragOver = true;
    }
    function handleDragLeave() {
        isDragOver = false;
    }

    async function handleBrowseFiles(event: Event) {
        const input = event.target as HTMLInputElement;
        if (!input.files?.length || !caseData) return;
        uploading = true;
        const files = input.files;
        for (let i = 0; i < files.length; i++) {
            uploadProgress = `Uploading ${i + 1}/${files.length}: ${files[i].name}`;
            try {
                await uploadFile(caseData.id, files[i]);
            } catch (err) {
                console.error(err);
            }
        }
        uploadProgress = "";
        uploading = false;
        if (uploadingForItem) {
            newlyUploadedItems = new Set([
                ...newlyUploadedItems,
                uploadingForItem,
            ]);
            uploadingForItem = null;
        }
        hasNewDocsSinceAnalysis = true;
        input.value = "";
        await loadCase();
        // Automatically select the newest document
        if (caseData && caseData.files && caseData.files.length > 0) {
            selectedDoc = caseData.files[caseData.files.length - 1].id;
        }
    }

    async function handleGeneratePack() {
        if (generatingPack || !caseData) return;
        generatingPack = true;
        try {
            const result = await generatePack(data.caseId);
            // Force system download using Blob to prevent browser from hijacking the tab
            const pdfResponse = await fetch(
                `http://localhost:8000${result.path}`,
            );
            if (!pdfResponse.ok) throw new Error("Failed to fetch PDF blob");

            const blob = await pdfResponse.blob();
            const blobUrl = URL.createObjectURL(blob);

            const link = document.createElement("a");
            link.href = blobUrl;
            link.download = `evidence_pack_${caseData.case_number || "case"}.pdf`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(blobUrl);
            await loadCase();
        } catch (e) {
            console.error("Pack generation failed:", e);
            alert(
                "Evidence pack generation failed. Please ensure the case has been analyzed.",
            );
        } finally {
            generatingPack = false;
        }
    }

    function handleShareLink() {
        const url = `${window.location.origin}/cases/${data.caseId}/patient`;
        navigator.clipboard.writeText(url);
        isCopied = true;
        setTimeout(() => (isCopied = false), 2000);
    }

    async function confirmPayerSubmission() {
        confirmingSendToPayer = false;
        isSendingPayer = true;
        try {
            const res = await fetch(`/api/cases/${data.caseId}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ status: "closed" }),
            });
            if (!res.ok) throw new Error("Failed to send to payer");
            await loadCase();
        } catch (e) {
            console.error(e);
            alert("Error sending to payer.");
        } finally {
            isSendingPayer = false;
        }
    }
</script>

<div class="flex flex-col h-full gap-5">
    <!-- Header -->
    <div
        class="flex items-center justify-between animate-fade-up"
        style="padding-bottom: 1.25rem; border-bottom: 1px solid var(--border-subtle);"
    >
        <div class="flex items-center gap-4">
            <a
                href="/"
                aria-label="Back"
                style="padding: 0.5rem; border-radius: var(--radius-md); color: var(--n-500); transition: all 0.2s;"
            >
                <svg
                    class="w-5 h-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M10 19l-7-7m0 0l7-7m-7 7h18"
                    />
                </svg>
            </a>
            <div>
                <div
                    class="flex items-center gap-2"
                    style="margin-bottom: 0.25rem;"
                >
                    <span
                        style="font-size: 0.65rem; font-weight: 700; color: var(--teal-400); text-transform: uppercase; letter-spacing: 0.15em; white-space: nowrap;"
                        >Case Workbench</span
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
                        ? "Loading Case..."
                        : caseData?.patient || "Unknown Patient"}
                </h1>
            </div>
        </div>

        <div class="flex items-center gap-3">
            <button
                on:click={runAnalysis}
                disabled={analyzing || loading}
                style="display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem; background: {hasNewDocsSinceAnalysis
                    ? 'linear-gradient(135deg, rgba(251,191,36,0.15), rgba(251,191,36,0.05))'
                    : caseData?.score
                      ? 'rgba(45,212,191,0.08)'
                      : 'var(--bg-card)'}; border: 1px solid {hasNewDocsSinceAnalysis
                    ? 'rgba(251,191,36,0.3)'
                    : caseData?.score
                      ? 'rgba(45,212,191,0.2)'
                      : 'var(--border-subtle)'}; border-radius: var(--radius-md); font-size: 0.85rem; font-weight: 600; color: var(--n-200); transition: all 0.2s; opacity: {analyzing ||
                loading
                    ? 0.5
                    : 1};"
            >
                {#if analyzing}
                    <div
                        style="width: 1rem; height: 1rem; border-radius: 50%; border: 2px solid var(--border-subtle); border-top-color: var(--teal-400); animation: spin 0.8s linear infinite;"
                    ></div>
                    Analyzing...
                {:else if isAnalyzed && hasNewDocsSinceAnalysis}
                    <svg
                        class="w-4 h-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                        />
                    </svg>
                    <span style="color: var(--status-amber);"
                        >⚡ Re-analyze</span
                    >
                {:else if caseData?.score}
                    <svg
                        class="w-4 h-4"
                        style="color: var(--teal-400);"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                    </svg>
                    <span style="color: var(--teal-400);"
                        >✓ Analyzed ({caseData.score}/100)</span
                    >
                {:else}
                    <svg
                        class="w-4 h-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                    </svg>
                    Analyze Case
                {/if}
            </button>
            {#if caseData?.score}
                <button
                    on:click={handleGeneratePack}
                    disabled={generatingPack}
                    style="display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem; background: linear-gradient(135deg, rgba(45,212,191,0.12), rgba(45,212,191,0.04)); border: 1px solid rgba(45,212,191,0.2); border-radius: var(--radius-md); font-size: 0.85rem; font-weight: 600; color: var(--teal-400); transition: all 0.2s; opacity: {generatingPack
                        ? 0.5
                        : 1};"
                >
                    {#if generatingPack}
                        <div
                            style="width: 1rem; height: 1rem; border-radius: 50%; border: 2px solid var(--border-subtle); border-top-color: var(--teal-400); animation: spin 0.8s linear infinite;"
                        ></div>
                        Generating...
                    {:else}
                        <svg
                            class="w-4 h-4"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            stroke-width="2"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                            />
                        </svg>
                        Evidence Pack
                    {/if}
                </button>
            {/if}
            <a
                href="/cases/{data.caseId}/query"
                style="display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem; background: linear-gradient(135deg, var(--teal-500), var(--teal-600)); border-radius: var(--radius-md); font-size: 0.85rem; font-weight: 600; color: white; box-shadow: var(--shadow-glow-teal); text-decoration: none; transition: all 0.2s;"
            >
                <svg
                    class="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                    />
                </svg>
                Draft Query Reply
            </a>
            <button
                on:click={handleShareLink}
                style="display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem; background: rgba(148,163,184,0.08); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); font-size: 0.85rem; font-weight: 600; color: var(--n-200); transition: all 0.2s;"
                title="Share patient link"
            >
                <svg
                    class="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d={isCopied
                            ? "M5 13l4 4L19 7"
                            : "M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"}
                    />
                </svg>
                {isCopied ? "Copied!" : "Share Link"}
            </button>

            {#if ["pack_generated", "query_drafted"].includes(caseData?.status)}
                <button
                    on:click={() => {
                        confirmingSendToPayer = true;
                    }}
                    disabled={isSendingPayer}
                    style="display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem; background: #6366f1; border-radius: var(--radius-md); font-size: 0.85rem; font-weight: 600; color: white; box-shadow: 0 4px 12px rgba(99,102,241,0.3); transition: all 0.2s; border: none; cursor: pointer;"
                >
                    <svg
                        class="w-4 h-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <path
                            stroke-linecap="round"
                            d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                        />
                    </svg>
                    {isSendingPayer ? "Sending..." : "Send to Payer"}
                </button>
            {:else if caseData?.status === "closed"}
                <div
                    style="display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem; background: rgba(59,130,246,0.1); border: 1px solid rgba(59,130,246,0.2); border-radius: var(--radius-md); font-size: 0.85rem; font-weight: 600; color: #3b82f6;"
                >
                    <svg
                        class="w-4 h-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M5 13l4 4L19 7"
                        />
                    </svg>
                    Sent to Payer
                </div>
            {/if}
        </div>
    </div>

    <!-- Main Content -->
    {#if loading}
        <div
            class="flex-1 flex flex-col items-center justify-center gap-4"
            style="background: var(--bg-card); border-radius: var(--radius-xl); border: 1px solid var(--border-subtle);"
        >
            <div
                style="width: 3rem; height: 3rem; border-radius: 50%; border: 3px solid var(--border-subtle); border-top-color: var(--teal-400); animation: spin 0.8s linear infinite;"
            ></div>
            <p style="color: var(--n-500); font-weight: 500;">
                Syncing with medical sidecar...
            </p>
        </div>
    {:else}
        <div class="flex h-0 flex-1 gap-5">
            <!-- Left Panel: Score + Documents -->
            <div
                style="width: 20rem; display: flex; flex-direction: column; gap: 1.25rem; overflow: auto; padding-right: 0.25rem;"
            >
                <!-- Score Card -->
                <div
                    class="animate-fade-up"
                    style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-xl); padding: 1.5rem; position: relative; overflow: hidden;"
                >
                    <!-- Glow -->
                    <div
                        style="position: absolute; top: -3rem; right: -3rem; width: 8rem; height: 8rem; border-radius: 50%; background: {getBandColor(
                            caseData?.band,
                        )}; opacity: 0.04; filter: blur(40px);"
                    ></div>

                    <div style="position: relative; z-index: 1;">
                        <div
                            class="flex items-center justify-between"
                            style="margin-bottom: 1.5rem;"
                        >
                            <span
                                style="font-size: 0.6rem; font-weight: 700; color: var(--n-500); text-transform: uppercase; letter-spacing: 0.15em;"
                                >Readiness Audit</span
                            >
                            <div
                                style="padding: 0.2rem 0.75rem; border-radius: var(--radius-full); font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: white; background: {getBandColor(
                                    caseData?.band,
                                )}; box-shadow: {getBandGlow(caseData?.band)};"
                            >
                                {caseData?.band || "UNSCORED"}
                            </div>
                        </div>

                        <!-- Score Circle -->
                        <div
                            class="flex items-center justify-center relative"
                            style="margin-bottom: 1.5rem;"
                        >
                            <svg
                                style="width: 10rem; height: 10rem; transform: rotate(-90deg);"
                            >
                                <circle
                                    cx="80"
                                    cy="80"
                                    r="72"
                                    stroke="var(--bg-surface)"
                                    stroke-width="10"
                                    fill="transparent"
                                />
                                <circle
                                    cx="80"
                                    cy="80"
                                    r="72"
                                    stroke={getBandColor(caseData.band)}
                                    stroke-width="10"
                                    fill="transparent"
                                    stroke-dasharray="452.4"
                                    stroke-dashoffset={452.4 -
                                        (452.4 * (caseData.score || 0)) / 100}
                                    stroke-linecap="round"
                                    style="transition: stroke-dashoffset 1.5s cubic-bezier(0.34, 1.56, 0.64, 1); filter: drop-shadow(0 0 6px {getBandColor(
                                        caseData.band,
                                    )});"
                                />
                            </svg>
                            <div class="absolute flex flex-col items-center">
                                <span
                                    style="font-size: 3rem; font-weight: 800; color: var(--n-50); letter-spacing: -0.04em; line-height: 1; font-family: 'Space Grotesk', sans-serif;"
                                    >{caseData.score}</span
                                >
                                <span
                                    style="font-size: 0.6rem; color: var(--n-500); font-weight: 700; text-transform: uppercase; letter-spacing: 0.15em; margin-top: 0.25rem;"
                                    >Percent</span
                                >
                            </div>
                        </div>

                        <div
                            style="padding: 0.75rem; background: var(--bg-surface); border-radius: var(--radius-lg); border: 1px solid var(--border-subtle);"
                        >
                            <p
                                style="font-size: 0.7rem; color: var(--n-400); font-weight: 500; text-align: center; font-style: italic;"
                            >
                                {caseData.band === "GREEN"
                                    ? "Medical evidence meets clinical policy thresholds. Ready for pack generation."
                                    : "Clinical gaps or quality issues detected. Review the audit flags below."}
                            </p>
                        </div>
                    </div>
                </div>

                <!-- Remediation Checklist (shown when score exists and items are missing) -->
                {#if caseData?.score && (checklist.length > 0 || riskFlags.length > 0)}
                    <div
                        class="animate-fade-up stagger-1"
                        style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-xl); padding: 1rem; position: relative; overflow: hidden;"
                    >
                        <div
                            style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;"
                        >
                            <span
                                style="font-size: 0.6rem; font-weight: 700; color: var(--n-500); text-transform: uppercase; letter-spacing: 0.15em;"
                                >📋 Improve Score</span
                            >
                            <span
                                style="font-size: 0.6rem; color: var(--n-500);"
                                >+{checklist.reduce(
                                    (sum, c) => sum + (c.impact || 0),
                                    0,
                                )} pts possible</span
                            >
                        </div>
                        {#each checklist as item, i}
                            <div
                                style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0; border-bottom: 1px solid rgba(148,163,184,0.06);"
                            >
                                <span
                                    style="font-size: 0.7rem; color: var(--status-red);"
                                    >✕</span
                                >
                                <div style="flex: 1;">
                                    <div
                                        style="font-size: 0.75rem; color: var(--n-200); font-weight: 500;"
                                    >
                                        {formatDocName(item.item)}
                                    </div>
                                    <div
                                        style="font-size: 0.6rem; color: var(--n-500);"
                                    >
                                        Owner: {item.owner || "TPA"} · +{item.impact ||
                                            0} pts
                                    </div>
                                </div>
                                <button
                                    on:click={() => {
                                        uploadingForItem = item.item;
                                        fileInput?.click();
                                    }}
                                    disabled={newlyUploadedItems.has(item.item)}
                                    style="padding: 0.25rem 0.5rem; font-size: 0.6rem; background: {newlyUploadedItems.has(
                                        item.item,
                                    )
                                        ? 'rgba(52,211,153,0.1)'
                                        : 'rgba(45,212,191,0.1)'}; color: {newlyUploadedItems.has(
                                        item.item,
                                    )
                                        ? 'var(--status-green)'
                                        : 'var(--teal-400)'}; border: 1px solid {newlyUploadedItems.has(
                                        item.item,
                                    )
                                        ? 'rgba(52,211,153,0.2)'
                                        : 'rgba(45,212,191,0.2)'}; border-radius: var(--radius-md); font-weight: 600; cursor: {newlyUploadedItems.has(
                                        item.item,
                                    )
                                        ? 'default'
                                        : 'pointer'}; transition: all 0.2s;"
                                    >{newlyUploadedItems.has(item.item)
                                        ? "Uploaded ✓"
                                        : "Upload ↑"}</button
                                >
                            </div>
                        {/each}
                        {#each riskFlags as flag}
                            <div
                                style="display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0; border-bottom: 1px solid rgba(148,163,184,0.06);"
                            >
                                <span
                                    style="font-size: 0.7rem; color: var(--status-amber);"
                                    >⚠</span
                                >
                                <div style="flex: 1;">
                                    <div
                                        style="font-size: 0.75rem; color: var(--n-200); font-weight: 500;"
                                    >
                                        {formatDocName(flag.filename) ||
                                            "Document"}
                                    </div>
                                    <div
                                        style="font-size: 0.6rem; color: var(--n-500);"
                                    >
                                        {flag.message ||
                                            flag.flag ||
                                            "Quality issue detected"}
                                    </div>
                                </div>
                                <button
                                    on:click={() => {
                                        uploadingForItem = flag.filename;
                                        fileInput?.click();
                                    }}
                                    disabled={newlyUploadedItems.has(
                                        flag.filename,
                                    )}
                                    style="padding: 0.25rem 0.5rem; font-size: 0.6rem; background: {newlyUploadedItems.has(
                                        flag.filename,
                                    )
                                        ? 'rgba(52,211,153,0.1)'
                                        : 'rgba(45,212,191,0.1)'}; color: {newlyUploadedItems.has(
                                        flag.filename,
                                    )
                                        ? 'var(--status-green)'
                                        : 'var(--teal-400)'}; border: 1px solid {newlyUploadedItems.has(
                                        flag.filename,
                                    )
                                        ? 'rgba(52,211,153,0.2)'
                                        : 'rgba(45,212,191,0.2)'}; border-radius: var(--radius-md); font-weight: 600; cursor: {newlyUploadedItems.has(
                                        flag.filename,
                                    )
                                        ? 'default'
                                        : 'pointer'}; transition: all 0.2s;"
                                    >{newlyUploadedItems.has(flag.filename)
                                        ? "Uploaded ✓"
                                        : "Upload ↑"}</button
                                >
                            </div>
                        {/each}
                        {#if checklist.length > 0}
                            <div
                                style="margin-top: 0.75rem; padding: 0.5rem; background: rgba(45,212,191,0.05); border-radius: var(--radius-md); text-align: center;"
                            >
                                <span
                                    style="font-size: 0.65rem; color: var(--n-400);"
                                >
                                    Projected score after fixes: <strong
                                        style="color: var(--teal-400);"
                                        >{Math.min(
                                            100,
                                            caseData.score +
                                                checklist.reduce(
                                                    (sum, c) =>
                                                        sum + (c.impact || 0),
                                                    0,
                                                ),
                                        )}/100</strong
                                    >
                                </span>
                            </div>
                        {/if}
                    </div>
                {/if}

                <!-- Drop Zone for Additional Files -->
                <div
                    class="animate-fade-up stagger-1"
                    on:drop={handleDrop}
                    on:dragover={handleDragOver}
                    on:dragleave={handleDragLeave}
                    role="region"
                    aria-label="Drop files here"
                    style="border: 2px dashed {isDragOver
                        ? 'var(--teal-400)'
                        : 'var(--border-subtle)'}; border-radius: var(--radius-lg); padding: 1rem; text-align: center; transition: all 0.3s; background: {isDragOver
                        ? 'rgba(45,212,191,0.05)'
                        : 'transparent'}; cursor: pointer;"
                >
                    {#if uploading}
                        <p
                            style="font-size: 0.75rem; color: var(--teal-400); font-weight: 600;"
                        >
                            {uploadProgress}
                        </p>
                    {:else}
                        <p
                            style="font-size: 0.7rem; color: var(--n-500); font-weight: 500; margin-bottom: 0.4rem;"
                        >
                            <span style="color: var(--teal-400);">＋</span> Drop
                            files here
                        </p>
                        <input
                            type="file"
                            multiple
                            bind:this={fileInput}
                            on:change={handleBrowseFiles}
                            style="display: none;"
                        />
                        <button
                            on:click={() => fileInput?.click()}
                            style="padding: 0.3rem 0.75rem; font-size: 0.65rem; background: rgba(45,212,191,0.1); color: var(--teal-400); border: 1px solid rgba(45,212,191,0.2); border-radius: var(--radius-md); font-weight: 600; cursor: pointer;"
                        >
                            Browse Files
                        </button>
                    {/if}
                </div>

                <!-- Document List -->
                <div
                    class="animate-fade-up stagger-2"
                    style="flex: 1; background: var(--bg-card); border-radius: var(--radius-xl); border: 1px solid var(--border-subtle); display: flex; flex-direction: column; overflow: hidden;"
                >
                    <div
                        style="padding: 0.75rem 1rem; border-bottom: 1px solid var(--border-subtle);"
                    >
                        <h3
                            style="font-weight: 700; color: var(--n-200); font-size: 0.85rem;"
                        >
                            Medical Evidence
                        </h3>
                    </div>
                    <div style="overflow: auto;">
                        {#each documents as cmd}
                            <div class="flex items-center justify-between">
                                <button
                                    on:click={() => (selectedDoc = cmd.id)}
                                    class="w-full"
                                    style="padding: 0.75rem 1rem; display: flex; align-items: flex-start; gap: 0.75rem; border-bottom: 1px solid rgba(148,163,184,0.06); transition: all 0.2s; text-align: left;
                                        {selectedDoc === cmd.id
                                        ? 'background: rgba(45,212,191,0.06); border-right: 3px solid var(--teal-400);'
                                        : ''}"
                                >
                                    <div
                                        style="width: 2.25rem; height: 2.25rem; border-radius: var(--radius-md); background: var(--bg-surface); display: flex; align-items: center; justify-content: center; flex-shrink: 0;"
                                    >
                                        {#if isImage(cmd.mime_type)}
                                            <svg
                                                style="width: 1.1rem; height: 1.1rem; color: var(--amber-400);"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke="currentColor"
                                                stroke-width="2"
                                            >
                                                <path
                                                    stroke-linecap="round"
                                                    stroke-linejoin="round"
                                                    d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                                                />
                                            </svg>
                                        {:else}
                                            <svg
                                                style="width: 1.1rem; height: 1.1rem; color: var(--n-500);"
                                                fill="none"
                                                viewBox="0 0 24 24"
                                                stroke="currentColor"
                                                stroke-width="2"
                                            >
                                                <path
                                                    stroke-linecap="round"
                                                    stroke-linejoin="round"
                                                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                                                />
                                            </svg>
                                        {/if}
                                    </div>
                                    <div style="min-width: 0;">
                                        <p
                                            style="font-size: 0.8rem; font-weight: 600; color: var(--n-200); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin: 0 0 0.15rem 0;"
                                        >
                                            {cmd.filename}
                                        </p>
                                        <p
                                            style="font-size: 0.6rem; font-weight: 700; color: var(--n-500); text-transform: uppercase; letter-spacing: 0.1em; margin: 0;"
                                        >
                                            {formatDocName(cmd.doc_type)}
                                        </p>
                                    </div>
                                </button>
                                <!-- Delete File Button -->
                                <button
                                    on:click={() => handleDeleteFile(cmd.id)}
                                    style="color: var(--n-500); background: transparent; border: none; padding: 0.4rem; border-radius: 6px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.2s; margin-left: 0.5rem;"
                                    on:mouseover={(e) => {
                                        e.currentTarget.style.color = "#ef4444";
                                        e.currentTarget.style.backgroundColor =
                                            "rgba(239,68,68,0.1)";
                                    }}
                                    on:mouseout={(e) => {
                                        e.currentTarget.style.color =
                                            "var(--n-500)";
                                        e.currentTarget.style.backgroundColor =
                                            "transparent";
                                    }}
                                    title="Remove File"
                                >
                                    <svg
                                        class="w-4 h-4"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        stroke="currentColor"
                                        stroke-width="2"
                                    >
                                        <path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                                        />
                                    </svg>
                                </button>
                            </div>
                        {/each}
                    </div>
                </div>
            </div>

            <!-- Middle Panel: Document Viewer -->
            <div
                class="flex-1 animate-fade-up stagger-2"
                style="background: var(--bg-card); border-radius: var(--radius-xl); border: 1px solid var(--border-subtle); display: flex; flex-direction: column; overflow: hidden;"
            >
                {#if selectedDoc}
                    {@const doc = documents.find((d) => d.id === selectedDoc)}
                    <div
                        style="padding: 0.75rem 1rem; border-bottom: 1px solid var(--border-subtle); display: flex; align-items: center; justify-content: space-between;"
                    >
                        <div class="flex items-center gap-3">
                            <span
                                style="font-weight: 700; color: var(--n-200); font-size: 0.9rem;"
                                >{doc?.filename}</span
                            >
                            <span
                                style="padding: 0.15rem 0.5rem; background: var(--bg-surface); color: var(--n-500); border-radius: var(--radius-sm); font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;"
                            >
                                {formatDocName(doc?.doc_type)}
                            </span>
                        </div>
                        <div class="flex items-center gap-2">
                            <button
                                on:click={() =>
                                    (zoomLevel = Math.min(
                                        zoomLevel + 0.15,
                                        2.0,
                                    ))}
                                aria-label="Zoom In"
                                style="padding: 0.35rem; border-radius: var(--radius-sm); color: var(--n-400); background: var(--bg-surface); border: 1px solid var(--border-subtle);"
                            >
                                <svg
                                    class="w-4 h-4"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2"
                                    ><path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M12 4v16m8-8H4"
                                    /></svg
                                >
                            </button>
                            <button
                                on:click={() =>
                                    (zoomLevel = Math.max(
                                        zoomLevel - 0.15,
                                        0.5,
                                    ))}
                                aria-label="Zoom Out"
                                style="padding: 0.35rem; border-radius: var(--radius-sm); color: var(--n-400); background: var(--bg-surface); border: 1px solid var(--border-subtle);"
                            >
                                <svg
                                    class="w-4 h-4"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    stroke-width="2"
                                    ><path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        d="M20 12H4"
                                    /></svg
                                >
                            </button>
                        </div>
                    </div>
                    <div
                        class="flex-1"
                        style="background: var(--bg-deep); overflow: auto; padding: 1rem;"
                    >
                        {#if doc}
                            {#if isImage(doc.mime_type)}
                                <div
                                    style="display: flex; justify-content: center; transform: scale({zoomLevel}); transform-origin: top center; transition: transform 0.2s;"
                                >
                                    <img
                                        src={getDocUrl(doc.path)}
                                        alt={doc.filename}
                                        style="max-width: 100%; height: auto; border-radius: var(--radius-md); border: 1px solid var(--border-subtle);"
                                    />
                                </div>
                            {:else if isPdf(doc.mime_type)}
                                <iframe
                                    src={getDocUrl(doc.path)}
                                    title={doc.filename}
                                    style="width: 100%; height: 100%; border: none; border-radius: var(--radius-md); background: white; transform: scale({zoomLevel}); transform-origin: top center;"
                                ></iframe>
                            {:else}
                                <div
                                    style="max-width: 56rem; margin: 0 auto; padding: 3rem; background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); min-height: 600px; transform: scale({zoomLevel}); transform-origin: top center;"
                                >
                                    <div
                                        style="display: flex; justify-content: space-between; border-bottom: 1px solid var(--border-subtle); padding-bottom: 1.5rem; margin-bottom: 1.5rem;"
                                    >
                                        <h1
                                            style="font-size: 1rem; font-weight: 700; color: var(--teal-400); text-transform: uppercase; letter-spacing: -0.01em;"
                                        >
                                            Clinical Record
                                        </h1>
                                        <span
                                            style="font-size: 0.75rem; color: var(--n-500);"
                                            >Ref: {doc.sha256?.substring(
                                                0,
                                                8,
                                            )}</span
                                        >
                                    </div>
                                    <div
                                        style="padding: 1rem; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); margin-bottom: 1rem;"
                                    >
                                        <span
                                            style="font-size: 0.6rem; font-weight: 700; color: var(--teal-400); text-transform: uppercase; letter-spacing: 0.1em;"
                                            >Type</span
                                        >
                                        <p
                                            style="font-weight: 700; color: var(--n-200); margin: 0.25rem 0 0 0;"
                                        >
                                            {formatDocName(
                                                doc.doc_type,
                                            ).toUpperCase()}
                                        </p>
                                    </div>
                                    <p
                                        style="color: var(--n-400); font-size: 0.85rem; line-height: 1.6;"
                                    >
                                        Document: <strong
                                            style="color: var(--n-200);"
                                            >{doc.filename}</strong
                                        >
                                    </p>
                                </div>
                            {/if}
                        {/if}
                    </div>
                {:else}
                    <div
                        class="flex-1 flex flex-col items-center justify-center"
                        style="color: var(--n-600);"
                    >
                        <svg
                            style="width: 4rem; height: 4rem; opacity: 0.15; margin-bottom: 1rem;"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            stroke-width="1"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                            />
                        </svg>
                        <p style="font-weight: 500;">
                            Select a document to preview
                        </p>
                    </div>
                {/if}
            </div>

            <!-- Right Panel: Audit Sidebar -->
            <div
                style="width: 20rem; display: flex; flex-direction: column; gap: 1.25rem; overflow: auto; padding-left: 0.25rem;"
            >
                <!-- Checklist -->
                <div
                    class="animate-fade-up stagger-3"
                    style="background: var(--bg-card); border-radius: var(--radius-xl); border: 1px solid var(--border-subtle); display: flex; flex-direction: column; overflow: hidden;"
                >
                    <div
                        style="padding: 0.75rem 1rem; border-bottom: 1px solid var(--border-subtle); display: flex; align-items: center; justify-content: space-between;"
                    >
                        <div>
                            <h3
                                style="font-weight: 700; color: var(--n-200); font-size: 0.85rem;"
                            >
                                Policy Checklist
                            </h3>
                            <p
                                style="font-size: 0.6rem; color: var(--n-500); font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 0.15rem;"
                            >
                                Medical Necessity
                            </p>
                        </div>
                        <span
                            style="font-size: 0.65rem; font-weight: 700; color: var(--n-400); padding: 0.2rem 0.6rem; background: var(--bg-surface); border-radius: var(--radius-md); border: 1px solid var(--border-subtle);"
                        >
                            {checklist.filter((c) => c.met).length} / {checklist.length}
                        </span>
                    </div>
                    <div style="padding: 0.5rem;">
                        {#each checklist as item}
                            <div
                                style="padding: 0.6rem 0.75rem; display: flex; align-items: flex-start; gap: 0.6rem; border-radius: var(--radius-md); margin-bottom: 0.25rem;
                                {!item.met
                                    ? 'background: rgba(248,113,113,0.04); border: 1px solid rgba(248,113,113,0.1);'
                                    : ''}"
                            >
                                <div
                                    style="flex-shrink: 0; margin-top: 0.1rem;"
                                >
                                    {#if item.met}
                                        <div
                                            style="width: 1.25rem; height: 1.25rem; border-radius: 50%; background: rgba(52,211,153,0.15); display: flex; align-items: center; justify-content: center;"
                                        >
                                            <svg
                                                style="width: 0.75rem; height: 0.75rem; color: var(--status-green);"
                                                fill="currentColor"
                                                viewBox="0 0 20 20"
                                            >
                                                <path
                                                    fill-rule="evenodd"
                                                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                                                    clip-rule="evenodd"
                                                />
                                            </svg>
                                        </div>
                                    {:else}
                                        <div
                                            style="width: 1.25rem; height: 1.25rem; border-radius: 50%; background: rgba(248,113,113,0.15); display: flex; align-items: center; justify-content: center;"
                                        >
                                            <svg
                                                style="width: 0.75rem; height: 0.75rem; color: var(--status-red);"
                                                fill="currentColor"
                                                viewBox="0 0 20 20"
                                            >
                                                <path
                                                    fill-rule="evenodd"
                                                    d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                                                    clip-rule="evenodd"
                                                />
                                            </svg>
                                        </div>
                                    {/if}
                                </div>
                                <div class="flex flex-col flex-1">
                                    <div class="flex items-center gap-3">
                                        <span
                                            style="font-size: 0.75rem; font-weight: 600; color: var(--n-200); line-height: 1.2; display: block;"
                                            class:line-through={item.met}
                                        >
                                            {formatDocName(item.item)}
                                        </span>
                                    </div>
                                    {#if !item.met}
                                        <span
                                            style="font-size: 0.6rem; color: var(--status-red); font-weight: 700; margin-top: 0.2rem; text-transform: uppercase; letter-spacing: 0.1em;"
                                            >Missing Proof</span
                                        >
                                    {/if}
                                </div>
                            </div>
                        {:else}
                            <div
                                style="padding: 2rem; text-align: center; color: var(--n-600); font-size: 0.75rem; font-style: italic;"
                            >
                                Run analysis to generate checklist
                            </div>
                        {/each}
                    </div>
                </div>

                <!-- Doctor's Approved Draft -->
                {#if approvedDraft}
                    <div
                        class="animate-fade-up stagger-3"
                        style="background: var(--bg-card); border-radius: var(--radius-xl); border: 1px solid var(--border-subtle); display: flex; flex-direction: column; overflow: hidden; margin-bottom: 2rem;"
                    >
                        <div
                            style="padding: 0.75rem 1rem; border-bottom: 1px solid var(--border-subtle); display: flex; align-items: center; justify-content: space-between;"
                        >
                            <div
                                style="display: flex; align-items: center; gap: 0.5rem;"
                            >
                                <span style="font-size: 1rem;">👨‍⚕️</span>
                                <h3
                                    style="font-weight: 700; color: var(--n-200); font-size: 0.85rem;"
                                >
                                    Approved Clinical Response
                                </h3>
                            </div>
                            <span
                                style="font-size: 0.65rem; font-weight: 700; color: var(--teal-400); padding: 0.2rem 0.6rem; background: rgba(45,212,191,0.1); border-radius: var(--radius-md); text-transform: uppercase;"
                            >
                                Ready to Send
                            </span>
                        </div>
                        <div style="padding: 1.25rem;">
                            <!-- AI Suggested Reply Content -->
                            {#if approvedDraft.summary || approvedDraft.clinical_summary}
                                <div style="margin-bottom: 1.25rem;">
                                    <h4
                                        style="font-size: 0.75rem; font-weight: 600; color: var(--n-400); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;"
                                    >
                                        Clinical Summary
                                    </h4>
                                    <p
                                        style="font-size: 0.9rem; color: var(--n-100); line-height: 1.5;"
                                    >
                                        {approvedDraft.summary ||
                                            approvedDraft.clinical_summary}
                                    </p>
                                </div>
                            {/if}

                            {#if approvedDraft.justifications}
                                <div>
                                    <h4
                                        style="font-size: 0.75rem; font-weight: 600; color: var(--n-400); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;"
                                    >
                                        Justification Points
                                    </h4>
                                    <ul
                                        style="margin: 0; padding-left: 1.25rem; font-size: 0.9rem; color: var(--n-100); line-height: 1.5;"
                                    >
                                        {#each Array.isArray(approvedDraft.justifications) ? approvedDraft.justifications : [approvedDraft.justifications] as point}
                                            <li style="margin-bottom: 0.4rem;">
                                                {point.point || point}
                                            </li>
                                        {/each}
                                    </ul>
                                </div>
                            {/if}
                        </div>
                    </div>
                {/if}

                <!-- Risk Flags -->
                <div
                    class="animate-fade-up stagger-4"
                    style="background: var(--bg-card); border-radius: var(--radius-xl); border: 1px solid var(--border-subtle); display: flex; flex-direction: column; overflow: hidden;"
                >
                    <div
                        style="padding: 0.75rem 1rem; border-bottom: 1px solid var(--border-subtle);"
                    >
                        <div class="flex items-center justify-between">
                            <h3
                                style="font-weight: 700; color: var(--n-200); font-size: 0.85rem;"
                            >
                                Clinical Quality
                            </h3>
                            {#if riskFlags.length > 0}
                                <span
                                    style="padding: 0.15rem 0.5rem; background: rgba(248,113,113,0.15); color: var(--status-red); font-size: 0.55rem; font-weight: 700; border-radius: var(--radius-full); text-transform: uppercase; letter-spacing: 0.08em;"
                                >
                                    {riskFlags.length} Flags
                                </span>
                            {/if}
                        </div>
                        <p
                            style="font-size: 0.6rem; color: var(--n-500); font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 0.15rem;"
                        >
                            MedGemma Risk Engine
                        </p>
                    </div>
                    <div style="padding: 0.75rem;">
                        {#each riskFlags as risk}
                            <div
                                style="padding: 0.75rem; border-radius: var(--radius-lg); margin-bottom: 0.5rem; position: relative; overflow: hidden; transition: transform 0.2s;
                                {risk.severity >= 4
                                    ? 'background: rgba(248,113,113,0.04); border: 1px solid rgba(248,113,113,0.1);'
                                    : 'background: rgba(251,191,36,0.04); border: 1px solid rgba(251,191,36,0.1);'}"
                            >
                                <div
                                    class="flex items-center gap-2"
                                    style="margin-bottom: 0.4rem;"
                                >
                                    <div
                                        style="width: 0.4rem; height: 0.4rem; border-radius: 50%; animation: pulse 2s ease infinite;
                                        {risk.severity >= 4
                                            ? 'background: var(--status-red);'
                                            : 'background: var(--status-amber);'}"
                                    ></div>
                                    <span
                                        style="font-size: 0.6rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em;
                                        {risk.severity >= 4
                                            ? 'color: var(--status-red);'
                                            : 'color: var(--status-amber);'}"
                                    >
                                        {risk.flag?.replace("_", " ") || "RISK"}
                                    </span>
                                </div>
                                <p
                                    style="font-size: 0.75rem; font-weight: 600; color: var(--n-200); margin-bottom: 0.5rem; line-height: 1.4;"
                                >
                                    {risk.message}
                                </p>
                                <div
                                    style="padding: 0.5rem; background: var(--bg-surface); border-radius: var(--radius-md); border: 1px solid var(--border-subtle);"
                                >
                                    <div class="flex items-start gap-2">
                                        <span
                                            style="font-size: 0.55rem; font-weight: 700; color: var(--n-500); text-transform: uppercase; letter-spacing: 0.1em; margin-top: 0.1rem;"
                                            >Fix</span
                                        >
                                        <p
                                            style="font-size: 0.7rem; color: var(--n-400); line-height: 1.3; font-weight: 500; font-style: italic; margin: 0;"
                                        >
                                            {risk.recommendation ||
                                                "Re-verify document clarity."}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        {:else}
                            <div
                                class="flex flex-col items-center justify-center"
                                style="padding: 2rem; text-align: center;"
                            >
                                <div
                                    style="width: 3rem; height: 3rem; border-radius: 50%; background: rgba(52,211,153,0.08); display: flex; align-items: center; justify-content: center; margin-bottom: 0.75rem;"
                                >
                                    <svg
                                        style="width: 1.5rem; height: 1.5rem; color: var(--status-green);"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        stroke="currentColor"
                                        stroke-width="2"
                                    >
                                        <path
                                            stroke-linecap="round"
                                            stroke-linejoin="round"
                                            d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                                        />
                                    </svg>
                                </div>
                                <p
                                    style="font-size: 0.65rem; font-weight: 700; color: var(--n-300); text-transform: uppercase; letter-spacing: 0.12em;"
                                >
                                    Clean Record
                                </p>
                                <p
                                    style="font-size: 0.6rem; color: var(--n-500); text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600;"
                                >
                                    Verified by MedGemma
                                </p>
                            </div>
                        {/each}
                    </div>
                </div>
            </div>
        </div>
    {/if}
</div>

<!-- Cinematic Pipeline Overlay -->
{#if pipelineActive}
    <div
        class="pipeline-overlay"
        on:click|self={() => {}}
        role="dialog"
        aria-label="Analysis Pipeline"
    >
        <div class="pipeline-panel">
            <!-- Header -->
            <div
                style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.5rem;"
            >
                <div
                    style="width: 2.5rem; height: 2.5rem; border-radius: 50%; background: linear-gradient(135deg, var(--teal-500), var(--teal-600)); display: flex; align-items: center; justify-content: center; box-shadow: 0 0 20px rgba(8,145,178,0.4);"
                >
                    <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="white"
                        stroke-width="2"
                        ><path
                            d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v18m0 0h10a2 2 0 0 0 2-2V9M9 21H5a2 2 0 0 1-2-2V9m0 0h18"
                        /></svg
                    >
                </div>
                <div>
                    <h3
                        style="font-size: 1rem; font-weight: 700; color: var(--n-50); letter-spacing: -0.02em; font-family: 'Clash Display', 'DM Sans', sans-serif;"
                    >
                        MedGemma Analysis Pipeline
                    </h3>
                    <p
                        style="font-size: 0.7rem; color: var(--teal-400); font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em;"
                    >
                        Edge AI · Zero Cloud
                    </p>
                </div>
            </div>

            <!-- Pipeline Stages -->
            <div
                style="display: flex; align-items: center; gap: 0; margin-bottom: 1.5rem; padding: 0 0.5rem;"
            >
                {#each [["classify", "Document Classification"], ["quality", "Quality Scan"], ["score", "Readiness Score"]] as [key, label], i}
                    <div style="flex: 1; display: flex; align-items: center;">
                        <div
                            class="pipeline-node"
                            class:active={pipelineStages[key] === "active"}
                            class:done={pipelineStages[key] === "done"}
                        >
                            {#if pipelineStages[key] === "done"}
                                <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    stroke-width="3"
                                    ><path d="M5 13l4 4L19 7" /></svg
                                >
                            {:else if pipelineStages[key] === "active"}
                                <div class="node-spinner"></div>
                            {:else}
                                <span
                                    style="font-size: 0.7rem; font-weight: 700;"
                                    >{i + 1}</span
                                >
                            {/if}
                        </div>
                        <span
                            class="pipeline-label"
                            class:active={pipelineStages[key] === "active"}
                            class:done={pipelineStages[key] === "done"}
                            >{label}</span
                        >
                        {#if i < 2}
                            <div
                                class="pipeline-connector"
                                class:done={pipelineStages[key] === "done"}
                            ></div>
                        {/if}
                    </div>
                {/each}
            </div>

            <!-- Live Feed -->
            <div class="pipeline-feed">
                {#each pipelineResults as item, i}
                    <div class="feed-item" style="animation-delay: {i * 0.05}s">
                        <span style="min-width: 1.25rem; text-align: center;"
                            >{item.icon}</span
                        >
                        <span
                            style="flex: 1; color: {item.level === 'warning'
                                ? 'var(--amber-400)'
                                : item.level === 'error'
                                  ? 'var(--status-red)'
                                  : 'var(--n-300)'}; font-size: 0.8rem; font-family: 'JetBrains Mono', 'Space Grotesk', monospace;"
                            >{item.message}</span
                        >
                        {#if item.elapsed}
                            <span
                                style="color: var(--n-600); font-size: 0.7rem; font-family: monospace;"
                                >{item.elapsed}s</span
                            >
                        {/if}
                    </div>
                {/each}
                {#if analyzing && !showScoreReveal}
                    <div class="feed-item" style="opacity: 0.6;">
                        <div class="feed-spinner"></div>
                        <span
                            style="color: var(--n-500); font-size: 0.8rem; font-style: italic;"
                            >Processing...</span
                        >
                    </div>
                {/if}
            </div>

            <!-- Score Reveal -->
            {#if showScoreReveal && finalScore !== null}
                <div class="score-reveal">
                    <div
                        class="score-ring"
                        style="--ring-color: {finalBand === 'GREEN'
                            ? 'var(--status-green)'
                            : finalBand === 'AMBER'
                              ? 'var(--status-amber)'
                              : 'var(--status-red)'}"
                    >
                        <span class="score-number">{finalScore}</span>
                        <span
                            style="font-size: 0.65rem; color: var(--n-500); text-transform: uppercase; letter-spacing: 0.1em;"
                            >/ 100</span
                        >
                    </div>
                    <div style="text-align: center;">
                        <div
                            class="band-badge"
                            style="background: {finalBand === 'GREEN'
                                ? 'var(--status-green)'
                                : finalBand === 'AMBER'
                                  ? 'var(--status-amber)'
                                  : 'var(--status-red)'}"
                        >
                            {finalBand}
                        </div>
                        <p
                            style="font-size: 0.75rem; color: var(--n-400); margin-top: 0.5rem;"
                        >
                            Analysis complete
                        </p>
                    </div>
                </div>
            {/if}
        </div>
    </div>
{/if}

<!-- Policy Viewer Modal -->
{#if viewingPolicy}
    <div
        style="position: fixed; inset: 0; background: rgba(15,23,42,0.85); backdrop-filter: blur(8px); display: flex; flex-direction: column; z-index: 200;"
    >
        <div
            style="padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; background: var(--bg-card); border-bottom: 1px solid var(--border-subtle);"
        >
            <h3
                style="color: var(--n-50); font-weight: 600; font-size: 1.1rem; flex: 1;"
            >
                Policy Viewer
            </h3>
            <button
                on:click={() => {
                    viewingPolicy = null;
                }}
                style="padding: 0.5rem 1rem; border-radius: var(--radius-md); font-weight: 600; font-size: 0.85rem; background: var(--bg-surface); color: var(--n-200); border: 1px solid var(--border-subtle); cursor: pointer; transition: all 0.2s;"
                on:mouseover={(e) => (e.currentTarget.style.color = "white")}
                on:mouseout={(e) =>
                    (e.currentTarget.style.color = "var(--n-200)")}
            >
                Close Viewer
            </button>
        </div>
        <div
            style="flex: 1; overflow: hidden; background: #e2e8f0; display: flex; justify-content: center;"
        >
            <iframe
                src={viewingPolicy}
                style="width: 100%; max-width: 1200px; height: 100%; border: none; background: white; box-shadow: 0 0 40px rgba(0,0,0,0.5);"
                title="Policy Document"
            ></iframe>
        </div>
    </div>
{/if}

<!-- Confirm Send to Payer Modal -->
{#if confirmingSendToPayer}
    <div
        style="position: fixed; inset: 0; background: rgba(15,23,42,0.85); backdrop-filter: blur(8px); display: flex; align-items: center; justify-content: center; z-index: 300;"
    >
        <div
            style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-xl); overflow: hidden; max-width: 28rem; width: 100%; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5);"
        >
            <div style="padding: 1.5rem 1.5rem 1rem;">
                <h3
                    style="color: var(--n-50); font-weight: 700; font-size: 1.25rem; margin-bottom: 0.5rem; letter-spacing: -0.02em;"
                >
                    Submit to Payer?
                </h3>
                <p
                    style="color: var(--n-400); font-size: 0.85rem; line-height: 1.5;"
                >
                    You are about to submit this clinical response and evidence
                    pack to the payer. This action will lock the case and
                    prevent further edits.
                </p>
            </div>
            <div
                style="padding: 1rem 1.5rem; background: var(--bg-surface); display: flex; justify-content: flex-end; gap: 0.75rem; border-top: 1px solid var(--border-subtle);"
            >
                <button
                    on:click={() => {
                        confirmingSendToPayer = false;
                    }}
                    style="padding: 0.5rem 1rem; border-radius: var(--radius-md); font-weight: 600; font-size: 0.85rem; background: transparent; color: var(--n-300); border: 1px solid var(--border-strong); cursor: pointer; transition: all 0.2s;"
                >
                    Cancel
                </button>
                <button
                    on:click={confirmPayerSubmission}
                    style="padding: 0.5rem 1.25rem; border-radius: var(--radius-md); font-weight: 600; font-size: 0.85rem; background: #6366f1; color: white; border: none; box-shadow: 0 4px 12px rgba(99,102,241,0.3); cursor: pointer; transition: all 0.2s;"
                >
                    Submit Case
                </button>
            </div>
        </div>
    </div>
{/if}

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

    /* Pipeline Overlay */
    .pipeline-overlay {
        position: fixed;
        inset: 0;
        z-index: 1000;
        background: rgba(5, 10, 20, 0.85);
        backdrop-filter: blur(12px);
        display: flex;
        align-items: center;
        justify-content: center;
        animation: fadeIn 0.3s ease;
    }
    @keyframes fadeIn {
        from {
            opacity: 0;
        }
        to {
            opacity: 1;
        }
    }
    .pipeline-panel {
        width: min(560px, 92vw);
        max-height: 80vh;
        overflow-y: auto;
        background: linear-gradient(
            170deg,
            rgba(15, 23, 42, 0.98),
            rgba(10, 16, 30, 0.98)
        );
        border: 1px solid rgba(8, 145, 178, 0.2);
        border-radius: 1rem;
        padding: 1.75rem;
        box-shadow:
            0 0 60px rgba(8, 145, 178, 0.1),
            0 25px 50px rgba(0, 0, 0, 0.5);
    }

    /* Pipeline Nodes */
    .pipeline-node {
        width: 2rem;
        height: 2rem;
        border-radius: 50%;
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--bg-elevated);
        border: 2px solid var(--n-700);
        color: var(--n-500);
        transition: all 0.4s ease;
    }
    .pipeline-node.active {
        border-color: var(--teal-400);
        color: var(--teal-400);
        box-shadow: 0 0 16px rgba(8, 145, 178, 0.4);
    }
    .pipeline-node.done {
        background: var(--teal-500);
        border-color: var(--teal-500);
        color: white;
    }
    .node-spinner {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        border: 2px solid rgba(8, 145, 178, 0.3);
        border-top-color: var(--teal-400);
        animation: spin 0.7s linear infinite;
    }
    .pipeline-label {
        font-size: 0.65rem;
        font-weight: 600;
        color: var(--n-600);
        margin-left: 0.4rem;
        white-space: nowrap;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        transition: color 0.3s;
    }
    .pipeline-label.active,
    .pipeline-label.done {
        color: var(--n-300);
    }
    .pipeline-connector {
        flex: 1;
        height: 2px;
        background: var(--n-800);
        margin: 0 0.5rem;
        position: relative;
        overflow: hidden;
        min-width: 1rem;
    }
    .pipeline-connector.done {
        background: var(--teal-500);
    }

    /* Live Feed */
    .pipeline-feed {
        max-height: 200px;
        overflow-y: auto;
        border: 1px solid var(--n-800);
        border-radius: 0.5rem;
        padding: 0.5rem;
        background: rgba(0, 0, 0, 0.3);
        scrollbar-width: thin;
        scrollbar-color: var(--n-700) transparent;
    }
    .feed-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.3rem 0.4rem;
        border-radius: 0.25rem;
        animation: slideIn 0.2s ease;
    }
    .feed-item:hover {
        background: rgba(255, 255, 255, 0.03);
    }
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(6px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    .feed-spinner {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin: 0 0.15rem;
        border: 2px solid var(--n-700);
        border-top-color: var(--teal-400);
        animation: spin 0.7s linear infinite;
    }

    /* Score Reveal */
    .score-reveal {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1.5rem;
        padding: 1.5rem 0 0.5rem;
        animation: revealPop 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
    }
    @keyframes revealPop {
        from {
            opacity: 0;
            transform: scale(0.7);
        }
        to {
            opacity: 1;
            transform: scale(1);
        }
    }
    .score-ring {
        width: 5rem;
        height: 5rem;
        border-radius: 50%;
        border: 3px solid var(--ring-color);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 30px
            color-mix(in srgb, var(--ring-color) 30%, transparent);
        animation: ringGlow 2s ease infinite alternate;
    }
    @keyframes ringGlow {
        from {
            box-shadow: 0 0 20px
                color-mix(in srgb, var(--ring-color) 20%, transparent);
        }
        to {
            box-shadow: 0 0 40px
                color-mix(in srgb, var(--ring-color) 40%, transparent);
        }
    }
    .score-number {
        font-size: 1.75rem;
        font-weight: 800;
        color: var(--n-50);
        font-family: "Clash Display", "DM Sans", sans-serif;
    }
    .band-badge {
        display: inline-block;
        padding: 0.25rem 1rem;
        border-radius: 2rem;
        font-size: 0.7rem;
        font-weight: 800;
        color: white;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
</style>
