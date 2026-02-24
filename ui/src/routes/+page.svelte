<script lang="ts">
    import { onMount } from "svelte";
    import { goto } from "$app/navigation";
    import {
        getCases,
        deleteCase,
        smartScan,
        createCase,
        uploadFile,
        type Case,
    } from "$lib/api";
    import { currentRole } from "$lib/stores/role";

    let cases: Case[] = [];
    let loading = true;
    let stats = { total: 0, ready: 0, queries: 0, critical: 0 };

    // Smart upload state
    let showUploadModal = false;
    let uploadPhase: "drop" | "scanning" | "confirm" | "uploading" = "drop";
    let scannedMeta = { patient_name: "", lane: "cardio", payer: "" };
    let selectedFiles: File[] = [];
    let uploadProgress = 0;
    let confirmingDelete: string | null = null;

    async function loadData() {
        loading = true;
        try {
            cases = await getCases();
            calculateStats();
        } catch (e) {
            console.error(e);
        } finally {
            loading = false;
        }
    }

    function calculateStats() {
        stats.total = cases.length;
        stats.ready = cases.filter((c) => c.band === "GREEN").length;
        stats.queries = cases.filter(
            (c) => c.status === "Query Drafted" || c.status === "query_drafted",
        ).length;
        stats.critical = cases.filter((c) => c.band === "RED").length;
    }

    onMount(() => {
        loadData();
    });

    function getBandColor(band: string, status?: string) {
        // Pending / un-analyzed → neutral slate gray
        if (status === "closed") return "#3b82f6"; // Blue for Sent to Payer
        if (!band) return "var(--n-500)";

        if (band === "GREEN") return "var(--status-green)";
        if (band === "AMBER") return "var(--status-amber)";
        return "var(--status-red)";
    }

    async function handleDeleteCase(id: string) {
        try {
            await deleteCase(id);
            confirmingDelete = null;
            await loadData();
        } catch (e) {
            console.error(e);
        }
    }

    function handleFolderSelect(e: Event) {
        const input = e.target as HTMLInputElement;
        if (!input.files?.length) return;
        selectedFiles = Array.from(input.files).filter(
            (f) =>
                f.name.endsWith(".pdf") ||
                f.name.endsWith(".jpg") ||
                f.name.endsWith(".jpeg") ||
                f.name.endsWith(".png"),
        );
        if (selectedFiles.length > 0) {
            runSmartScan();
        }
    }

    async function handleDropFiles(e: DragEvent) {
        e.preventDefault();
        const items = e.dataTransfer?.items;
        if (!items) return;

        const allFiles: File[] = [];

        async function readEntry(entry: any): Promise<void> {
            if (entry.isFile) {
                const file: File = await new Promise((resolve) =>
                    entry.file(resolve),
                );
                const name = file.name.toLowerCase();
                if (
                    name.endsWith(".pdf") ||
                    name.endsWith(".jpg") ||
                    name.endsWith(".jpeg") ||
                    name.endsWith(".png")
                ) {
                    allFiles.push(file);
                }
            } else if (entry.isDirectory) {
                const reader = entry.createReader();
                const entries: any[] = await new Promise((resolve) =>
                    reader.readEntries(resolve),
                );
                for (const child of entries) {
                    await readEntry(child);
                }
            }
        }

        for (let i = 0; i < items.length; i++) {
            const entry = items[i].webkitGetAsEntry?.();
            if (entry) {
                await readEntry(entry);
            }
        }

        if (allFiles.length > 0) {
            selectedFiles = allFiles;
            runSmartScan();
        } else if (e.dataTransfer?.files?.length) {
            // Fallback: plain file drop
            selectedFiles = Array.from(e.dataTransfer.files).filter((f) => {
                const n = f.name.toLowerCase();
                return (
                    n.endsWith(".pdf") ||
                    n.endsWith(".jpg") ||
                    n.endsWith(".jpeg") ||
                    n.endsWith(".png")
                );
            });
            if (selectedFiles.length > 0) runSmartScan();
        }
    }

    async function runSmartScan() {
        uploadPhase = "scanning";
        const firstPdf = selectedFiles.find((f) => f.name.endsWith(".pdf"));
        if (firstPdf) {
            try {
                const result = await smartScan(firstPdf);
                scannedMeta = {
                    patient_name: result.patient_name,
                    lane: result.lane,
                    payer: result.payer,
                };
            } catch {
                /* use defaults */
            }
        }
        uploadPhase = "confirm";
    }

    async function confirmUpload() {
        uploadPhase = "uploading";
        try {
            const caseData = await createCase({
                patient_alias: scannedMeta.patient_name || "Unknown Patient",
                lane: scannedMeta.lane,
                payer_id: scannedMeta.payer || "unknown",
                case_number: `PRAMANA-${Math.floor(Math.random() * 9000) + 1000}`,
            });
            for (let i = 0; i < selectedFiles.length; i++) {
                await uploadFile(caseData.id, selectedFiles[i]);
                uploadProgress = Math.round(
                    ((i + 1) / selectedFiles.length) * 100,
                );
            }
            closeModal();
            // Automatically navigate to the newly created case details page
            goto(`/cases/${caseData.id}`);
        } catch (e) {
            console.error(e);
            alert("Upload failed: " + (e as Error).message);
        }
    }

    function closeModal() {
        showUploadModal = false;
        uploadPhase = "drop";
        selectedFiles = [];
        uploadProgress = 0;
        scannedMeta = { patient_name: "", lane: "cardio", payer: "" };
    }
