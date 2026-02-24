<script lang="ts">
    import { onMount } from "svelte";
    import * as api from "$lib/api";

    // Live Policy State
    let policies: any[] = [];
    let loading = true;

    // Search State
    let searchQuery = "";
    let searchResults: any[] = [];
    let searching = false;

    // Upload & Indexing Terminal State
    let isUploading = false;
    let isIndexing = false;
    let uploadPayerId = "ICICI Lombard";
    let terminalLogs: string[] = [];
    let showTerminal = false;

    // PDF Viewer
    let viewingResult: any = null;
    let fileInput: HTMLInputElement;

    function escapeRegExp(string: string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    }

    function highlightText(text: string, keyword: string) {
        if (!keyword) return text;
        const regex = new RegExp(`(${escapeRegExp(keyword)})`, "gi");
        return text.replace(
            regex,
            `<mark style="background: rgba(20, 184, 166, 0.3); border: 1px solid rgba(20,184,166,0.6); color: #fff; padding: 0.1rem 0.3rem; border-radius: 4px; font-weight: 700; box-shadow: 0 0 10px rgba(20,184,166,0.4);">$1</mark>`,
        );
    }

    const formatDocName = (str: string) => {
        if (!str) return "Unclassified";
        return str.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
    };

    onMount(async () => {
        await loadPolicies();
    });

    async function loadPolicies() {
        loading = true;
        try {
            policies = await api.getPolicies();
        } catch (e) {
            console.error("Failed to load policies", e);
        }
        loading = false;
    }

    async function searchPolicies() {
        if (!searchQuery.trim()) return;
        searching = true;
        try {
            // Search ALL indexed policies
            const indexedPolicies = policies.filter((p) => p.index_path);
            let allResults: any[] = [];
            for (const p of indexedPolicies) {
                try {
                    let res = await api.searchPolicy(
                        p.payer_id,
                        searchQuery,
                        3,
                    );
                    if (res && res.results) {
                        allResults = allResults.concat(
                            res.results.map((r: any) => ({
                                ...r,
                                payer: p.payer_id,
                            })),
                        );
                    }
                } catch (e) {
                    console.error(`Search failed for ${p.payer_id}`, e);
                }
            }
            // Sort by Cosine Similarity (HIGHER is better in Inner Product)
            allResults.sort((a, b) => b.distance - a.distance);
            // Keep only highest contextual relevance
            searchResults = allResults.slice(0, 5);
        } catch (e) {
            console.error("Search failed", e);
            searchResults = [];
        }
        searching = false;
    }

    async function handleDelete(payerId: string) {
        if (
            !confirm(
                `Are you sure you want to completely delete the policy, PDFs, and FAISS index for ${payerId}?`,
            )
        )
            return;
        try {
            await api.deletePolicy(payerId);
            await loadPolicies();
        } catch (e) {
            console.error("Delete failed", e);
        }
    }

    function triggerUpload(payerId: string) {
        uploadPayerId = payerId;
        fileInput.click();
    }

    async function handleFileSelected(event: Event) {
        const input = event.target as HTMLInputElement;
        if (!input.files || input.files.length === 0) return;

        const file = input.files[0];

        // --- 1. Upload Phase ---
        showTerminal = true;
        terminalLogs = [];
        addLog(`[System] Initiating local upload of ${file.name}...`);

        isUploading = true;
        try {
            await api.uploadPolicy(uploadPayerId, file);
            addLog(
                `[Success] File successfully written to /data/policies/${uploadPayerId}/pdfs`,
            );
        } catch (e: any) {
            addLog(`[Error] Upload failed: ${e.message}`);
            isUploading = false;
            return;
        }
        isUploading = false;

        // --- 2. Indexing Phase (Real SSE) ---
        addLog(
            `\n[Agentive RAG] Triggering local FAISS vector construction...`,
        );
        isIndexing = true;
        try {
            const response = await fetch(
                `/api/policies/${uploadPayerId}/index-stream`,
            );
            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            if (!reader) throw new Error("Stream failed");

            let buffer = "";
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split("\n\n");
                buffer = parts.pop() || "";

                for (const part of parts) {
                    if (part.startsWith("event: log")) {
                        const data = JSON.parse(part.split("data: ")[1]);
                        addLog(`[${data.step.toUpperCase()}] ${data.message}`);
                    } else if (part.startsWith("event: complete")) {
                        const data = JSON.parse(part.split("data: ")[1]);
                        addLog(
                            `\n✨ POLICY VECTORIZATION COMPLETE: ${data.chunks} chunks embedded.`,
                        );
                    }
                }
            }

            // Reload UI
            await loadPolicies();
        } catch (e: any) {
            addLog(
                `[Error] FAISS Indexing failed: ${e.message || "Check terminal output for Ollama errors."}`,
            );
        }
        isIndexing = false;

        // Auto-close terminal after 4 seconds of completion
        setTimeout(() => {
            showTerminal = false;
        }, 4000);
    }

    async function forceIndexBuild(payerId: string) {
        showTerminal = true;
        terminalLogs = [];
        addLog(`[System] Forcing local FAISS index rebuild for ${payerId}...`);
        isIndexing = true;

        try {
            const response = await fetch(
                `/api/policies/${payerId}/index-stream`,
            );
            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            if (!reader) throw new Error("Stream failed");

            let buffer = "";
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const parts = buffer.split("\n\n");
                buffer = parts.pop() || "";

                for (const part of parts) {
                    if (part.startsWith("event: log")) {
                        const data = JSON.parse(part.split("data: ")[1]);
                        addLog(`[${data.step.toUpperCase()}] ${data.message}`);
                    } else if (part.startsWith("event: complete")) {
                        const data = JSON.parse(part.split("data: ")[1]);
                        addLog(
                            `\n✨ POLICY VECTORIZATION COMPLETE: ${data.chunks} chunks embedded.`,
                        );
                    }
                }
            }

            await loadPolicies();
        } catch (e: any) {
            addLog(`[Error] FAISS Indexing failed: ${e.message}`);
        }

        isIndexing = false;
        setTimeout(() => {
            showTerminal = false;
        }, 4000);
    }

    function addLog(msg: string) {
        terminalLogs = [...terminalLogs, msg];
        // Auto scroll to bottom of terminal could go here
    }
