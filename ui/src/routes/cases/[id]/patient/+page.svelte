<script lang="ts">
    import { onMount } from "svelte";
    export let data: { caseId: string };

    let caseData: any = null;
    let documents: any[] = [];
    let timeline: any[] = [];
    let loading = true;

    onMount(async () => {
        try {
            const res = await fetch(`/api/cases/${data.caseId}`);
            if (res.ok) {
                const c = await res.json();
                caseData = {
                    ...c,
                    patient: c.patient_alias || "Patient",
                    score: c.readiness_score || 0,
                    band: c.readiness_band || null,
                };
            }
            // Load documents
            const filesRes = await fetch(
                `/api/analysis/${data.caseId}/results`,
            );
            if (filesRes.ok) {
                const results = await filesRes.json();
                documents = results.files || [];
            }
            // Load audit timeline
            const auditRes = await fetch(`/api/cases/${data.caseId}/audit`);
            if (auditRes.ok) {
                timeline = await auditRes.json();
            }
        } catch (e) {
            console.error(e);
        } finally {
            loading = false;
        }
    });

    function getStatusLabel(status: string) {
        const map: Record<string, string> = {
            new: "Documents Being Collected",
            in_review: "AI Verification Complete",
            analyzed: "AI Verification Complete",
            query_drafted: "Response Drafted",
            pack_generated: "Evidence Pack Ready",
            closed: "Submitted to Insurer",
        };
        return map[status] || "Processing";
    }

    function getStatusStep(status: string): number {
        const order = [
            "new",
            "in_review",
            "query_drafted",
            "pack_generated",
            "closed",
        ];
        const idx = order.indexOf(status);
        return idx >= 0 ? idx : 0;
    }

    function getBandColor(band: string) {
        if (band === "GREEN") return "#2dd4bf";
        if (band === "AMBER") return "#fbbf24";
        return "#f87171";
    }

    function formatDate(d: string) {
        if (!d) return "";
        return new Date(d).toLocaleDateString("en-IN", {
            day: "numeric",
            month: "short",
            year: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    }
</script>

<div
    style="max-width: 480px; margin: 0 auto; padding: 1.5rem 1rem; min-height: 100vh; background: var(--bg-base, #0b1120); color: #e2e8f0; font-family: 'Inter', system-ui, sans-serif;"
>
    {#if loading}
        <div
            style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 60vh; gap: 1rem;"
        >
            <div
                style="width: 2.5rem; height: 2.5rem; border-radius: 50%; border: 3px solid rgba(148,163,184,0.15); border-top-color: #2dd4bf; animation: spin 0.8s linear infinite;"
            ></div>
            <p style="color: #64748b; font-size: 0.85rem;">
                Loading your claim...
            </p>
        </div>
    {:else if !caseData}
        <div style="text-align: center; padding: 3rem 1rem;">
            <p style="font-size: 1.5rem; margin-bottom: 0.5rem;">🔒</p>
            <h2
                style="font-size: 1.1rem; font-weight: 700; color: #e2e8f0; margin-bottom: 0.5rem;"
            >
                Claim Not Found
            </h2>
            <p style="font-size: 0.8rem; color: #64748b;">
                This link may have expired or the claim ID is invalid.
            </p>
        </div>
    {:else}
        <!-- Header -->
        <div style="text-align: center; margin-bottom: 2rem;">
            <div
                style="display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.3rem 0.8rem; background: rgba(45,212,191,0.08); border: 1px solid rgba(45,212,191,0.15); border-radius: 999px; margin-bottom: 1rem;"
            >
                <span
                    style="font-size: 0.6rem; font-weight: 700; color: #2dd4bf; letter-spacing: 0.1em; text-transform: uppercase;"
                    >🏥 Pramana Patient Portal</span
                >
            </div>
            <h1
                style="font-size: 1.3rem; font-weight: 800; color: #f1f5f9; margin-bottom: 0.25rem;"
            >
                Your Claim Status
            </h1>
            <p style="font-size: 0.8rem; color: #64748b;">
                Claim #{caseData.case_number ||
                    caseData.id?.slice(0, 8).toUpperCase()}
            </p>
        </div>

        <!-- Status Card -->
        <div
            style="background: rgba(15,23,42,0.6); border: 1px solid rgba(148,163,184,0.1); border-radius: 1rem; padding: 1.5rem; margin-bottom: 1.25rem; backdrop-filter: blur(10px);"
        >
            <div
                style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;"
            >
                <span
                    style="font-size: 0.65rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.1em;"
                    >Current Status</span
                >
                <span
                    style="padding: 0.2rem 0.6rem; border-radius: 999px; font-size: 0.6rem; font-weight: 700; color: white; background: {getBandColor(
                        caseData.band,
                    )}; text-transform: uppercase;"
                >
                    {caseData.band || "PENDING"}
                </span>
            </div>
            <p
                style="font-size: 1rem; font-weight: 600; color: #f1f5f9; margin-bottom: 1rem;"
            >
                {getStatusLabel(caseData.status)}
            </p>

            <!-- Progress Steps -->
            <div style="display: flex; gap: 0.25rem; margin-bottom: 0.5rem;">
                {#each ["Uploaded", "Verified", "Drafted", "Packed", "Submitted"] as step, i}
                    <div
                        style="flex: 1; height: 4px; border-radius: 2px; background: {getStatusStep(
                            caseData.status,
                        ) >= i
                            ? '#2dd4bf'
                            : 'rgba(148,163,184,0.15)'}; transition: background 0.5s;"
                    ></div>
                {/each}
            </div>
            <div style="display: flex; justify-content: space-between;">
                {#each ["Uploaded", "Verified", "Drafted", "Packed", "Submitted"] as step, i}
                    <span
                        style="font-size: 0.5rem; color: {getStatusStep(
                            caseData.status,
                        ) >= i
                            ? '#2dd4bf'
                            : '#475569'};">{step}</span
                    >
                {/each}
            </div>
        </div>

        <!-- Score Circle -->
        {#if caseData.score}
            <div
                style="background: rgba(15,23,42,0.6); border: 1px solid rgba(148,163,184,0.1); border-radius: 1rem; padding: 1.5rem; margin-bottom: 1.25rem; text-align: center;"
            >
                <p
                    style="font-size: 0.65rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 1rem;"
                >
                    AI Readiness Score
                </p>
                <div
                    style="position: relative; display: inline-block; margin-bottom: 1rem;"
                >
                    <svg
                        style="width: 8rem; height: 8rem; transform: rotate(-90deg);"
                    >
                        <circle
                            cx="64"
                            cy="64"
                            r="56"
                            stroke="rgba(148,163,184,0.1)"
                            stroke-width="8"
                            fill="transparent"
                        />
                        <circle
                            cx="64"
                            cy="64"
                            r="56"
                            stroke={getBandColor(caseData.band)}
                            stroke-width="8"
                            fill="transparent"
                            stroke-dasharray="351.9"
                            stroke-dashoffset={351.9 -
                                (351.9 * caseData.score) / 100}
                            stroke-linecap="round"
                            style="transition: stroke-dashoffset 1.5s ease; filter: drop-shadow(0 0 6px {getBandColor(
                                caseData.band,
                            )});"
                        />
                    </svg>
                    <div
                        style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;"
                    >
                        <span
                            style="font-size: 2rem; font-weight: 800; color: #f1f5f9; letter-spacing: -0.03em;"
                            >{caseData.score}</span
                        >
                        <span
                            style="display: block; font-size: 0.55rem; color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em;"
                            >/ 100</span
                        >
                    </div>
                </div>
                <div
                    style="display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.3rem 0.7rem; background: rgba(45,212,191,0.06); border: 1px solid rgba(45,212,191,0.1); border-radius: 999px;"
                >
                    <span style="font-size: 0.6rem;">🧠</span>
                    <span
                        style="font-size: 0.6rem; color: #2dd4bf; font-weight: 600;"
                        >Verified by Pramana AI</span
                    >
                </div>
            </div>
        {/if}

        <!-- Your Documents -->
        <div
            style="background: rgba(15,23,42,0.6); border: 1px solid rgba(148,163,184,0.1); border-radius: 1rem; padding: 1.25rem; margin-bottom: 1.25rem;"
        >
            <div
                style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem;"
            >
                <span
                    style="font-size: 0.65rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.1em;"
                    >📄 Your Documents</span
                >
                <span style="font-size: 0.65rem; color: #64748b;"
                    >{documents.length} file{documents.length !== 1
                        ? "s"
                        : ""}</span
                >
            </div>
            {#if documents.length === 0}
                <p
                    style="font-size: 0.8rem; color: #475569; text-align: center; padding: 1rem;"
                >
                    No documents uploaded yet.
                </p>
            {:else}
                {#each documents as doc}
                    <div
                        style="display: flex; align-items: center; gap: 0.6rem; padding: 0.6rem 0; border-bottom: 1px solid rgba(148,163,184,0.06);"
                    >
                        <div
                            style="width: 2rem; height: 2rem; border-radius: 0.5rem; background: rgba(45,212,191,0.08); display: flex; align-items: center; justify-content: center;"
                        >
                            <span style="font-size: 0.7rem;">📎</span>
                        </div>
                        <div style="flex: 1; min-width: 0;">
                            <p
                                style="font-size: 0.8rem; color: #e2e8f0; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"
                            >
                                {doc.filename || "Document"}
                            </p>
                            <p style="font-size: 0.6rem; color: #64748b;">
                                {doc.doc_type
                                    ?.replace(/_/g, " ")
                                    ?.replace(/\b\w/g, (l) =>
                                        l.toUpperCase(),
                                    ) || "Processing..."}
                            </p>
                        </div>
                        <span style="font-size: 0.7rem; color: #2dd4bf;">✓</span
                        >
                    </div>
                {/each}
            {/if}
        </div>

        <!-- Key Info -->
        <div
            style="background: rgba(15,23,42,0.6); border: 1px solid rgba(148,163,184,0.1); border-radius: 1rem; padding: 1.25rem; margin-bottom: 1.25rem;"
        >
            <span
                style="font-size: 0.65rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.1em; display: block; margin-bottom: 0.75rem;"
                >ℹ️ Claim Details</span
            >
            <div
                style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;"
            >
                <div>
                    <p
                        style="font-size: 0.6rem; color: #475569; margin-bottom: 0.15rem;"
                    >
                        Patient
                    </p>
                    <p
                        style="font-size: 0.8rem; color: #e2e8f0; font-weight: 600;"
                    >
                        {caseData.patient}
                    </p>
                </div>
                <div>
                    <p
                        style="font-size: 0.6rem; color: #475569; margin-bottom: 0.15rem;"
                    >
                        Department
                    </p>
                    <p
                        style="font-size: 0.8rem; color: #e2e8f0; font-weight: 600; text-transform: capitalize;"
                    >
                        {caseData.lane}
                    </p>
                </div>
                <div>
                    <p
                        style="font-size: 0.6rem; color: #475569; margin-bottom: 0.15rem;"
                    >
                        Created
                    </p>
                    <p style="font-size: 0.75rem; color: #e2e8f0;">
                        {formatDate(caseData.created_at)}
                    </p>
                </div>
                <div>
                    <p
                        style="font-size: 0.6rem; color: #475569; margin-bottom: 0.15rem;"
                    >
                        Last Updated
                    </p>
                    <p style="font-size: 0.75rem; color: #e2e8f0;">
                        {formatDate(caseData.updated_at)}
                    </p>
                </div>
            </div>
        </div>

        <!-- AI Transparency Badge -->
        <div
            style="text-align: center; padding: 1.5rem 1rem; margin-bottom: 1rem;"
        >
            <div
                style="display: inline-flex; flex-direction: column; align-items: center; gap: 0.5rem; padding: 1rem 1.5rem; background: rgba(45,212,191,0.04); border: 1px solid rgba(45,212,191,0.1); border-radius: 1rem;"
            >
                <span style="font-size: 1.5rem;">🛡️</span>
                <p
                    style="font-size: 0.75rem; color: #2dd4bf; font-weight: 700;"
                >
                    AI-Verified Claim
                </p>
                <p
                    style="font-size: 0.6rem; color: #64748b; max-width: 240px; line-height: 1.4;"
                >
                    This claim was verified by Pramana Edge AI for document
                    completeness, scan quality, and policy compliance — all
                    processed locally on the hospital's infrastructure. No
                    patient data leaves this facility.
                </p>
            </div>
        </div>

        <!-- Footer -->
        <div
            style="text-align: center; padding: 1rem; border-top: 1px solid rgba(148,163,184,0.06);"
        >
            <p style="font-size: 0.6rem; color: #475569;">
                Pramana · Edge AI Claim Readiness · Zero Cloud
            </p>
        </div>
    {/if}
</div>

<style>
    @keyframes spin {
        to {
            transform: rotate(360deg);
        }
    }
</style>
