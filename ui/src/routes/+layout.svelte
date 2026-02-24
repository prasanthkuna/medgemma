<script lang="ts">
  import "../app.css";
  import { page } from "$app/stores";
  import { currentRole, type Role } from "$lib/stores/role";

  const roleConfig = {
    tpa: {
      label: "TPA Desk",
      icon: "M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z",
      navItems: [
        {
          label: "Cases",
          path: "/",
          pathMatch: ["/", "/cases"],
          icon: "M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z",
        },
        {
          label: "Batch Audit",
          path: "/batch",
          pathMatch: ["/batch"],
          icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
        },
        {
          label: "Policy Library",
          path: "/policies",
          pathMatch: ["/policies"],
          icon: "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253",
        },
        {
          label: "Settings",
          path: "/settings",
          pathMatch: ["/settings"],
          icon: "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z",
        },
      ],
    },
    doctor: {
      label: "Doctor",
      icon: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z",
      navItems: [
        {
          label: "Pending Queries",
          path: "/",
          pathMatch: ["/"],
          icon: "M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z",
        },
        {
          label: "My Cases",
          path: "/cases",
          pathMatch: ["/cases"],
          icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2",
        },
      ],
    },
    patient: {
      label: "Patient",
      icon: "M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z",
      navItems: [
        {
          label: "Claim Status",
          path: "/",
          pathMatch: ["/"],
          icon: "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z",
        },
      ],
    },
  };

  const roles: Role[] = ["tpa", "doctor", "patient"];
  const roleLabels: Record<Role, string> = {
    tpa: "TPA Desk",
    doctor: "Doctor",
    patient: "Patient",
  };
  const roleIcons: Record<Role, string> = {
    tpa: "👤",
    doctor: "🩺",
    patient: "👁️",
  };

  function isActive(pathMatch: string[], pathname: string) {
    return pathMatch?.some(
      (p) => pathname === p || (p !== "/" && pathname.startsWith(p)),
    );
  }

  $: config = roleConfig[$currentRole];
</script>

