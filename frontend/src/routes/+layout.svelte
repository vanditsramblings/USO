<script lang="ts">
	import '../app.css';
	import { Splitpanes, Pane } from 'svelte-splitpanes';
	import OmniSearch from '$lib/components/OmniSearch.svelte';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import ContextDrawer from '$lib/components/ContextDrawer.svelte';
	import { loadScripts, loadTags, drawerOpen } from '$lib/stores';
	import { onMount } from 'svelte';

	let { children } = $props();

	onMount(() => {
		loadScripts();
		loadTags();
	});
</script>

<svelte:head>
	<title>USO — Unified Script Orchestrator</title>
</svelte:head>

<div class="flex h-screen flex-col overflow-hidden">
	<!-- Top Bar -->
	<header class="flex h-12 shrink-0 items-center gap-3 border-b border-border bg-bg-elevated px-4">
		<a href="/" class="font-mono text-sm font-bold tracking-tight text-accent">USO</a>
		<div class="flex-1">
			<OmniSearch />
		</div>
		<nav class="flex gap-1 items-center">
			<a href="/" class="ghost-btn">Scripts</a>
			<a href="/graph" class="ghost-btn">Graph</a>
			<a href="/metrics" class="ghost-btn">Metrics</a>
			<a href="/workflows" class="ghost-btn">Workflows</a>
			<a href="/schedules" class="ghost-btn">Schedules</a>
			<div class="relative group">
				<button class="ghost-btn flex items-center gap-1">
					System
					<span style="font-size:10px">▾</span>
				</button>
				<div class="absolute right-0 top-full z-50 hidden group-focus-within:flex group-hover:flex flex-col
				            min-w-[160px] rounded-lg border border-border bg-bg-elevated shadow-lg py-1">
					<a href="/system/config" class="ghost-btn rounded-none text-left px-4 py-2">Configuration</a>
					<a href="/system/modules" class="ghost-btn rounded-none text-left px-4 py-2">Modules</a>
				</div>
			</div>
		</nav>
	</header>

	<!-- Resizable Triple Pane -->
	<Splitpanes class="flex-1" dblClickSplitter={false}>
		<Pane size={18} minSize={12} maxSize={30}>
			<Sidebar />
		</Pane>
		<Pane size={$drawerOpen ? 57 : 82} minSize={40}>
			<main class="h-full overflow-auto">
				{@render children()}
			</main>
		</Pane>
		{#if $drawerOpen}
			<Pane size={25} minSize={15} maxSize={40}>
				<ContextDrawer />
			</Pane>
		{/if}
	</Splitpanes>
</div>

<style>
	:global(.ghost-btn) {
		padding: 4px 10px;
		border-radius: 6px;
		font-size: 13px;
		color: var(--color-text-muted);
		transition: all 0.15s;
		text-decoration: none;
	}
	:global(.ghost-btn:hover) {
		background: var(--color-bg-hover);
		color: var(--color-text);
	}
	:global(.badge) {
		display: inline-flex;
		align-items: center;
		padding: 1px 8px;
		border-radius: 9999px;
		font-size: 11px;
		font-weight: 500;
		border: 1px solid var(--color-border);
		color: var(--color-text-muted);
	}
	:global(.btn-primary) {
		padding: 6px 14px;
		border-radius: 6px;
		font-size: 13px;
		font-weight: 500;
		background: var(--color-accent-dim);
		color: var(--color-accent);
		border: 1px solid var(--color-accent);
		cursor: pointer;
		transition: all 0.15s;
	}
	:global(.btn-primary:hover) {
		background: var(--color-accent);
		color: var(--color-bg);
	}
	:global(.btn-danger) {
		padding: 6px 14px;
		border-radius: 6px;
		font-size: 13px;
		background: transparent;
		color: var(--color-danger);
		border: 1px solid var(--color-danger);
		cursor: pointer;
		transition: all 0.15s;
	}
	:global(.btn-danger:hover) {
		background: var(--color-danger);
		color: var(--color-bg);
	}
	:global(.input) {
		padding: 6px 10px;
		border-radius: 6px;
		font-size: 13px;
		background: var(--color-bg);
		color: var(--color-text);
		border: 1px solid var(--color-border);
		outline: none;
		width: 100%;
	}
	:global(.input:focus) {
		border-color: var(--color-accent);
	}
</style>
