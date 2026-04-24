<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import { scripts, edges, graphSelectedNode, flyoutOpen, loadGraphConfig, graphConfig } from '$lib/stores';
	import * as api from '$lib/api/client';
	import { Plus, Trash2, GitBranch } from 'lucide-svelte';
	import GraphControls from '$lib/components/graph/GraphControls.svelte';
	import GraphCanvas from '$lib/components/graph/GraphCanvas.svelte';
	import type { CanvasNode, CanvasEdge } from '$lib/components/graph/GraphCanvas.svelte';

	// ── State ─────────────────────────────────────────────────────
	let loading  = $state(true);
	let nodeCount = $state(0);
	let edgeCount = $state(0);

	// Plain arrays — use $state.raw so assignment propagates to canvas but D3
	// in-place mutations (.x/.y per tick) don't trigger Svelte reactive updates.
	let simNodes = $state.raw<CanvasNode[]>([]);
	let simEdges = $state.raw<CanvasEdge[]>([]);
	let selectedId = $state<string | null>(null);
	let canvasRef = $state<{ fitView: (a: boolean) => void; zoomTo: (id: string) => void } | null>(null);

	// Edge panel
	let showAddEdge = $state(false);
	let sourceId = $state('');
	let targetId = $state('');
	type ManualRelation = 'data_flow' | 'shared_env' | 'manual' | 'sequential';
	let manualRelation = $state<ManualRelation>('manual');

	// D3 simulation handle
	let simulation: d3.Simulation<CanvasNode, d3.SimulationLinkDatum<CanvasNode>> | null = null;

	const heightScale = d3.scaleSqrt().domain([0, 100]).range([44, 80]).clamp(true);

	// ── Data loading ───────────────────────────────────────────────
	async function loadGraph() {
		loading = true;
		try {
			const cfg = $graphConfig;
			const limit = cfg?.run_history_limit ?? 500;
			const [graphData, runsData] = await Promise.all([api.graph(), api.runs.list(undefined, limit)]);

			const runCounts = new Map<string, number>();
			const lastStatus = new Map<string, string>();
			for (const r of runsData) {
				runCounts.set(r.script_id, (runCounts.get(r.script_id) ?? 0) + 1);
				if (!lastStatus.has(r.script_id)) lastStatus.set(r.script_id, r.status);
			}

			simNodes = graphData.nodes
				.filter((n: { type: string }) => n.type === 'script')
				.map((n: { id: string; data: Record<string, unknown> }) => {
					const count = runCounts.get(n.id) ?? 0;
					const h = heightScale(count);
					return {
						id: n.id, label: String(n.data.name ?? n.id),
						runtime: String(n.data.runtime ?? '?'), runCount: count,
						lastStatus: lastStatus.get(n.id), w: h * 2.57, h,
					} satisfies CanvasNode;
				});

			const scriptIds = new Set(simNodes.map(n => n.id));
			const explicit: CanvasEdge[] = graphData.edges
				.filter((e: { source: string; target: string; type: string }) =>
					scriptIds.has(e.source) && scriptIds.has(e.target) && !['written_in', 'labeled_as'].includes(e.type))
				.map((e: { id: string; source: string; target: string; type: string }) => ({
					id: e.id, sourceId: e.source, targetId: e.target, relation: e.type, implicit: false,
				}));

			// Implicit shared-tag edges
			const minShared = cfg?.implicit_edge_min_shared_tags ?? 2;
			const tagEdges = graphData.edges.filter((e: { type: string }) => e.type === 'labeled_as');
			const stMap = new Map<string, Set<string>>();
			for (const e of tagEdges) { if (!stMap.has(e.source)) stMap.set(e.source, new Set()); stMap.get(e.source)!.add(e.target); }
			const implicit: CanvasEdge[] = [];
			for (let i = 0; i < simNodes.length; i++) {
				for (let j = i + 1; j < simNodes.length; j++) {
					const a = simNodes[i], b = simNodes[j];
					const shared = [...(stMap.get(a.id) ?? [])].filter(t => stMap.get(b.id)?.has(t));
					if (shared.length >= minShared)
						implicit.push({ id: `imp-${a.id}-${b.id}`, sourceId: a.id, targetId: b.id, relation: 'shared_tags', implicit: true });
				}
			}
			simEdges = [...explicit, ...implicit];

			nodeCount = simNodes.length;
			edgeCount = explicit.length;
			initSimulation();
		} finally { loading = false; }
	}

	function initSimulation() {
		simulation?.stop();
		const cfg = $graphConfig;
		const W = window.innerWidth * 0.7, H = window.innerHeight;
		const cols = Math.ceil(Math.sqrt(simNodes.length));
		simNodes.forEach((n, i) => { if (!n.x) { n.x = 100 + (i % cols) * 200; n.y = 100 + Math.floor(i / cols) * 160; } });

		const linkData = simEdges.map(e => ({ source: e.sourceId, target: e.targetId, implicit: e.implicit, relation: e.relation }));
		simulation = d3.forceSimulation<CanvasNode>(simNodes)
			.force('link', d3.forceLink<CanvasNode, typeof linkData[0]>(linkData)
				.id(d => d.id)
				.distance(d => d.implicit ? (cfg?.link_distance_implicit ?? 220) : (cfg?.link_distance_explicit ?? 140))
				.strength(d => d.implicit ? (cfg?.link_strength_implicit ?? 0.3) : (cfg?.link_strength_explicit ?? 0.6)))
			.force('charge', d3.forceManyBody<CanvasNode>().strength(cfg?.charge_strength ?? -450).distanceMax(cfg?.charge_distance_max ?? 400))
			.force('center', d3.forceCenter(W / 2, H / 2).strength(cfg?.center_strength ?? 0.05))
			.force('collision', simNodes.length <= (cfg?.collision_node_threshold ?? 80)
				? d3.forceCollide<CanvasNode>(d => Math.hypot(d.w, d.h) / 2 + 20) : null)
			.alphaDecay(cfg?.alpha_decay ?? 0.028)
			.velocityDecay(cfg?.velocity_decay ?? 0.4);

		setTimeout(() => canvasRef?.fitView(true), cfg?.fit_view_delay_ms ?? 1800);
	}

	// Watch selection → smart zoom
	$effect(() => {
		const id = $graphSelectedNode;
		selectedId = id;
		if (id && !loading) setTimeout(() => canvasRef?.zoomTo(id), 50);
	});

	onMount(async () => { await loadGraphConfig(); await loadGraph(); });
	onDestroy(() => { simulation?.stop(); });

	// ── Edge management ────────────────────────────────────────────
	async function addEdge() {
		if (!sourceId || !targetId || sourceId === targetId) return;
		await api.edges.create({ source_id: sourceId, target_id: targetId, relation: manualRelation });
		showAddEdge = false; sourceId = ''; targetId = '';
		await loadGraph();
	}

	async function removeEdge(id: string) {
		await api.edges.delete(id);
		await loadGraph();
	}

	const relColor: Record<string, string> = {
		data_flow: 'text-cs-success', shared_env: 'text-cs-running',
		manual: 'text-cs-text-muted', sequential: 'text-cs-accent',
	};