</script>

<!-- Role: TPA Desk -->
{#if $currentRole === "tpa"}
    <div class="flex flex-col gap-6" style="max-width: 80rem; margin: 0 auto;">
        <div class="flex items-center justify-between animate-fade-up">
            <div class="flex flex-col gap-1">
                <h1
                    style="font-size: 1.75rem; font-weight: 700; color: var(--n-50); letter-spacing: -0.03em;"
                >
                    Case Workbench
                </h1>
                <p style="font-size: 0.85rem; color: var(--n-500);">
                    Manage, audit, and verify active claim cases.
                </p>
            </div>
            <button
                on:click={() => {
                    showUploadModal = true;
                    uploadPhase = "drop";
                }}
                style="display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem; background: linear-gradient(135deg, var(--teal-500), var(--teal-600)); color: white; border-radius: var(--radius-md); font-size: 0.85rem; font-weight: 600; box-shadow: var(--shadow-glow-teal);"
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
                        d="M12 4v16m8-8H4"
                    /></svg
                >
                New Case
            </button>
        </div>

        <!-- Stats -->
        <div class="grid grid-cols-4 gap-4 animate-fade-up stagger-1">
            {#each [{ label: "Total Active", val: stats.total, color: "var(--n-100)", border: "" }, { label: "Ready to Pack", val: stats.ready, color: "var(--status-green)", border: "border-left: 3px solid var(--status-green);" }, { label: "Queries", val: stats.queries, color: "var(--status-amber)", border: "border-left: 3px solid var(--status-amber);" }, { label: "Critical", val: stats.critical, color: "var(--status-red)", border: "border-left: 3px solid var(--status-red);" }] as s}
                <div class="premium-card p-6" style={s.border}>
                    <div
                        style="font-size: 0.6rem; color: var(--n-500); font-weight: 700; text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 0.75rem;"
                    >
                        {s.label}
                    </div>
                    <div
                        style="font-size: 2.5rem; font-weight: 800; color: {s.color}; letter-spacing: -0.04em; line-height: 1; font-family: 'Space Grotesk', sans-serif;"
                    >
                        {s.val}
                    </div>
                </div>
            {/each}
        </div>

        <!-- Table -->
        <div
            class="animate-fade-up stagger-2"
            style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-xl); overflow: hidden; min-height: 300px;"
        >
            {#if loading}
                <div
                    class="flex items-center justify-center"
                    style="height: 16rem; color: var(--n-500);"
                >
                    <div class="flex items-center gap-3">
                        <div
                            style="width: 2rem; height: 2rem; border-radius: 50%; border: 3px solid var(--border-subtle); border-top-color: var(--teal-400); animation: spin 0.8s linear infinite;"
                        ></div>
                        <span style="font-weight: 500;">Loading cases...</span>
                    </div>
                </div>
            {:else if cases.length === 0}
                <div
                    class="flex flex-col items-center justify-center"
                    style="padding: 4rem 2rem; text-align: center;"
                >
                    <div
                        style="width: 5rem; height: 5rem; border-radius: var(--radius-xl); background: rgba(45, 212, 191, 0.08); border: 2px dashed rgba(45, 212, 191, 0.2); display: flex; align-items: center; justify-content: center; margin-bottom: 1.5rem; animation: dropZonePulse 2s ease infinite;"
                    >
                        <svg
                            style="width: 2rem; height: 2rem; color: var(--teal-400);"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            stroke-width="1.5"
                            ><path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                            /></svg
                        >
                    </div>
                    <h3
                        style="font-size: 1.25rem; font-weight: 700; color: var(--n-100); margin-bottom: 0.5rem;"
                    >
                        No cases yet
                    </h3>
                    <p
                        style="font-size: 0.85rem; color: var(--n-500); max-width: 24rem; margin-bottom: 1.5rem;"
                    >
                        Drop a case folder to begin. Pramana AI auto-detects
                        patient details from clinical documents.
                    </p>
                    <button
                        on:click={() => {
                            showUploadModal = true;
                        }}
                        style="display: flex; align-items: center; gap: 0.5rem; padding: 0.75rem 1.5rem; background: linear-gradient(135deg, var(--teal-500), var(--teal-600)); color: white; border-radius: var(--radius-md); font-size: 0.9rem; font-weight: 600; box-shadow: var(--shadow-glow-teal);"
                    >
                        Upload First Case
                    </button>
                </div>
            {:else}
                <table
                    class="w-full text-left"
                    style="border-collapse: collapse; font-family: 'DM Sans', sans-serif;"
                >
                    <thead>
                        <tr
                            style="border-bottom: 1px solid var(--border-subtle);"
                        >
                            {#each ["Case ID", "Lane", "Patient & Payer", "Score", "Status", ""] as h, i}
                                <th
                                    style="padding: 1rem 1.5rem; font-size: 0.6rem; font-weight: 700; color: var(--n-500); text-transform: uppercase; letter-spacing: 0.15em; {i ===
                                    3
                                        ? 'text-align: center; width: 6rem;'
                                        : ''}{i === 5
                                        ? 'text-align: right; width: 6rem;'
                                        : ''}">{h}</th
                                >
                            {/each}
                        </tr>
                    </thead>
                    <tbody>
                        {#each cases as kase}
                            <tr
                                class="interactive-row group"
                                style="cursor: pointer; border-bottom: 1px solid rgba(148,163,184,0.06);"
                                on:click={() => goto(`/cases/${kase.id}`)}
                                on:keydown={(e) => {
                                    if (e.key === "Enter")
                                        goto(`/cases/${kase.id}`);
                                }}
                                tabindex="0"
                            >
                                <td
                                    style="padding: 1rem 1.5rem; position: relative;"
                                >
                                    <div
                                        class="status-indicator-bar"
                                        style="background: {getBandColor(
                                            kase.band || '',
                                            kase.status || '',
                                        )}; opacity: {confirmingDelete ===
                                        kase.id
                                            ? 0
                                            : 1};"
                                    ></div>
                                    <span
                                        style="font-family: 'Space Grotesk', monospace; font-size: 0.85rem; font-weight: 600; color: var(--n-200);"
                                        >{kase.case_number}</span
                                    >
                                </td>
                                <td style="padding: 1rem 1.5rem;">
                                    <span
                                        style="display: inline-flex; padding: 0.2rem 0.6rem; border-radius: var(--radius-full); font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
                                    {kase.lane === 'cardio'
                                            ? 'background: rgba(248,113,113,0.1); color: var(--status-red); border: 1px solid rgba(248,113,113,0.15);'
                                            : 'background: rgba(96,165,250,0.1); color: #60A5FA; border: 1px solid rgba(96,165,250,0.15);'}"
                                    >
                                        {kase.lane.toUpperCase()}
                                    </span>
                                </td>
                                <td style="padding: 1rem 1.5rem;">
                                    <div class="flex flex-col">
                                        <span
                                            style="font-weight: 600; color: var(--n-100); font-size: 0.9rem;"
                                            >{kase.patient}</span
                                        >
                                        <span
                                            style="font-size: 0.75rem; color: var(--n-500);"
                                            >{kase.payer_id}</span
                                        >
                                    </div>
                                </td>
                                <td
                                    style="padding: 1rem 1.5rem; text-align: center;"
                                >
                                    <span
                                        style="font-family: 'Space Grotesk', sans-serif; font-size: 1.25rem; font-weight: 700; color: {getBandColor(
                                            kase.band || '',
                                            kase.status || '',
                                        )};">{kase.score}</span
                                    >
                                </td>
                                <td style="padding: 1rem 1.5rem;">
                                    <div class="flex items-center gap-2">
                                        <span
                                            style="width: 0.5rem; height: 0.5rem; border-radius: 50%; background: {getBandColor(
                                                kase.band || '',
                                                kase.status || '',
                                            )};"
                                        ></span>
                                        <span
                                            style="font-size: 0.8rem; color: var(--n-400);"
                                            >{kase.status === "closed"
                                                ? "Sent to Payer"
                                                : kase.status?.replace(
                                                      "_",
                                                      " ",
                                                  )}</span
                                        >
                                    </div>
                                </td>
                                <td
                                    style="padding: 1rem 1.5rem; text-align: right;"
                                >
                                    <div
                                        class="flex items-center justify-end gap-2"
                                    >
                                        <a
                                            href={`/cases/${kase.id}`}
                                            style="font-size: 0.8rem; font-weight: 600; color: var(--teal-400); opacity: 0; transition: opacity 0.2s;"
                                            class="group-hover-link">Open →</a
                                        >
                                        {#if confirmingDelete === kase.id}
                                            <button
                                                on:click|stopPropagation={() =>
                                                    handleDeleteCase(kase.id)}
                                                style="padding: 0.3rem 0.6rem; background: rgba(248,113,113,0.15); color: var(--status-red); font-size: 0.65rem; font-weight: 700; border-radius: var(--radius-sm); border: 1px solid rgba(248,113,113,0.3);"
                                                >Confirm</button
                                            >
                                        {:else}
                                            <button
                                                on:click|stopPropagation={() =>
                                                    (confirmingDelete =
                                                        kase.id)}
                                                aria-label="Delete"
                                                style="padding: 0.35rem; color: var(--n-600); opacity: 0; transition: all 0.2s; border-radius: var(--radius-sm);"
                                                class="group-hover-link"
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
                                                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                                                    /></svg
                                                >
                                            </button>
                                        {/if}
                                    </div>
                                </td>
                            </tr>
                        {/each}
                    </tbody>
                </table>
            {/if}
        </div>
    </div>

    <!-- Doctor View -->
{:else if $currentRole === "doctor"}
    <div class="flex flex-col gap-6" style="max-width: 60rem; margin: 0 auto;">
        <div class="animate-fade-up">
            <h1
                style="font-size: 1.75rem; font-weight: 700; color: var(--n-50); letter-spacing: -0.03em; margin-bottom: 0.25rem;"
            >
                Pending Queries
            </h1>
            <p style="font-size: 0.85rem; color: var(--n-500);">
                Insurance queries awaiting your clinical justification.
            </p>
        </div>

        {#if loading}
            <div
                class="flex items-center justify-center"
                style="height: 20rem; color: var(--n-500);"
            >
                <div
                    style="width: 2rem; height: 2rem; border-radius: 50%; border: 3px solid var(--border-subtle); border-top-color: var(--teal-400); animation: spin 0.8s linear infinite;"
                ></div>
            </div>
        {:else}
            {@const queryCases = cases.filter(
                (c) => c.band === "AMBER" || c.band === "RED",
            )}
            {#if queryCases.length === 0}
                <div
                    class="premium-card p-8 flex flex-col items-center justify-center animate-fade-up"
                    style="text-align: center;"
                >
                    <div
                        style="width: 4rem; height: 4rem; border-radius: 50%; background: rgba(52,211,153,0.08); display: flex; align-items: center; justify-content: center; margin-bottom: 1rem;"
                    >
                        <svg
                            style="width: 2rem; height: 2rem; color: var(--status-green);"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            stroke-width="2"
                            ><path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M5 13l4 4L19 7"
                            /></svg
                        >
                    </div>
                    <h3
                        style="font-size: 1.1rem; font-weight: 700; color: var(--n-100); margin-bottom: 0.25rem;"
                    >
                        All clear, Doctor
                    </h3>
                    <p style="font-size: 0.8rem; color: var(--n-500);">
                        No pending queries need your attention right now.
                    </p>
                </div>
            {:else}
                <div class="space-y-4">
                    {#each queryCases as kase, i}
                        <div
                            class="premium-card animate-fade-up stagger-{i + 1}"
                            style="padding: 1.5rem; display: flex; align-items: center; gap: 1.5rem; border-left: 3px solid {getBandColor(
                                kase.band || '',
                                kase.status || '',
                            )};"
                        >
                            <div
                                style="width: 3.5rem; height: 3.5rem; border-radius: var(--radius-lg); background: var(--bg-surface); display: flex; align-items: center; justify-content: center; flex-shrink: 0;"
                            >
                                <span
                                    style="font-family: 'Space Grotesk'; font-size: 1.25rem; font-weight: 700; color: {getBandColor(
                                        kase.band || '',
                                        kase.status || '',
                                    )};">{kase.score}</span
                                >
                            </div>
                            <div style="flex: 1; min-width: 0;">
                                <div
                                    class="flex items-center gap-2"
                                    style="margin-bottom: 0.25rem;"
                                >
                                    <span
                                        style="font-weight: 700; color: var(--n-100); font-size: 1rem;"
                                        >{kase.patient}</span
                                    >
                                    <span
                                        style="padding: 0.1rem 0.5rem; background: rgba(45,212,191,0.1); color: {getBandColor(
                                            kase.band || '',
                                            kase.status || '',
                                        )}; font-size: 0.55rem; font-weight: 700; border-radius: var(--radius-full); text-transform: uppercase; letter-spacing: 0.1em;"
                                        >{kase.band || "NEW"}</span
                                    >
                                </div>
                                <p
                                    style="font-size: 0.8rem; color: var(--n-500);"
                                >
                                    {kase.case_number} · {kase.lane
                                        .charAt(0)
                                        .toUpperCase() + kase.lane.slice(1)} · {kase.payer_id}
                                </p>
                                <p
                                    style="font-size: 0.75rem; color: var(--n-400); font-style: italic; margin-top: 0.35rem;"
                                >
                                    {kase.band === "RED"
                                        ? "Critical issues detected — missing documents or identity mismatch."
                                        : "Gaps in clinical evidence — your input can resolve this."}
                                </p>
                            </div>
                            <a
                                href={`/cases/${kase.id}`}
                                style="display: flex; align-items: center; gap: 0.5rem; padding: 0.6rem 1.25rem; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); font-size: 0.8rem; font-weight: 600; color: var(--teal-400); white-space: nowrap; text-decoration: none; transition: all 0.2s;"
                            >
                                Review & Respond →
                            </a>
                        </div>
                    {/each}
                </div>
            {/if}
        {/if}
    </div>

    <!-- Patient View -->
{:else if $currentRole === "patient"}
    <div class="flex flex-col gap-6" style="max-width: 40rem; margin: 0 auto;">
        <div
            class="animate-fade-up"
            style="text-align: center; padding-top: 1rem;"
        >
            <div
                style="width: 4rem; height: 4rem; margin: 0 auto 1rem; border-radius: 50%; background: linear-gradient(135deg, var(--teal-500), var(--teal-600)); display: flex; align-items: center; justify-content: center; box-shadow: var(--shadow-glow-teal);"
            >
                <svg
                    style="width: 2rem; height: 2rem; color: white;"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    stroke-width="2"
                    ><path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                    /></svg
                >
            </div>
            <h1
                style="font-size: 1.75rem; font-weight: 700; color: var(--n-50); letter-spacing: -0.03em;"
            >
                Your Claim Status
            </h1>
            <p
                style="font-size: 0.85rem; color: var(--n-500); margin-top: 0.25rem;"
            >
                Real-time updates on your insurance claim progress.
            </p>
        </div>

        {#if loading}
            <div
                class="flex items-center justify-center"
                style="height: 10rem; color: var(--n-500);"
            >
                <div
                    style="width: 2rem; height: 2rem; border-radius: 50%; border: 3px solid var(--border-subtle); border-top-color: var(--teal-400); animation: spin 0.8s linear infinite;"
                ></div>
            </div>
        {:else if cases.length === 0}
            <div
                class="premium-card p-8 animate-fade-up"
                style="text-align: center;"
            >
                <p style="color: var(--n-400);">
                    No claims found for your account.
                </p>
            </div>
        {:else}
            {@const kase = cases[0]}
            <!-- Main Claim Card -->
            <div
                class="premium-card animate-fade-up stagger-1"
                style="padding: 2rem; text-align: center; overflow: hidden; position: relative;"
            >
                <div
                    style="position: absolute; top: -3rem; right: -3rem; width: 10rem; height: 10rem; border-radius: 50%; background: {getBandColor(
                        kase.band || '',
                        kase.status || '',
                    )}; opacity: 0.04; filter: blur(50px);"
                ></div>
                <div style="margin-bottom: 1rem;">
                    <span
                        style="padding: 0.25rem 1rem; background: rgba(45,212,191,0.1); color: {getBandColor(
                            kase.band || '',
                            kase.status || '',
                        )}; font-size: 0.65rem; font-weight: 700; border-radius: var(--radius-full); text-transform: uppercase; letter-spacing: 0.1em; border: 1px solid rgba(45,212,191,0.2);"
                    >
                        {kase.band === "GREEN"
                            ? "Ready for Submission"
                            : kase.band === "AMBER"
                              ? "Additional Info Needed"
                              : "Action Required"}
                    </span>
                </div>

                <!-- Score -->
                <div
                    style="position: relative; display: inline-block; margin-bottom: 1.5rem;"
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
                            stroke={getBandColor(
                                kase.band || "",
                                kase.status || "",
                            )}
                            stroke-width="10"
                            fill="transparent"
                            stroke-dasharray="452.4"
                            stroke-dashoffset={452.4 -
                                (452.4 * (kase.score || 0)) / 100}
                            stroke-linecap="round"
                            style="transition: stroke-dashoffset 1.5s cubic-bezier(0.34, 1.56, 0.64, 1); filter: drop-shadow(0 0 6px {getBandColor(
                                kase.band || '',
                                kase.status || '',
                            )});"
                        />
                    </svg>
                    <div
                        style="position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;"
                    >
                        <span
                            style="font-size: 3rem; font-weight: 800; color: var(--n-50); letter-spacing: -0.04em; line-height: 1; font-family: 'Space Grotesk';"
                            >{kase.score}</span
                        >
                        <span
                            style="font-size: 0.55rem; color: var(--n-500); font-weight: 700; text-transform: uppercase; letter-spacing: 0.15em;"
                            >Claim Ready</span
                        >
                    </div>
                </div>

                <h2
                    style="font-size: 1.25rem; font-weight: 700; color: var(--n-100); margin-bottom: 0.5rem;"
                >
                    {kase.band === "GREEN"
                        ? "🎉 Your claim documents are complete!"
                        : kase.band === "AMBER"
                          ? "Almost there — a few items needed"
                          : "⚠️ Important: Action needed on your claim"}
                </h2>
                <p
                    style="font-size: 0.9rem; color: var(--n-400); max-width: 28rem; margin: 0 auto; line-height: 1.6;"
                >
                    {kase.band === "GREEN"
                        ? "All your medical records have been collected and verified. Your claim has been submitted to " +
                          kase.payer_id +
                          " for processing. Expected turnaround: 5-7 business days."
                        : kase.band === "AMBER"
                          ? "Your medical records are mostly complete, but your hospital is gathering a few more documents. No action is needed from your side — we'll notify you once everything is ready."
                          : "There's an issue with some documents in your claim. The hospital team is working on resolving it. If you have any additional medical records, please bring them during your next visit."}
                </p>
            </div>

            <!-- Info cards -->
            <div class="grid grid-cols-2 gap-4 animate-fade-up stagger-2">
                <div class="premium-card p-5" style="text-align: center;">
                    <div
                        style="font-size: 0.6rem; color: var(--n-500); font-weight: 700; text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 0.5rem;"
                    >
                        Procedure
                    </div>
                    <div
                        style="font-size: 1rem; font-weight: 700; color: var(--n-200);"
                    >
                        {kase.lane === "cardio"
                            ? "Cardiac Stent (PCI)"
                            : "Joint Replacement"}
                    </div>
                </div>
                <div class="premium-card p-5" style="text-align: center;">
                    <div
                        style="font-size: 0.6rem; color: var(--n-500); font-weight: 700; text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 0.5rem;"
                    >
                        Insurer
                    </div>
                    <div
                        style="font-size: 1rem; font-weight: 700; color: var(--n-200);"
                    >
                        {kase.payer_id}
                    </div>
                </div>
            </div>

            <div
                class="premium-card p-5 animate-fade-up stagger-3"
                style="background: rgba(45,212,191,0.04); border: 1px solid rgba(45,212,191,0.15);"
            >
                <div class="flex items-start gap-3">
                    <svg
                        style="width: 1.25rem; height: 1.25rem; color: var(--teal-400); flex-shrink: 0; margin-top: 0.1rem;"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        stroke-width="2"
                        ><path
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        /></svg
                    >
                    <div>
                        <p
                            style="font-size: 0.8rem; font-weight: 600; color: var(--teal-400); margin-bottom: 0.25rem;"
                        >
                            What happens next?
                        </p>
                        <p
                            style="font-size: 0.8rem; color: var(--n-400); line-height: 1.5;"
                        >
                            Your hospital's TPA desk is managing your claim
                            using AI-powered document verification. All your
                            medical data stays on the hospital's local server —
                            it is never uploaded to the cloud. You can check
                            this page anytime for updates.
                        </p>
                    </div>
                </div>
            </div>
        {/if}
    </div>
{/if}

