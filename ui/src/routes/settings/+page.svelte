<script lang="ts">
    // Settings & Admin Page

    let ollamaStatus = "connected";
    let ollamaEndpoint = "http://127.0.0.1:11434";
    let modelInstalled = true;
    let hospitalMode = true;
    let dataRoot = "C:\\AegisLocal\\data";
    let ocrEnabled = true;

    async function testOllama() {
        ollamaStatus = "testing";
        await new Promise((r) => setTimeout(r, 1500));
        ollamaStatus = "connected";
    }

    async function exportDiagnostics() {
        alert("Exporting diagnostics bundle...");
    }
</script>

<div class="max-w-4xl mx-auto">
    <div class="mb-6">
        <h1 class="text-2xl font-bold text-slate-800">Settings & Admin</h1>
        <p class="text-sm text-slate-500 mt-1">
            Configure Pramana Local for your environment
        </p>
    </div>

    <div class="space-y-6">
        <!-- Model Runtime -->
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm">
            <div class="p-5 border-b border-slate-100">
                <h3 class="font-semibold text-slate-800">Model Runtime</h3>
                <p class="text-sm text-slate-500 mt-1">
                    Configure local AI model connection
                </p>
            </div>

            <div class="p-5 space-y-4">
                <div class="flex items-center justify-between">
                    <div>
                        <div class="font-medium text-slate-700">
                            Ollama Status
                        </div>
                        <div class="text-sm text-slate-500">
                            Local LLM runtime
                        </div>
                    </div>
                    <div class="flex items-center gap-3">
                        {#if ollamaStatus === "connected"}
                            <span
                                class="flex items-center gap-1.5 px-3 py-1.5 bg-green-50 text-green-700 rounded-full text-sm font-medium"
                            >
                                <div
                                    class="w-2 h-2 rounded-full bg-green-500"
                                ></div>
                                Connected
                            </span>
                        {:else if ollamaStatus === "testing"}
                            <span
                                class="flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 text-amber-700 rounded-full text-sm font-medium"
                            >
                                <svg
                                    class="w-4 h-4 animate-spin"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                >
                                    <circle
                                        class="opacity-25"
                                        cx="12"
                                        cy="12"
                                        r="10"
                                        stroke="currentColor"
                                        stroke-width="4"
                                    ></circle>
                                    <path
                                        class="opacity-75"
                                        fill="currentColor"
                                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                                    ></path>
                                </svg>
                                Testing...
                            </span>
                        {:else}
                            <span
                                class="flex items-center gap-1.5 px-3 py-1.5 bg-red-50 text-red-700 rounded-full text-sm font-medium"
                            >
                                <div
                                    class="w-2 h-2 rounded-full bg-red-500"
                                ></div>
                                Disconnected
                            </span>
                        {/if}
                        <button
                            on:click={testOllama}
                            class="text-sm text-cyan-600 hover:underline"
                            >Test</button
                        >
                    </div>
                </div>

                <div>
                    <label
                        for="ollama-endpoint"
                        class="block text-sm font-medium text-slate-700 mb-1.5"
                        >Ollama Endpoint</label
                    >
                    <input
                        id="ollama-endpoint"
                        type="text"
                        bind:value={ollamaEndpoint}
                        class="w-full px-4 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                    />
                </div>

                <div
                    class="flex items-center justify-between py-3 border-t border-slate-100"
                >
                    <div>
                        <div class="font-medium text-slate-700">
                            Model: gemma3:4b
                        </div>
                        <div class="text-sm text-slate-500">
                            MedGemma-compatible local model
                        </div>
                    </div>
                    {#if modelInstalled}
                        <span
                            class="px-3 py-1.5 bg-green-50 text-green-700 rounded-full text-sm font-medium"
                            >Installed</span
                        >
                    {:else}
                        <button
                            class="px-4 py-2 bg-cyan-800 text-white rounded-lg text-sm font-medium hover:bg-cyan-900"
                        >
                            Install Model
                        </button>
                    {/if}
                </div>
            </div>
        </div>

        <!-- Storage -->
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm">
            <div class="p-5 border-b border-slate-100">
                <h3 class="font-semibold text-slate-800">Storage</h3>
                <p class="text-sm text-slate-500 mt-1">
                    Data and cache locations
                </p>
            </div>

            <div class="p-5 space-y-4">
                <div>
                    <label
                        for="data-root"
                        class="block text-sm font-medium text-slate-700 mb-1.5"
                        >Data Root Path</label
                    >
                    <div class="flex gap-2">
                        <input
                            id="data-root"
                            type="text"
                            bind:value={dataRoot}
                            class="flex-1 px-4 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500/50 font-mono"
                        />
                        <button
                            class="px-4 py-2 border border-slate-200 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-50"
                        >
                            Browse
                        </button>
                    </div>
                </div>

                <div class="grid grid-cols-3 gap-4 pt-2">
                    <div class="p-4 bg-slate-50 rounded-lg">
                        <div class="text-2xl font-bold text-slate-800">24</div>
                        <div
                            class="text-xs text-slate-500 uppercase tracking-wide"
                        >
                            Active Cases
                        </div>
                    </div>
                    <div class="p-4 bg-slate-50 rounded-lg">
                        <div class="text-2xl font-bold text-slate-800">
                            1.2 GB
                        </div>
                        <div
                            class="text-xs text-slate-500 uppercase tracking-wide"
                        >
                            Storage Used
                        </div>
                    </div>
                    <div class="p-4 bg-slate-50 rounded-lg">
                        <div class="text-2xl font-bold text-slate-800">598</div>
                        <div
                            class="text-xs text-slate-500 uppercase tracking-wide"
                        >
                            Audit Events
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Hospital Mode -->
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm">
            <div class="p-5 border-b border-slate-100">
                <h3 class="font-semibold text-slate-800">Security & Mode</h3>
            </div>

            <div class="p-5 space-y-4">
                <div class="flex items-center justify-between">
                    <div>
                        <div class="font-medium text-slate-700">
                            Hospital Mode
                        </div>
                        <div class="text-sm text-slate-500">
                            Locks updates, disables all network
                        </div>
                    </div>
                    <button
                        aria-label="Toggle Hospital Mode"
                        role="switch"
                        aria-checked={hospitalMode}
                        class="relative w-12 h-6 rounded-full transition-colors {hospitalMode
                            ? 'bg-cyan-600'
                            : 'bg-slate-300'}"
                        on:click={() => (hospitalMode = !hospitalMode)}
                    >
                        <div
                            class="absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow transition-transform {hospitalMode
                                ? 'translate-x-6'
                                : ''}"
                        ></div>
                    </button>
                </div>

                <div
                    class="flex items-center justify-between pt-3 border-t border-slate-100"
                >
                    <div>
                        <div class="font-medium text-slate-700">
                            OCR Processing
                        </div>
                        <div class="text-sm text-slate-500">
                            Enable for scanned documents
                        </div>
                    </div>
                    <button
                        aria-label="Toggle OCR Processing"
                        role="switch"
                        aria-checked={ocrEnabled}
                        class="relative w-12 h-6 rounded-full transition-colors {ocrEnabled
                            ? 'bg-cyan-600'
                            : 'bg-slate-300'}"
                        on:click={() => (ocrEnabled = !ocrEnabled)}
                    >
                        <div
                            class="absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow transition-transform {ocrEnabled
                                ? 'translate-x-6'
                                : ''}"
                        ></div>
                    </button>
                </div>
            </div>
        </div>

        <!-- Diagnostics -->
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm">
            <div class="p-5 border-b border-slate-100">
                <h3 class="font-semibold text-slate-800">Diagnostics</h3>
            </div>

            <div class="p-5">
                <button
                    on:click={exportDiagnostics}
                    class="px-4 py-2 border border-slate-200 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-50 flex items-center gap-2"
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
                            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                        />
                    </svg>
                    Export Debug Bundle
                </button>
                <p class="text-xs text-slate-400 mt-2">
                    Includes logs, versions, config (redacted), and index
                    metadata
                </p>
            </div>
        </div>

        <!-- Version Info -->
        <div class="text-center py-4 text-xs text-slate-400">
            <div>Pramana Local v1.0.0-hackathon</div>
            <div class="mt-1">Built with Pramana AI + MedASR from HAI-DEF</div>
        </div>
    </div>
</div>
