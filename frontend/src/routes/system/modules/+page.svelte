<script lang="ts">
	import { onMount } from 'svelte';
	import { modules as modulesApi } from '$lib/api/client';
	import { Package, CheckCircle, XCircle, RefreshCw } from 'lucide-svelte';

	type Module = {
		name: string;
		import_name?: string;
		description: string;
		category: string;
		available: boolean;
		runtime: string;
	};

	type ModulesData = {
		python: { version: string; executable: string; modules: Module[] };
		shell: { modules: Module[] };
		javascript: { node_available: boolean; modules: Module[] };
	};

	let data = $state<ModulesData | null>(null);
	let loading = $state(true);
	let activeRuntime = $state<'py' | 'sh' | 'js'>('py');
	let categoryFilter = $state('all');

	onMount(async () => {
		data = (await modulesApi()) as ModulesData;
		loading = false;
	});

	const runtimeModules = $derived(
		!data
			? []
			: activeRuntime === 'py'
				? data.python.modules
				: activeRuntime === 'sh'
					? data.shell.modules
					: data.javascript.modules
	);

	const categories = $derived([
		'all',
		...new Set(runtimeModules.map((m) => m.category))
	]);

	const filtered = $derived(
		categoryFilter === 'all'
			? runtimeModules
			: runtimeModules.filter((m) => m.category === categoryFilter)
	);

	const available = $derived(filtered.filter((m) => m.available).length);

	function runtimeLabel(r: string) {
		return r === 'py' ? 'Python' : r === 'sh' ? 'Shell' : 'JavaScript';
	}
</script>

<svelte:head>
	<title>USO — Supported Modules</title>
</svelte:head>

<div class="mx-auto max-w-4xl space-y-5 p-6">
	<!-- Header -->
	<div class="flex items-center gap-2">
		<Package size={18} class="text-accent" />
		<h1 class="text-base font-semibold">Supported Modules</h1>
	</div>

	<!-- Runtime tabs -->
	<div class="flex gap-1 rounded-lg border border-cs-border bg-cs-surface p-1 w-fit">
		{#each ['py', 'sh', 'js'] as rt}
			<button
				class="rounded px-4 py-1.5 text-sm font-medium transition-all"
				class:bg-cs-surface-2={activeRuntime === rt}
				class:text-accent={activeRuntime === rt}
				class:text-cs-text-muted={activeRuntime !== rt}
				onclick={() => { activeRuntime = rt as 'py' | 'sh' | 'js'; categoryFilter = 'all'; }}
			>
				{runtimeLabel(rt)}
			</button>
		{/each}
	</div>

	{#if data}
		<!-- Runtime meta -->
		<div class="rounded border border-cs-border bg-cs-surface px-4 py-2 text-xs text-cs-text-muted">
			{#if activeRuntime === 'py'}
				Python {data.python.version.split(' ')[0]} · {data.python.executable}
			{:else if activeRuntime === 'sh'}
				Shell builtins — availability checked via <code>which</code>
			{:else}
				Node.js {data.javascript.node_available ? '— available' : '— not found in PATH'}
			{/if}
		</div>
	{/if}

	<!-- Category filter + stats -->
	<div class="flex items-center justify-between">
		<div class="flex flex-wrap gap-1">
			{#each categories as cat}
				<button
					class="badge cursor-pointer transition-all"
					class:border-accent={categoryFilter === cat}
					class:text-accent={categoryFilter === cat}
					onclick={() => (categoryFilter = cat)}
				>
					{cat}
				</button>
			{/each}
		</div>
		{#if !loading}
			<span class="text-xs text-cs-text-muted">
				{available}/{filtered.length} available
			</span>
		{/if}
	</div>

	<!-- Table -->
	{#if loading}
		<div class="text-sm text-cs-text-muted">Loading modules…</div>
	{:else}
		<div class="rounded-lg border border-cs-border overflow-hidden">
			<table class="w-full text-sm">
				<thead class="bg-cs-surface text-xs text-cs-text-muted">
					<tr>
						<th class="px-4 py-2 text-left font-medium">Module</th>
						<th class="px-4 py-2 text-left font-medium">Category</th>
						<th class="px-4 py-2 text-left font-medium">Description</th>
						<th class="px-4 py-2 text-center font-medium">Status</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-border">
					{#each filtered as mod}
						<tr class="hover:bg-cs-surface-2/40 transition-colors">
							<td class="px-4 py-2.5 font-mono text-xs text-accent">{mod.name}</td>
							<td class="px-4 py-2.5">
								<span class="badge">{mod.category}</span>
							</td>
							<td class="px-4 py-2.5 text-cs-text-muted text-xs">{mod.description}</td>
							<td class="px-4 py-2.5 text-center">
								{#if mod.available}
									<CheckCircle size={15} class="inline text-green-400" />
								{:else}
									<XCircle size={15} class="inline text-cs-error/70" />
								{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
