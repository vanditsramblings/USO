<script lang="ts">
	import '../app.css';
	import OmniSearch from '$lib/components/OmniSearch.svelte';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import ScriptFlyout from '$lib/components/ScriptFlyout.svelte';
	import { loadScripts, loadTags, loadRuns, omniSearchOpen } from '$lib/stores';
	import { onMount } from 'svelte';

	let { children } = $props();

	onMount(() => {
		loadScripts();
		loadTags();
		loadRuns();
	});

	function handleKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
			e.preventDefault();
			omniSearchOpen.set(true);
		}
	}
</script>

<svelte:head>
	<title>USO — Unified Script Orchestrator</title>
</svelte:head>

<svelte:window onkeydown={handleKeydown} />

<div class="flex h-screen flex-col overflow-hidden" style="background: var(--color-cs-bg);">
	<!-- Top Chrome -->
	<header class="flex h-11 flex-shrink-0 items-center gap-3 border-b border-cs-border px-4"
		style="background: var(--color-cs-surface);">
		<a href="/" class="font-mono text-sm font-bold tracking-widest text-cs-accent uppercase select-none">USO</a>
		<div class="flex-1 flex justify-center">
			<OmniSearch />
		</div>
		<nav class="flex gap-1 items-center">
			<div class="relative group">
				<button class="ghost-btn flex items-center gap-1 text-xs">
					System <span style="font-size:9px">▾</span>
				</button>
				<div class="absolute right-0 top-full z-50 hidden group-focus-within:flex group-hover:flex flex-col
				            min-w-[160px] rounded border border-cs-border shadow-lg py-1"
					style="background: var(--color-cs-surface);">
					<a href="/system/config" class="ghost-btn rounded-none text-left px-4 py-2 text-xs">Configuration</a>
					<a href="/system/modules" class="ghost-btn rounded-none text-left px-4 py-2 text-xs">Modules</a>
				</div>
			</div>
		</nav>
	</header>

	<!-- Body: Sidebar + Main -->
	<div class="flex flex-1 overflow-hidden">
		<Sidebar />
		<main class="flex-1 overflow-auto h-full">
			{@render children()}
		</main>
	</div>
</div>

<ScriptFlyout />

<style>
	:global(.ghost-btn) {
		padding: 4px 10px;
		border-radius: 6px;
		font-size: 13px;
		color: var(--color-cs-text-muted);
		transition: color 200ms cubic-bezier(0.4,0,0.2,1), background 200ms cubic-bezier(0.4,0,0.2,1);
		text-decoration: none;
		background: transparent;
		border: none;
		cursor: pointer;
	}
	:global(.ghost-btn:hover) {
		background: var(--color-cs-surface-2);
		color: var(--color-cs-text);
	}
	:global(.badge) {
		display: inline-flex;
		align-items: center;
		padding: 1px 8px;
		border-radius: 9999px;
		font-size: 11px;
		font-weight: 500;
		border: 1px solid var(--color-cs-border);
		color: var(--color-cs-text-muted);
	}
	:global(.btn-primary) {
		padding: 6px 14px;
		border-radius: 6px;
		font-size: 13px;
		font-weight: 500;
		background: var(--color-cs-accent-dim);
		color: var(--color-cs-accent);
		border: 1px solid var(--color-cs-accent);
		cursor: pointer;
		transition: all 200ms cubic-bezier(0.4,0,0.2,1);
	}
	:global(.btn-primary:hover) {
		background: var(--color-cs-accent);
		color: var(--color-cs-bg);
	}
	:global(.btn-danger) {
		padding: 6px 14px;
		border-radius: 6px;
		font-size: 13px;
		background: transparent;
		color: var(--color-cs-error);
		border: 1px solid var(--color-cs-error);
		cursor: pointer;
		transition: all 200ms cubic-bezier(0.4,0,0.2,1);
	}
	:global(.btn-danger:hover) {
		background: var(--color-cs-error);
		color: var(--color-cs-bg);
	}
	:global(.input) {
		padding: 6px 10px;
		border-radius: 6px;
		font-size: 13px;
		background: var(--color-cs-surface-2);
		color: var(--color-cs-text);
		border: 1px solid var(--color-cs-border);
		outline: none;
		width: 100%;
		transition: border-color 200ms cubic-bezier(0.4,0,0.2,1);
	}
	:global(.input:focus) {
		border-color: var(--color-cs-accent);
	}
</style>
