<script lang="ts">
    // Redirect to main dashboard for /cases route
    import { goto } from "$app/navigation";
    import { onMount } from "svelte";

    onMount(() => {
        goto("/");
    });
</script>

<div class="flex items-center justify-center h-full text-slate-400">
    Redirecting to Case List...
</div>
