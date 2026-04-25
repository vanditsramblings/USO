<script lang="ts">
	import '../app.css';
	import OmniSearch from '$lib/components/OmniSearch.svelte';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import ScriptFlyout from '$lib/components/ScriptFlyout.svelte';
	import { loadScripts, loadTags, loadRuns, omniSearchOpen, theme, sidebarCollapsed } from '$lib/stores';
	import { onMount } from 'svelte';

	let { children } = $props();

	// Apply data-theme to <html> whenever the store changes
	$effect(() => {
		document.documentElement.dataset.theme = $theme;
	});

	onMount(() => {
		loadScripts();
		loadTags();
		loadRuns();
	});

	function handleKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
			e.preventDefault();
			omniSearchOpen.set(true); // OmniSearch $effect watches this to focus its input
		}
	}
</script>

<svelte:head>
	<title>USO — Unified Script Orchestrator</title>
</svelte:head>

<svelte:window onkeydown={handleKeydown} />

<div class="flex h-screen flex-col overflow-hidden" style="background: var(--color-cs-bg);">
	<!-- Top Chrome -->
	<header class="flex h-20 flex-shrink-0 items-center border-b border-cs-border"
		style="background: var(--color-cs-surface);">
		<!-- USO Title Box (matches sidebar width) -->
		<div class="flex-shrink-0 border-r border-cs-border px-4 flex items-center justify-center transition-[width] duration-200"
			style="width: {$sidebarCollapsed ? '56px' : '220px'};">
			<a href="/" class="font-mono font-bold tracking-widest text-cs-accent uppercase select-none transition-[font-size] duration-200"
				style="font-size: {$sidebarCollapsed ? '0.875rem' : '2.00rem'}; width: 100%; text-align: center;">
				USO
			</a>
		</div>
		<!-- Search Box (fills remaining space) -->
		<div class="flex-1 px-4 flex items-center">
			<OmniSearch />
		</div>
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

