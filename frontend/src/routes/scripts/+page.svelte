<script lang="ts">
	import { scripts, scriptLoading, runs, tags as allTags } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { Plus, Search, X } from 'lucide-svelte';

	// Local filter state
	let localSearch = $state('');
	let filterRuntime = $state('');
	let filterTag = $state('');

	// Last run start_time per script
	const lastRunMap = $derived.by(() => {
		const map: Record<string, string | null> = {};
		for (const run of $runs) {
			if (
				run.start_time &&
				(!map[run.script_id] || run.start_time > (map[run.script_id] ?? ''))
			) {
				map[run.script_id] = run.start_time;
			}
		}
		return map;
	});

	// Filtered list — uses script.tags embedded from API (no N+1)
	const filtered = $derived.by(() => {
		let list = $scripts;
		if (localSearch) {
			const q = localSearch.toLowerCase();
			list = list.filter(
				(s) =>
					s.name.toLowerCase().includes(q) || (s.description ?? '').toLowerCase().includes(q)
			);
		}
		if (filterRuntime) list = list.filter((s) => s.runtime === filterRuntime);
		if (filterTag) list = list.filter((s) => s.tags?.some((t) => t.name === filterTag));
		return list;
	});

	// Derive which script IDs are currently running
	const runningScriptIds = $derived(
		new Set($runs.filter((r) => r.status === 'running').map((r) => r.script_id))
	);

	const hasFilters = $derived(!!localSearch || !!filterRuntime || !!filterTag);

	function clearFilters() {
		localSearch = '';
		filterRuntime = '';
		filterTag = '';
	}

	const runtimeLabel: Record<string, string> = { py: 'Python', sh: 'Shell', js: 'JavaScript' };
	const runtimeDot: Record<string, string> = {
		py: 'bg-cs-accent',
		sh: 'bg-cs-success',
		js: 'bg-cs-warning'
	};

	function relativeDate(iso: string | null | undefined): string {
		if (!iso) return '—';
		const diff = Date.now() - new Date(iso).getTime();
		const m = Math.floor(diff / 60000);
		if (m < 1) return 'just now';
		if (m < 60) return `${m}m ago`;
		const h = Math.floor(m / 60);
		if (h < 24) return `${h}h ago`;
		const d = Math.floor(h / 24);
		if (d < 30) return `${d}d ago`;
		return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	}
</script>