</script>

<div class="relative flex h-full flex-col" style="background: var(--color-cs-bg);">
	<div class="flex flex-shrink-0 items-center gap-2 border-b border-cs-border px-4 py-2"
		style="background: var(--color-cs-surface);">
		<GitBranch size={14} strokeWidth={2} style="color: var(--color-cs-text-muted);" />
		<h2 class="font-mono text-xs font-semibold text-cs-text">Knowledge Graph</h2>
		<div class="flex-1"></div>
		<button class="ghost-btn flex items-center gap-1.5 text-xs" onclick={() => (showAddEdge = !showAddEdge)}>
			<Plus size={12} strokeWidth={2} /> Add Edge
		</button>
	</div>

	{#if showAddEdge}
		<div class="flex flex-shrink-0 flex-wrap items-end gap-2 border-b border-cs-border px-4 py-3"
			style="background: var(--color-cs-surface-2);">
			<div>
				<label for="edge-source" class="mb-0.5 block text-[10px] text-cs-text-muted">Source</label>
				<select id="edge-source" class="input text-xs" style="width:140px;" bind:value={sourceId}>
					<option value="">Select…</option>
					{#each $scripts as s}<option value={s.id}>{s.name}</option>{/each}
				</select>
			</div>
			<div>
				<label for="edge-relation" class="mb-0.5 block text-[10px] text-cs-text-muted">Relation</label>
				<select id="edge-relation" class="input text-xs" style="width:120px;" bind:value={manualRelation}>
					<option value="data_flow">Data Flow</option>
					<option value="shared_env">Shared Env</option>
					<option value="manual">Manual</option>
					<option value="sequential">Sequential</option>
				</select>
			</div>
			<div>
				<label for="edge-target" class="mb-0.5 block text-[10px] text-cs-text-muted">Target</label>
				<select id="edge-target" class="input text-xs" style="width:140px;" bind:value={targetId}>
					<option value="">Select…</option>
					{#each $scripts as s}<option value={s.id}>{s.name}</option>{/each}
				</select>
			</div>
			<button class="btn-primary text-xs" onclick={addEdge}>Add</button>
		</div>
	{/if}

	<div class="flex flex-1 overflow-hidden">
		<div class="relative flex-1 overflow-hidden">
			{#if loading}
				<div class="flex h-full items-center justify-center text-sm text-cs-text-muted">Loading graph…</div>
			{:else}
				<GraphCanvas
					bind:this={canvasRef}
					nodes={simNodes}
					edges={simEdges}
					{selectedId}
					cfg={$graphConfig}
					onselect={(id) => { graphSelectedNode.set(id); if (id) flyoutOpen.set(true); }}
					onhover={() => {}}
				/>
				<GraphControls {nodeCount} {edgeCount} onResetZoom={() => canvasRef?.fitView(true)} />
			{/if}
		</div>

		<div class="w-56 flex-shrink-0 overflow-y-auto border-l border-cs-border p-3"
			style="background: var(--color-cs-surface);">
			<h4 class="mb-2 text-[10px] font-semibold uppercase tracking-wider text-cs-text-muted">Connections</h4>
			{#if $edges.length === 0}
				<p class="text-xs text-cs-text-muted">No connections yet</p>
			{:else}
				{#each $edges as edge}
					{@const src = $scripts.find(s => s.id === edge.source_id)}
					{@const tgt = $scripts.find(s => s.id === edge.target_id)}
					<div class="mb-2 flex items-start gap-2 rounded p-2 text-xs" style="background: var(--color-cs-surface-2);">
						<div class="min-w-0 flex-1">
							<div class="truncate font-mono text-cs-text">{src?.name ?? '?'}</div>
							<div class="my-0.5 {relColor[edge.relation] ?? 'text-cs-text-muted'} text-[10px]">↓ {edge.relation}</div>
							<div class="truncate font-mono text-cs-text">{tgt?.name ?? '?'}</div>
						</div>
						<button class="mt-0.5 text-cs-text-muted transition-colors hover:text-cs-error" onclick={() => removeEdge(edge.id)}>
							<Trash2 size={11} />
						</button>
					</div>
				{/each}
			{/if}
		</div>
	</div>
</div>