<!-- Smart Upload Modal -->
{#if showUploadModal}
    <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
            style="position: absolute; inset: 0; background: rgba(6, 14, 26, 0.8); backdrop-filter: blur(8px);"
            on:click={closeModal}
            on:keydown={(e) => e.key === "Escape" && closeModal()}
            role="button"
            tabindex="-1"
            aria-label="Close"
        ></div>
        <div
            style="position: relative; width: 100%; max-width: 28rem; background: var(--bg-card); border-radius: var(--radius-2xl); box-shadow: var(--shadow-xl); border: 1px solid var(--border-subtle); overflow: hidden;"
        >
            <div class="p-6">
                {#if uploadPhase === "drop"}
                    <h2
                        style="font-size: 1.25rem; font-weight: 700; color: var(--n-50); margin-bottom: 0.5rem;"
                    >
                        Upload Case Folder
                    </h2>
                    <p
                        style="font-size: 0.75rem; color: var(--n-500); margin-bottom: 1.5rem;"
                    >
                        Drop a patient's case folder. Pramana AI will
                        auto-detect patient details.
                    </p>
                    <div
                        on:drop={handleDropFiles}
                        on:dragover|preventDefault
                        role="region"
                        style="border: 2px dashed var(--border-subtle); border-radius: var(--radius-lg); padding: 3rem 2rem; text-align: center; transition: all 0.3s; cursor: pointer; position: relative;"
                    >
                        <input
                            type="file"
                            multiple
                            webkitdirectory
                            on:change={handleFolderSelect}
                            style="position: absolute; inset: 0; opacity: 0; cursor: pointer;"
                        />
                        <svg
                            style="width: 3rem; height: 3rem; color: var(--teal-400); margin: 0 auto 1rem;"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            stroke-width="1.5"
                            ><path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                            /></svg
                        >
                        <p
                            style="font-size: 0.9rem; color: var(--n-300); font-weight: 600; margin-bottom: 0.25rem;"
                        >
                            Drop case folder here
                        </p>
                        <p style="font-size: 0.75rem; color: var(--n-500);">
                            or <span style="color: var(--teal-400);"
                                >click to browse</span
                            > (PDFs & images)
                        </p>
                    </div>
                {:else if uploadPhase === "scanning"}
                    <div
                        class="flex flex-col items-center justify-center"
                        style="padding: 3rem 2rem; text-align: center;"
                    >
                        <div
                            style="width: 3rem; height: 3rem; border-radius: 50%; border: 3px solid var(--border-subtle); border-top-color: var(--teal-400); animation: spin 0.8s linear infinite; margin-bottom: 1.5rem;"
                        ></div>
                        <h2
                            style="font-size: 1.1rem; font-weight: 700; color: var(--n-100); margin-bottom: 0.5rem;"
                        >
                            Scanning first document...
                        </h2>
                        <p style="font-size: 0.8rem; color: var(--n-500);">
                            Extracting patient name, department, and payer.
                        </p>
                    </div>
                {:else if uploadPhase === "confirm"}
                    <h2
                        style="font-size: 1.25rem; font-weight: 700; color: var(--n-50); margin-bottom: 1.25rem;"
                    >
                        Confirm Case Details
                    </h2>
                    <div class="space-y-3">
                        <div>
                            <div
                                class="flex items-center gap-2"
                                style="margin-bottom: 0.35rem;"
                            >
                                {#if scannedMeta.patient_name}<span
                                        style="color: var(--status-green); font-size: 0.7rem;"
                                        >✓ Auto-detected</span
                                    >{:else}<span
                                        style="color: var(--n-500); font-size: 0.7rem;"
                                        >Manual entry</span
                                    >{/if}
                            </div>
                            <label
                                for="patientName"
                                style="display: block; font-size: 0.65rem; font-weight: 700; color: var(--n-500); text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 0.25rem;"
                                >Patient Name</label
                            >
                            <input
                                id="patientName"
                                type="text"
                                bind:value={scannedMeta.patient_name}
                                placeholder="Patient name"
                                style="width: 100%; padding: 0.6rem 0.75rem; background: var(--bg-surface); border: 1px solid {scannedMeta.patient_name
                                    ? 'rgba(52,211,153,0.3)'
                                    : 'var(--border-subtle)'}; border-radius: var(--radius-md); color: var(--n-100); font-size: 0.875rem; outline: none;"
                            />
                        </div>
                        <div class="grid grid-cols-2 gap-3">
                            <div>
                                <label
                                    for="caseLane"
                                    style="display: block; font-size: 0.65rem; font-weight: 700; color: var(--n-500); text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 0.25rem;"
                                    >Lane</label
                                >
                                <select
                                    id="caseLane"
                                    bind:value={scannedMeta.lane}
                                    style="width: 100%; padding: 0.6rem 0.75rem; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); color: var(--n-100); font-size: 0.875rem; outline: none;"
                                >
                                    <option value="cardio">Cardiology</option>
                                    <option value="ortho">Orthopedics</option>
                                </select>
                            </div>
                            <div>
                                <label
                                    for="casePayer"
                                    style="display: block; font-size: 0.65rem; font-weight: 700; color: var(--n-500); text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 0.25rem;"
                                    >Payer</label
                                >
                                <input
                                    id="casePayer"
                                    type="text"
                                    bind:value={scannedMeta.payer}
                                    placeholder="Insurance"
                                    style="width: 100%; padding: 0.6rem 0.75rem; background: var(--bg-surface); border: 1px solid {scannedMeta.payer
                                        ? 'rgba(52,211,153,0.3)'
                                        : 'var(--border-subtle)'}; border-radius: var(--radius-md); color: var(--n-100); font-size: 0.875rem; outline: none;"
                                />
                            </div>
                        </div>
                        <div
                            style="padding: 0.75rem; background: var(--bg-surface); border-radius: var(--radius-md); border: 1px solid var(--border-subtle);"
                        >
                            <span
                                style="font-size: 0.7rem; font-weight: 700; color: var(--teal-400);"
                                >📄 {selectedFiles.length} documents</span
                            >
                            <span
                                style="font-size: 0.7rem; color: var(--n-500);"
                                >ready to upload</span
                            >
                        </div>
                    </div>
                    <div class="flex gap-3" style="margin-top: 1.5rem;">
                        <button
                            on:click={closeModal}
                            style="flex: 1; padding: 0.65rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); font-size: 0.85rem; font-weight: 600; color: var(--n-400);"
                            >Cancel</button
                        >
                        <button
                            on:click={confirmUpload}
                            style="flex: 2; padding: 0.65rem; background: linear-gradient(135deg, var(--teal-500), var(--teal-600)); color: white; border-radius: var(--radius-lg); font-size: 0.85rem; font-weight: 700; box-shadow: var(--shadow-glow-teal);"
                            >Confirm & Upload</button
                        >
                    </div>
                {:else if uploadPhase === "uploading"}
                    <div
                        class="flex flex-col items-center justify-center"
                        style="padding: 2rem;"
                    >
                        <h2
                            style="font-size: 1.1rem; font-weight: 700; color: var(--n-100); margin-bottom: 1rem;"
                        >
                            Uploading {selectedFiles.length} documents...
                        </h2>
                        <div
                            style="width: 100%; height: 6px; background: var(--bg-surface); border-radius: var(--radius-full); overflow: hidden; margin-bottom: 0.5rem;"
                        >
                            <div
                                style="height: 100%; background: linear-gradient(90deg, var(--teal-500), var(--teal-400)); width: {uploadProgress}%; border-radius: var(--radius-full); transition: width 0.3s;"
                            ></div>
                        </div>
                        <span
                            style="font-size: 0.8rem; color: var(--teal-400); font-weight: 600;"
                            >{uploadProgress}%</span
                        >
                    </div>
                {/if}
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
    .interactive-row:hover .group-hover-link {
        opacity: 1 !important;
    }
</style>