<div class="app-shell flex h-screen w-screen bg-app">
  <!-- Left Rail Navigation -->
  <aside
    class="w-64 flex flex-col justify-between shrink-0 z-20"
    style="background: var(--bg-deep); border-right: 1px solid var(--border-subtle);"
  >
    <div>
      <!-- Brand -->
      <div
        class="p-6 flex items-center gap-3"
        style="border-bottom: 1px solid var(--border-subtle);"
      >
        <div
          class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 relative overflow-hidden"
          style="background: linear-gradient(135deg, #0f172a, #1e293b); box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.1), 0 4px 15px rgba(45, 212, 191, 0.2); border: 1px solid rgba(45, 212, 191, 0.3);"
        >
          <svg
            class="w-6 h-6 z-10"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M12 2.5L20.5 7.5V16.5L12 21.5L3.5 16.5V7.5L12 2.5Z"
              fill="url(#gemGrad)"
              stroke="url(#gemBorder)"
              stroke-width="1.5"
            />
            <path
              d="M12 7V17M7 12H17"
              stroke="#ffffff"
              stroke-width="2.5"
              stroke-linecap="round"
            />
            <defs>
              <linearGradient
                id="gemGrad"
                x1="12"
                y1="2.5"
                x2="12"
                y2="21.5"
                gradientUnits="userSpaceOnUse"
              >
                <stop stop-color="#2dd4bf" stop-opacity="0.2" />
                <stop offset="1" stop-color="#0f766e" stop-opacity="0.8" />
              </linearGradient>
              <linearGradient
                id="gemBorder"
                x1="3.5"
                y1="2.5"
                x2="20.5"
                y2="21.5"
                gradientUnits="userSpaceOnUse"
              >
                <stop stop-color="#34d399" />
                <stop offset="1" stop-color="#0d9488" />
              </linearGradient>
            </defs>
          </svg>
          <div
            class="absolute inset-0 z-0 bg-teal-500 opacity-20 blur-xl"
          ></div>
        </div>
        <div class="flex flex-col ml-3">
          <span
            style="font-family: 'Space Grotesk', sans-serif; font-weight: 800; font-size: 1.25rem; letter-spacing: -0.04em; background: linear-gradient(180deg, #ffffff 0%, #cbd5e1 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;"
            >Pramana AI</span
          >
          <span
            style="font-size: 0.65rem; color: var(--teal-400); text-transform: uppercase; letter-spacing: 0.15em; font-weight: 700; margin-top: -0.1rem;"
            >Clinical Copilot</span
          >
        </div>
      </div>

      <!-- Role Switcher -->
      <div class="p-4" style="border-bottom: 1px solid var(--border-subtle);">
        <div
          style="font-size: 0.55rem; font-weight: 700; color: var(--n-600); text-transform: uppercase; letter-spacing: 0.15em; margin-bottom: 0.5rem; padding-left: 0.25rem;"
        >
          Viewing As
        </div>
        <div
          class="flex gap-1"
          style="background: var(--bg-surface); border-radius: var(--radius-md); padding: 3px; border: 1px solid var(--border-subtle);"
        >
          {#each roles as role}
            <button
              on:click={() => currentRole.set(role)}
              style="flex: 1; padding: 0.4rem 0.25rem; border-radius: 6px; font-size: 0.65rem; font-weight: 700; text-align: center; transition: all 0.2s; letter-spacing: 0.02em;
                {$currentRole === role
                ? 'background: rgba(45, 212, 191, 0.15); color: var(--teal-400); box-shadow: 0 0 8px rgba(45,212,191,0.1);'
                : 'color: var(--n-500);'}"
            >
              <span
                style="font-size: 0.75rem; display: block; line-height: 1; margin-bottom: 2px;"
                >{roleIcons[role]}</span
              >
              {roleLabels[role]}
            </button>
          {/each}
        </div>
      </div>

      <!-- Navigation -->
      <nav class="p-4 space-y-1">
        {#each config.navItems as item}
          <a
            href={item.path}
            class="flex items-center gap-3 px-4 py-3 transition-all"
            style="border-radius: var(--radius-md); {isActive(
              item.pathMatch,
              $page.url.pathname,
            )
              ? 'background: rgba(45, 212, 191, 0.1); color: var(--teal-400); border: 1px solid rgba(45, 212, 191, 0.2);'
              : 'color: var(--n-400); border: 1px solid transparent;'}"
          >
            <svg
              class="w-5 h-5"
              style="opacity: {isActive(item.pathMatch, $page.url.pathname)
                ? 1
                : 0.6}"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d={item.icon}
              />
            </svg>
            <span style="font-weight: 500; font-size: 0.875rem;"
              >{item.label}</span
            >
          </a>
        {/each}
      </nav>
    </div>

    <!-- Bottom: Edge AI Badge + User -->
    <div style="border-top: 1px solid var(--border-subtle);">
      <div class="p-4">
        <div
          class="p-3 flex items-center gap-3"
          style="background: rgba(45, 212, 191, 0.06); border: 1px solid rgba(45, 212, 191, 0.15); border-radius: var(--radius-md);"
        >
          <div
            class="w-8 h-8 rounded-lg flex items-center justify-center"
            style="background: rgba(45, 212, 191, 0.15);"
          >
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
                d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
              />
            </svg>
          </div>
          <div class="flex flex-col">
            <span
              style="font-size: 0.7rem; font-weight: 700; color: var(--teal-400); text-transform: uppercase; letter-spacing: 0.1em;"
              >Edge AI</span
            >
            <span style="font-size: 0.6rem; color: var(--n-500);"
              >Zero Cloud · 100% Local</span
            >
          </div>
        </div>
      </div>
      <div class="p-4 pt-0">
        <div class="flex items-center gap-3 px-2">
          <div
            class="w-8 h-8 rounded-full flex items-center justify-center"
            style="background: linear-gradient(135deg, var(--teal-600), var(--teal-400)); font-size: 0.7rem; font-weight: 700; color: white;"
          >
            {$currentRole === "doctor"
              ? "DR"
              : $currentRole === "patient"
                ? "PT"
                : "TP"}
          </div>
          <div class="flex flex-col" style="overflow: hidden;">
            <span
              style="font-size: 0.85rem; font-weight: 500; color: var(--n-200); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
            >
              {$currentRole === "doctor"
                ? "Dr. S. Reddy"
                : $currentRole === "patient"
                  ? "Ramesh Kumar"
                  : "TPA Admin"}
            </span>
            <span
              style="font-size: 0.7rem; color: var(--n-500); white-space: nowrap;"
            >
              {$currentRole === "doctor"
                ? "Cardiology Head"
                : $currentRole === "patient"
                  ? "Patient ID: P-10234"
                  : "Claim Processing"}
            </span>
          </div>
        </div>
      </div>
    </div>
  </aside>

  <!-- Main Content Area -->
  <main
    class="flex-1 flex flex-col min-w-0 overflow-hidden relative"
    style="background: var(--bg-navy);"
  >
    <header
      class="h-16 flex items-center justify-between px-6 shrink-0 z-10"
      style="background: var(--bg-deep); border-bottom: 1px solid var(--border-subtle);"
    >
      <div class="flex items-center gap-4">
        <div
          class="flex items-center gap-2 px-3 py-1.5"
          style="background: rgba(52, 211, 153, 0.08); color: var(--status-green); border-radius: var(--radius-full); border: 1px solid rgba(52, 211, 153, 0.2);"
        >
          <div
            class="w-2 h-2 rounded-full animate-pulse"
            style="background: var(--status-green);"
          ></div>
          <span
            style="font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;"
            >Offline Verified</span
          >
        </div>
        <div
          class="flex items-center gap-2 px-3 py-1.5"
          style="background: rgba(251, 191, 36, 0.08); color: var(--amber-400); border-radius: var(--radius-full); border: 1px solid rgba(251, 191, 36, 0.2); white-space: nowrap;"
        >
          <svg
            style="width: 14px; height: 14px; flex-shrink: 0;"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path d="M13 7H7v6h6V7z" />
            <path
              fill-rule="evenodd"
              d="M7 2a1 1 0 012 0v1h2V2a1 1 0 112 0v1h2a2 2 0 012 2v2h1a1 1 0 110 2h-1v2h1a1 1 0 110 2h-1v2a2 2 0 01-2 2h-2v1a1 1 0 11-2 0v-1H9v1a1 1 0 11-2 0v-1H5a2 2 0 01-2-2v-2H2a1 1 0 110-2h1V9H2a1 1 0 010-2h1V5a2 2 0 012-2h2V2zM5 5h10v10H5V5z"
              clip-rule="evenodd"
            />
          </svg>
          <span
            style="font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;"
            >MedGemma Powered</span
          >
        </div>
      </div>
      <div class="flex items-center gap-4">
        <div class="relative">
          <input
            type="text"
            placeholder="Search cases or clinical evidence..."
            style="padding: 0.4rem 1rem 0.4rem 2.25rem; font-size: 0.85rem; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); color: var(--text-primary); outline: none; width: 16rem;"
          />
          <svg
            class="w-4 h-4 absolute"
            style="left: 0.75rem; top: 0.6rem; color: var(--n-500);"
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
      </div>
    </header>
    <div class="flex-1 overflow-auto scroll-smooth p-6 relative bg-app">
      <slot />
    </div>
  </main>
</div>