</script>

<div
    class="flex flex-col gap-6"
    style="max-width: 80rem; margin: 0 auto; height: 100%;"
>
    <div class="flex items-center justify-between animate-fade-up">
        <div class="flex flex-col gap-1">
            <h1
                style="font-size: 1.75rem; font-weight: 700; color: var(--n-50); letter-spacing: -0.03em;"
            >
                Semantic Policy Library
            </h1>
            <p style="font-size: 0.85rem; color: var(--n-500);">
                100% Offline Document Retrieval & Payer Guidelines
            </p>
        </div>

        <div style="display: flex; gap: 0.5rem; align-items: center;">
            <input
                type="file"
                accept=".pdf"
                bind:this={fileInput}
                on:change={handleFileSelected}
                style="display: none;"
            />
            <button
                on:click={() => triggerUpload("ICICI Lombard")}
                disabled={isUploading || isIndexing}
                style="display: flex; align-items: center; gap: 0.4rem; padding: 0.5rem 1rem; background: linear-gradient(135deg, var(--teal-500), var(--teal-600)); color: white; border-radius: var(--radius-md); font-size: 0.8rem; font-weight: 600; box-shadow: var(--shadow-glow-teal); border: none; cursor: pointer; transition: all 0.2s;"
                on:mouseover={(e) =>
                    (e.currentTarget.style.transform = "translateY(-1px)")}
                on:focus={(e) =>
                    (e.currentTarget.style.transform = "translateY(-1px)")}
                on:mouseout={(e) =>
                    (e.currentTarget.style.transform = "translateY(0)")}
                on:blur={(e) =>
                    (e.currentTarget.style.transform = "translateY(0)")}
            >
                <svg
                    class="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2.5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                    />
                </svg>
                Upload ICICI Lombard
            </button>
            <button
                on:click={() => triggerUpload("Star Health Insurance")}
                disabled={isUploading || isIndexing}
                style="display: flex; align-items: center; gap: 0.4rem; padding: 0.5rem 1rem; background: linear-gradient(135deg, #8b5cf6, #6d28d9); color: white; border-radius: var(--radius-md); font-size: 0.8rem; font-weight: 600; box-shadow: 0 0 15px rgba(139, 92, 246, 0.4); border: none; cursor: pointer; transition: all 0.2s;"
                on:mouseover={(e) =>
                    (e.currentTarget.style.transform = "translateY(-1px)")}
                on:focus={(e) =>
                    (e.currentTarget.style.transform = "translateY(-1px)")}
                on:mouseout={(e) =>
                    (e.currentTarget.style.transform = "translateY(0)")}
                on:blur={(e) =>
                    (e.currentTarget.style.transform = "translateY(0)")}
            >
                <svg
                    class="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2.5"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"
                    />
                </svg>
                Upload Star Health
            </button>
        </div>
    </div>

    <!-- Live Policy Cards -->
    <div class="grid grid-cols-3 gap-5 animate-fade-up stagger-1">
        {#if loading}
            <div style="color: var(--n-400); font-size: 0.85rem;">
                Loading policies from SQLite...
            </div>
        {:else if policies.length === 0}
            <div
                style="grid-column: span 3; color: var(--n-400); font-size: 0.9rem; text-align: center; padding: 3rem; border: 1px dashed var(--border-subtle); border-radius: var(--radius-md);"
            >
                No policies indexed yet. Use the "Upload & Embed PDF" button to
                populate the FAISS Database.
            </div>
        {:else}
            {#each policies as policy}
                <div
                    class="premium-card p-5"
                    style="display: flex; flex-direction: column; gap: 1rem;"
                >
                    <div class="flex items-start justify-between">
                        <div>
                            <h3
                                style="font-weight: 700; color: var(--n-100); font-size: 0.95rem; text-transform: uppercase;"
                            >
                                {policy.payer_id}
                            </h3>
                            <div
                                style="font-size: 0.75rem; color: var(--n-400); margin-top: 0.25rem;"
                            >
                                Version {policy.version}
                            </div>
                        </div>
                        {#if policy.index_path}
                            <div class="flex items-center gap-2">
                                <span
                                    style="padding: 0.25rem 0.6rem; font-size: 0.65rem; font-weight: 700; background: rgba(52,211,153,0.1); color: var(--status-green); border-radius: var(--radius-full); text-transform: uppercase; letter-spacing: 0.05em;"
                                    >Vectorized</span
                                >
                                <button
                                    on:click={() =>
                                        handleDelete(policy.payer_id)}
                                    style="padding: 0.2rem 0.5rem; color: #ef4444; background: transparent; border: 1px solid #ef4444; border-radius: 4px; font-size: 0.65rem; cursor: pointer; opacity: 0.7; transition: opacity 0.2s;"
                                    class="hover:opacity-100">Delete</button
                                >
                            </div>
                        {:else}
                            <div class="flex items-center gap-2">
                                <span
                                    style="padding: 0.25rem 0.6rem; font-size: 0.65rem; font-weight: 700; background: rgba(245, 158, 11, 0.1); color: #f59e0b; border-radius: var(--radius-full); text-transform: uppercase; letter-spacing: 0.05em;"
                                    >Needs Embedding</span
                                >
                                <button
                                    on:click={() =>
                                        triggerUpload(policy.payer_id)}
                                    style="padding: 0.25rem 0.6rem; background: var(--teal-500); color: white; border: none; border-radius: 4px; font-size: 0.65rem; font-weight: 600; cursor: pointer;"
                                    >Upload PDF</button
                                >
                                <button
                                    on:click={() =>
                                        handleDelete(policy.payer_id)}
                                    style="padding: 0.2rem 0.5rem; color: #ef4444; background: transparent; border: 1px solid #ef4444; border-radius: 4px; font-size: 0.65rem; cursor: pointer; opacity: 0.7; transition: opacity 0.2s;"
                                    class="hover:opacity-100">Delete</button
                                >
                            </div>
                        {/if}
                    </div>

                    {#if policy.index_path}
                        <div
                            style="padding-top: 1rem; border-top: 1px solid var(--border-subtle);"
                        >
                            <div
                                class="flex items-center justify-between text-sm"
                                style="margin-bottom: 0.75rem;"
                            >
                                <span
                                    style="font-size: 0.75rem; color: var(--n-400);"
                                    >Local FAISS Index Active</span
                                >
                                <button
                                    style="font-size: 0.75rem; color: var(--teal-400); font-weight: 600; cursor: pointer; border: none; background: none;"
                                    on:click={() =>
                                        forceIndexBuild(policy.payer_id)}
                                    >Rebuild</button
                                >
                            </div>
                            <!-- Just showing the first source file for demo -->
                            {#if policy.source_files && policy.source_files.length > 0}
                                <button
                                    on:click={() => {
                                        viewingResult = {
                                            url: `http://localhost:8000/docs/policies/${encodeURIComponent(policy.payer_id)}/pdfs/${policy.source_files[0]}`,
                                            text: "Document loaded directly from library root.",
                                            keyword: "",
                                            payer: policy.payer_id,
                                        };
                                    }}
                                    style="display: block; width: 100%; text-align: center; padding: 0.5rem; font-size: 0.75rem; font-weight: 600; color: var(--n-200); background: var(--bg-body); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); transition: all 0.2s; cursor: pointer;"
                                >
                                    View {formatDocName(policy.source_files[0])}
                                </button>
                            {/if}
                        </div>
                    {:else}
                        <div
                            style="padding-top: 1rem; border-top: 1px solid var(--border-subtle);"
                        >
                            <button
                                class="glow-button"
                                on:click={() =>
                                    forceIndexBuild(policy.payer_id)}
                                style="width: 100%; text-align: center; padding: 0.5rem; font-size: 0.75rem; font-weight: 600; color: white; background: var(--teal-500); border: none; border-radius: var(--radius-md); cursor: pointer;"
                            >
                                Force Index Build
                            </button>
                        </div>
                    {/if}
                </div>
            {/each}
        {/if}
    </div>

    <!-- Search -->
    <div class="premium-card p-6" style="margin-bottom: 2rem;">
        <h3
            style="font-weight: 700; color: var(--n-50); margin-bottom: 1rem; font-size: 1.1rem;"
        >
            Policy Search
        </h3>

        <div style="display: flex; gap: 1rem; margin-bottom: 1.5rem;">
            <div style="flex: 1; position: relative;">
                <input
                    type="text"
                    bind:value={searchQuery}
                    on:keydown={(e) => e.key === "Enter" && searchPolicies()}
                    placeholder="Search policy documents..."
                    style="width: 100%; padding: 0.75rem 1rem 0.75rem 2.5rem; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); color: var(--n-100); font-size: 0.9rem; outline: none; transition: border-color 0.2s;"
                />
                <svg
                    style="width: 1.1rem; height: 1.1rem; color: var(--n-500); position: absolute; left: 0.8rem; top: 0.85rem;"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                    />
                </svg>
            </div>

            <button
                class="glow-button"
                on:click={searchPolicies}
                style="padding: 0.75rem 1.5rem; background: linear-gradient(135deg, var(--teal-500), var(--teal-600)); color: white; border-radius: var(--radius-md); font-weight: 600; font-size: 0.9rem; border: none; cursor: pointer; box-shadow: var(--shadow-glow-teal);"
            >
                Search
            </button>
        </div>

        <!-- Results -->
        {#if searching}
            <div
                style="display: flex; align-items: center; justify-content: center; padding: 3rem 0; color: var(--n-400);"
            >
                <div
                    style="width: 1.5rem; height: 1.5rem; border-radius: 50%; border: 3px solid var(--border-subtle); border-top-color: var(--teal-400); animation: spin 0.8s linear infinite; margin-right: 0.75rem;"
                ></div>
                Searching indexed policies...
            </div>
        {:else if searchResults.length > 0}
            <div style="display: flex; flex-direction: column; gap: 1rem;">
                {#each searchResults as result, i}
                    <div
                        style="padding: 1rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); background: var(--bg-surface); transition: border-color 0.2s;"
                    >
                        <div class="flex items-start justify-between gap-4">
                            <div class="flex-1">
                                <p
                                    style="font-size: 0.875rem; color: var(--n-100); line-height: 1.6;"
                                >
                                    {result.text}
                                </p>
                                <div
                                    class="flex items-center gap-3"
                                    style="margin-top: 0.75rem; font-size: 0.75rem; color: var(--n-400);"
                                >
                                    <span class="flex items-center gap-1">
                                        <svg
                                            class="w-4 h-4"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            stroke="currentColor"
                                        >
                                            <path
                                                stroke-linecap="round"
                                                stroke-linejoin="round"
                                                stroke-width="2"
                                                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                                            />
                                        </svg>
                                        {formatDocName(result.pdf_name)}
                                    </span>
                                    <span>Page {result.page_num}</span>
                                </div>
                            </div>
                            <div class="text-right shrink-0">
                                <div
                                    style="font-size: 0.875rem; font-weight: 700; color: var(--status-green);"
                                >
                                    Rank #{result.rank}
                                </div>
                                <div
                                    style="font-size: 0.65rem; color: var(--n-500); text-transform: uppercase;"
                                >
                                    relevance
                                </div>
                            </div>
                        </div>
                        <div
                            style="display: flex; gap: 0.5rem; margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-subtle);"
                        >
                            <button
                                on:click={() => {
                                    viewingResult = {
                                        url: `http://localhost:8000/docs/policies/${encodeURIComponent(result.payer)}/pdfs/${result.pdf_name}#page=${result.page_num}`,
                                        text: result.text,
                                        keyword: searchQuery,
                                        payer: result.payer,
                                    };
                                }}
                                style="padding: 0.5rem 1rem; font-size: 0.8rem; font-weight: 600; color: white; background: linear-gradient(135deg, var(--teal-500), var(--teal-600)); border: none; border-radius: var(--radius-md); cursor: pointer; display: flex; align-items: center; gap: 0.4rem; box-shadow: var(--shadow-glow-teal); transition: all 0.2s;"
                                on:mouseover={(e) =>
                                    (e.currentTarget.style.transform =
                                        "translateY(-1px)")}
                                on:focus={(e) =>
                                    (e.currentTarget.style.transform =
                                        "translateY(-1px)")}
                                on:mouseout={(e) =>
                                    (e.currentTarget.style.transform =
                                        "translateY(0)")}
                                on:blur={(e) =>
                                    (e.currentTarget.style.transform =
                                        "translateY(0)")}
                            >
                                <svg
                                    class="w-4 h-4"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                >
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        stroke-width="2"
                                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                                    />
                                    <path
                                        stroke-linecap="round"
                                        stroke-linejoin="round"
                                        stroke-width="2"
                                        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                                    />
                                </svg>
                                View Match in PDF
                            </button>
                        </div>
                    </div>
                {/each}
            </div>
        {:else if searchQuery}
            <div
                style="text-align: center; padding: 3rem 0; color: var(--n-400);"
            >
                <p>No results found for "{searchQuery}"</p>
            </div>
        {:else}
            <div
                style="text-align: center; padding: 3rem 0; color: var(--n-500);"
            >
                <svg
                    style="width: 3rem; height: 3rem; margin: 0 auto 0.75rem; opacity: 0.5;"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="1"
                        d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                    />
                </svg>
                <p style="font-size: 0.875rem;">
                    Enter a query to search indexed policy documents
                </p>
                <p style="font-size: 0.75rem; margin-top: 0.25rem;">
                    Semantic search powered by 'nomic-embed-text'
                </p>
            </div>
        {/if}
    </div>
</div>

<!-- Terminal Overlay for King Mode Upload Process -->
{#if showTerminal}
    <div
        style="position: fixed; inset: 0; background: rgba(15,23,42,0.9); backdrop-filter: blur(12px); display: flex; align-items: center; justify-content: center; z-index: 300;"
    >
        <div
            class="premium-card p-0"
            style="width: 100%; max-width: 48rem; background: #000; border: 1px solid #333; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);"
        >
            <!-- Mac style window controls -->
            <div
                style="display: flex; gap: 6px; padding: 0.75rem 1rem; background: #1a1a1a; border-bottom: 1px solid #333; border-radius: var(--radius-xl) var(--radius-xl) 0 0;"
            >
                <div
                    style="width: 12px; height: 12px; border-radius: 50%; background: #ff5f56;"
                ></div>
                <div
                    style="width: 12px; height: 12px; border-radius: 50%; background: #ffbd2e;"
                ></div>
                <div
                    style="width: 12px; height: 12px; border-radius: 50%; background: #27c93f;"
                ></div>
                <div
                    style="margin-left: auto; font-family: monospace; font-size: 0.75rem; color: #666;"
                >
                    medgemma_vectorizer_v1.sh
                </div>
            </div>

            <div
                style="padding: 1.5rem; max-height: 60vh; overflow-y: auto; font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.85rem; color: #10b981; line-height: 1.6;"
            >
                {#each terminalLogs as log}
                    <div style="margin-bottom: 0.25rem;">
                        <span style="color: #6366f1;">❯</span>
                        <span style="white-space: pre-wrap;">{log}</span>
                    </div>
                {/each}
                {#if isUploading || isIndexing}
                    <div style="margin-top: 1rem; display: inline-block;">
                        <span style="animation: pulse 1s infinite alternate;"
                            >...</span
                        >
                    </div>
                {/if}
            </div>
            {#if !isUploading && !isIndexing}
                <div
                    style="padding: 1rem; border-top: 1px solid #333; text-align: right;"
                >
                    <button
                        on:click={() => (showTerminal = false)}
                        style="padding: 0.5rem 1rem; background: #222; color: #fff; border: 1px solid #444; border-radius: 4px; cursor: pointer; font-family: monospace;"
                        >[ ESC ] CLOSE</button
                    >
                </div>
            {/if}
        </div>
    </div>
{/if}

<!-- Policy Viewer Modal -->
{#if viewingResult}
    <div
        style="position: fixed; inset: 0; background: rgba(10, 15, 30, 0.85); backdrop-filter: blur(16px); display: flex; flex-direction: column; z-index: 200; animation: fadeIn 0.3s ease-out;"
    >
        <div
            style="padding: 1.25rem 2.5rem; display: flex; justify-content: space-between; align-items: center; background: linear-gradient(to right, rgba(15,23,42,0.95), rgba(30,41,59,0.95)); border-bottom: 1px solid rgba(255,255,255,0.08); box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5);"
        >
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div
                    style="width: 2.5rem; height: 2.5rem; border-radius: 8px; background: linear-gradient(135deg, var(--teal-500), var(--teal-700)); display: flex; align-items: center; justify-content: center; box-shadow: 0 0 15px rgba(20, 184, 166, 0.4);"
                >
                    <svg
                        style="width: 1.25rem; height: 1.25rem; color: white;"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                    >
                        <path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            stroke-width="2"
                            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                        />
                    </svg>
                </div>
                <div>
                    <h3
                        style="color: #f8fafc; font-weight: 700; font-size: 1.15rem; letter-spacing: -0.02em; margin: 0;"
                    >
                        Secure Document Viewer
                    </h3>
                    <p
                        style="color: var(--teal-400); font-size: 0.75rem; font-weight: 600; margin: 0; text-transform: uppercase; letter-spacing: 0.05em;"
                    >
                        Document Origin: {viewingResult.payer}
                    </p>
                </div>
            </div>
            <button
                on:click={() => {
                    viewingResult = null;
                }}
                style="padding: 0.6rem 1.25rem; border-radius: var(--radius-full); font-weight: 600; font-size: 0.85rem; background: rgba(255,255,255,0.05); color: #94a3b8; border: 1px solid rgba(255,255,255,0.1); cursor: pointer; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); display: flex; align-items: center; gap: 0.5rem;"
                on:mouseover={(e) => {
                    e.currentTarget.style.background = "rgba(239, 68, 68, 0.1)";
                    e.currentTarget.style.color = "#ef4444";
                    e.currentTarget.style.borderColor =
                        "rgba(239, 68, 68, 0.3)";
                }}
                on:focus={(e) => {
                    e.currentTarget.style.background = "rgba(239, 68, 68, 0.1)";
                    e.currentTarget.style.color = "#ef4444";
                    e.currentTarget.style.borderColor =
                        "rgba(239, 68, 68, 0.3)";
                }}
                on:mouseout={(e) => {
                    e.currentTarget.style.background = "rgba(255,255,255,0.05)";
                    e.currentTarget.style.color = "#94a3b8";
                    e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)";
                }}
                on:blur={(e) => {
                    e.currentTarget.style.background = "rgba(255,255,255,0.05)";
                    e.currentTarget.style.color = "#94a3b8";
                    e.currentTarget.style.borderColor = "rgba(255,255,255,0.1)";
                }}
            >
                <svg
                    style="width: 1rem; height: 1rem;"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M6 18L18 6M6 6l12 12"
                    />
                </svg>
                Close Viewer
            </button>
        </div>
        <div
            style="flex: 1; overflow: hidden; display: flex; background: radial-gradient(circle at center, rgba(30,41,59,0.8) 0%, rgba(15,23,42,0.95) 100%);"
        >
            <!-- Left Side Semantic Highlight Context Panel -->
            {#if viewingResult.keyword}
                <div
                    style="flex: 0 0 350px; padding: 2rem; border-right: 1px solid rgba(255,255,255,0.08); background: rgba(15,23,42,0.6); display: flex; flex-direction: column; overflow-y: auto;"
                >
                    <div
                        style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1.25rem;"
                    >
                        <svg
                            class="w-5 h-5"
                            style="color: var(--teal-400);"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="2"
                                d="M13 10V3L4 14h7v7l9-11h-7z"
                            />
                        </svg>
                        <h4
                            style="color: #e2e8f0; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;"
                        >
                            AI Extracted Citation
                        </h4>
                    </div>

                    <div
                        style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 1.25rem; position: relative;"
                    >
                        <!-- Cyan Accent line -->
                        <div
                            style="position: absolute; top: 0; left: 0; bottom: 0; width: 3px; background: var(--teal-500); border-radius: 8px 0 0 8px;"
                        ></div>

                        <p
                            style="color: #f8fafc; font-size: 0.85rem; line-height: 1.6; mragin: 0;"
                        >
                            {@html highlightText(
                                viewingResult.text,
                                viewingResult.keyword,
                            )}
                        </p>
                    </div>
                    <p
                        style="margin-top: 2rem; color: #64748b; font-size: 0.75rem; text-align: center;"
                    >
                        The exact semantic match was retrieved from the FAISS
                        database alongside this document.
                    </p>
                </div>
            {/if}

            <div
                style="flex: 1; padding: 2rem; display: flex; justify-content: center; align-items: center; position: relative;"
            >
                <div
                    style="width: 100%; max-width: 1000px; height: 100%; position: relative; border-radius: 12px; overflow: hidden; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255,255,255,0.1);"
                >
                    <!-- Loading state placeholder behind iframe -->
                    <div
                        style="position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; background: #1e293b; z-index: -1;"
                    >
                        <div
                            style="width: 40px; height: 40px; border: 3px solid rgba(20, 184, 166, 0.2); border-top-color: var(--teal-500); border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 1rem;"
                        ></div>
                        <div
                            style="color: #94a3b8; font-size: 0.85rem; font-weight: 500;"
                        >
                            Decrypting & Loading Policy Document...
                        </div>
                    </div>
                    <iframe
                        src={viewingResult.url}
                        style="width: 100%; height: 100%; border: none; background: white;"
                        title="Policy Document"
                    ></iframe>
                </div>
            </div>
        </div>
    </div>
{/if}