<div class="flex h-full flex-col">
	<!-- ── Page header ────────────────────────────────────── -->
	<div
		class="flex flex-shrink-0 items-center justify-between border-b border-cs-border px-6 py-3"
		style="background: var(--color-cs-surface);"
	>
		<div>
			<h1 class="font-mono text-base font-semibold text-cs-text">Scripts</h1>
			<p class="text-xs text-cs-text-muted">
				{$scripts.length} script{$scripts.length !== 1 ? 's' : ''}
			</p>
		</div>
		<a href="/scripts/new" class="btn-primary flex items-center gap-1.5 text-xs">
			<Plus size={13} strokeWidth={2.5} /> New Script
		</a>
	</div>

	<!-- ── Filter bar ─────────────────────────────────────── -->
	<div
		class="flex flex-shrink-0 items-center gap-3 border-b border-cs-border px-6 py-0"
		style="background: var(--color-cs-surface);"
	>
		<!-- Local search -->
		<div class="relative flex-1 flex items-center">
			<input
				type="search"
				class="input h-11 w-full pl-9 text-sm"
				placeholder="Search scripts…"
				bind:value={localSearch}
			/>
		</div>

		<!-- Runtime filter -->
		<select class="input h-11 flex-1 text-sm" bind:value={filterRuntime}>
			<option value="">All runtimes</option>
			<option value="py">Python</option>
			<option value="sh">Shell</option>
			<option value="js">JavaScript</option>
		</select>

		<!-- Tag filter -->
		{#if $allTags.length > 0}
			<select class="input h-11 flex-1 text-sm" bind:value={filterTag}>
				<option value="">All tags</option>
				{#each $allTags as tag}
					<option value={tag.name}>{tag.name}</option>
				{/each}
			</select>
		{/if}

		<!-- Clear filters -->
		{#if hasFilters}
			<button class="ghost-btn flex items-center gap-1.5 text-sm" onclick={clearFilters}>
				<X size={13} /> Clear
			</button>
		{/if}
	</div>

	<!-- ── Inventory table ────────────────────────────────── -->
	<div class="flex-1 overflow-auto">
		{#if $scriptLoading}
			<div class="flex flex-col">
				{#each Array(8) as _}
					<div class="animate-pulse border-b border-cs-border px-6 py-3.5">
						<div class="flex items-center gap-4">
							<div class="h-2.5 w-2.5 rounded-full bg-cs-surface-2"></div>
							<div class="h-3.5 w-40 rounded bg-cs-surface-2"></div>
							<div class="h-3 w-56 rounded bg-cs-surface-2"></div>
							<div class="ml-auto h-3 w-20 rounded bg-cs-surface-2"></div>
						</div>
					</div>
				{/each}
			</div>
		{:else if filtered.length === 0}
			<div class="flex flex-col items-center justify-center py-20 text-center">
				<p class="mb-1 text-sm text-cs-text-muted">
					{hasFilters ? 'No scripts match your filters' : 'No scripts yet'}
				</p>
				{#if hasFilters}
					<button class="ghost-btn mt-2 text-xs" onclick={clearFilters}>Clear filters</button>
				{:else}
					<a href="/scripts/new" class="btn-primary mt-3 text-xs">Create your first script</a>
				{/if}
			</div>
		{:else}
			<!-- Column headers -->
			<div
				class="grid grid-cols-[2fr_1fr_2fr_1fr_1fr] gap-4 border-b border-cs-border px-6 py-2 text-[11px] font-medium uppercase tracking-wider text-cs-text-muted"
				style="background: var(--color-cs-surface);"
			>
				<span>Name</span>
				<span>Runtime</span>
				<span>Tags</span>
				<span>Last run</span>
				<span>Created</span>
			</div>

			{#each filtered as script (script.id)}
				<a
					href="/scripts/{script.id}"
					class="grid grid-cols-[2fr_1fr_2fr_1fr_1fr] items-center gap-4 border-b border-cs-border px-6 py-4 text-sm transition-colors hover:bg-cs-surface-2"
					style="text-decoration: none; min-height: 64px;"
				>
					<div class="min-w-0">
						<div class="flex items-center gap-2">
							{#if runningScriptIds.has(script.id)}
								<span class="status-dot status-dot--running flex-shrink-0"></span>
							{:else}
								<span class="h-2.5 w-2.5 flex-shrink-0 rounded-full {runtimeDot[script.runtime]}" style="box-shadow: 0 0 0 3px color-mix(in srgb, currentColor 12%, transparent);"></span>
							{/if}
							<span class="truncate font-mono text-sm font-semibold text-cs-text">{script.name}</span>
						</div>
						{#if script.description}
							<p class="ml-4 mt-1 truncate text-xs text-cs-text-muted">{script.description}</p>
						{/if}
					</div>

					<span class="badge w-fit">{runtimeLabel[script.runtime]}</span>

					<div class="flex flex-wrap gap-2">
						{#if script.tags?.length}
							{#each script.tags.slice(0, 4) as tag}
								<span class="tag-pill">{tag.name}</span>
							{/each}
							{#if script.tags.length > 4}
								<span class="text-[10px] text-cs-text-muted">+{script.tags.length - 4}</span>
							{/if}
						{:else}
							<span class="text-[10px] text-cs-text-muted">—</span>
						{/if}
					</div>

					<span class="text-xs text-cs-text-muted">{relativeDate(lastRunMap[script.id])}</span>

					<span class="text-xs text-cs-text-muted">{relativeDate(script.created_at)}</span>
				</a>
			{/each}
		{/if}
	</div>
</div>
