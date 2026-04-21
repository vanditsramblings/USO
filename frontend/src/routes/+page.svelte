<script lang="ts">
	import { filteredScripts, scriptLoading, activeScriptId, drawerOpen } from '$lib/stores';
	import { FileCode2, Zap, GitBranch, BarChart3 } from 'lucide-svelte';
	import { goto } from '$app/navigation';
	import * as api from '$lib/api/client';
	import type { Script, Tag } from '$lib/types';

	let scriptTags = $state<Record<string, Tag[]>>({});

	function selectScript(s: Script) {
		activeScriptId.set(s.id);
		drawerOpen.set(true);
		goto(`/scripts/${s.id}`);
	}

	$effect(() => {
		const list = $filteredScripts;
		if (list.length > 0) {
			Promise.all(list.map((s) => api.tags.forScript(s.id).then((t) => [s.id, t] as const))).then(
				(pairs) => {
					const map: Record<string, Tag[]> = {};
					for (const [id, t] of pairs) map[id] = t;
					scriptTags = map;
				}
			);
		}
	});

	const runtimeLabel: Record<string, string> = { py: 'Python', sh: 'Shell', js: 'JavaScript' };
</script>

<div class="p-6">
	<!-- Hero -->
	<div class="mb-8">
		<h1 class="mb-1 font-mono text-lg font-bold">Unified Script Orchestrator</h1>
		<p class="text-sm text-text-muted">Manage, execute, and connect your scripts</p>
	</div>

	<!-- Quick Stats -->
	<div class="mb-8 grid grid-cols-4 gap-3">
		<div class="rounded-lg border border-border bg-bg-elevated p-4">
			<div class="mb-1 flex items-center gap-2 text-text-dim">
				<FileCode2 size={14} strokeWidth={2} />
				<span class="text-xs uppercase tracking-wider">Scripts</span>
			</div>
			<span class="font-mono text-2xl font-bold">{$filteredScripts.length}</span>
		</div>
		<a href="/graph" class="rounded-lg border border-border bg-bg-elevated p-4 transition-colors hover:border-accent/30">
			<div class="mb-1 flex items-center gap-2 text-text-dim">
				<GitBranch size={14} strokeWidth={2} />
				<span class="text-xs uppercase tracking-wider">Graph</span>
			</div>
			<span class="text-sm text-text-muted">View Knowledge Graph</span>
		</a>
		<a href="/metrics" class="rounded-lg border border-border bg-bg-elevated p-4 transition-colors hover:border-accent/30">
			<div class="mb-1 flex items-center gap-2 text-text-dim">
				<BarChart3 size={14} strokeWidth={2} />
				<span class="text-xs uppercase tracking-wider">Metrics</span>
			</div>
			<span class="text-sm text-text-muted">Run Analytics</span>
		</a>
		<a href="/workflows" class="rounded-lg border border-border bg-bg-elevated p-4 transition-colors hover:border-accent/30">
			<div class="mb-1 flex items-center gap-2 text-text-dim">
				<Zap size={14} strokeWidth={2} />
				<span class="text-xs uppercase tracking-wider">Workflows</span>
			</div>
			<span class="text-sm text-text-muted">DAG Pipelines</span>
		</a>
	</div>

	<!-- Script Grid -->
	<h2 class="mb-3 text-xs font-medium uppercase tracking-wider text-text-dim">All Scripts</h2>
	{#if $scriptLoading}
		<div class="grid grid-cols-3 gap-3">
			{#each Array(6) as _}
				<div class="animate-pulse rounded-lg border border-border bg-bg-elevated p-4">
					<div class="mb-2 h-4 w-2/3 rounded bg-bg-surface"></div>
					<div class="h-3 w-full rounded bg-bg-surface"></div>
				</div>
			{/each}
		</div>
	{:else}
		<div class="grid grid-cols-3 gap-3">
			{#each $filteredScripts as script}
				<button
					class="rounded-lg border border-border bg-bg-elevated p-4 text-left transition-all hover:border-accent/30 hover:bg-bg-surface"
					onclick={() => selectScript(script)}
				>
					<div class="mb-1 flex items-center justify-between">
						<span class="font-mono text-sm font-medium">{script.name}</span>
						<span class="badge">{runtimeLabel[script.runtime]}</span>
					</div>
					<p class="mb-2 text-xs text-text-muted line-clamp-2">
						{script.description || 'No description'}
					</p>
					<div class="flex items-center gap-2 text-xs text-text-dim">
						<span>v{script.version}</span>
						<span>·</span>
						<span>{script.parameters.length} params</span>
					</div>
					{#if scriptTags[script.id]?.length}
						<div class="mt-1.5 flex flex-wrap gap-1">
							{#each scriptTags[script.id].slice(0, 4) as tag}
								<span class="inline-block rounded bg-accent/10 px-1.5 py-0.5 text-[10px] text-accent">{tag.name}</span>
							{/each}
						</div>
					{/if}
				</button>
			{/each}
		</div>
	{/if}
</div>
