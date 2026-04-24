<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import * as d3 from 'd3';
	import { scripts, edges, runs, graphSelectedNode, flyoutOpen, showImplicitEdges } from '$lib/stores';
	import * as api from '$lib/api/client';
	import { Plus, Trash2, GitBranch } from 'lucide-svelte';
	import GraphControls from '$lib/components/graph/GraphControls.svelte';

	// ── Types ──────────────────────────────────────────────────────
	interface SimNode extends d3.SimulationNodeDatum {
		id: string; name: string; runtime: string; description: string | null;
		runCount: number; nodeWidth: number; nodeHeight: number;
		lastStatus?: string;
	}
	interface SimLink extends d3.SimulationLinkDatum<SimNode> {
		id: string; relation: string; implicit: boolean;
	}

	// ── State ──────────────────────────────────────────────────────
	let svgEl    = $state<SVGSVGElement | null>(null);
	let loading  = $state(true);
	let nodeCount = $state(0);
	let edgeCount = $state(0);

	// Edge panel
	let showAddEdge   = $state(false);
	let sourceId      = $state('');
	let targetId      = $state('');
	let manualRelation = $state<'data_flow'|'shared_env'|'manual'|'sequential'>('manual');

	// Edge tooltip
	let tooltip = $state<{ x:number; y:number; text:string } | null>(null);

	// D3 handles (not reactive state)
	let simulation: d3.Simulation<SimNode, SimLink> | null = null;
	let zoomBehavior: d3.ZoomBehavior<SVGSVGElement, unknown> | null = null;
	let gMain: d3.Selection<SVGGElement, unknown, null, unknown> | null = null;
	let simNodes: SimNode[] = [];
	let simLinks: SimLink[] = [];

	// ── Scales ─────────────────────────────────────────────────────
	const heightScale = d3.scaleSqrt().domain([0, 100]).range([44, 80]).clamp(true);

	// ── Edge styles ────────────────────────────────────────────────
	const edgeStyle: Record<string, { stroke: string; strokeWidth: number; dasharray?: string }> = {
		data_flow:   { stroke: 'var(--color-cs-success)',     strokeWidth: 2 },
		sequential:  { stroke: 'var(--color-cs-accent)',      strokeWidth: 2 },
		shared_env:  { stroke: 'var(--color-cs-running)',     strokeWidth: 1.5, dasharray: '6 3' },
		manual:      { stroke: 'var(--color-cs-border)',      strokeWidth: 1 },
		shared_tags: { stroke: 'var(--color-cs-text-muted)', strokeWidth: 1, dasharray: '4 4' },
	};

	function statusColor(status?: string): string {
		const m: Record<string, string> = {
			success: 'var(--color-cs-success)',
			failure: 'var(--color-cs-error)',
			running: 'var(--color-cs-running)',
			timeout: 'var(--color-cs-warning)',
		};
		return m[status ?? ''] ?? 'var(--color-cs-border)';
	}

	// ── Build path for curved edge ──────────────────────────────────
	function curvePath(d: SimLink): string {
		const s = d.source as SimNode, t = d.target as SimNode;
		if (!s.x || !t.x) return '';
		const dx = (t.x - s.x) * 0.4;
		const sx = s.x + (s.nodeWidth ?? 144) / 2;
		const tx = t.x - (t.nodeWidth ?? 144) / 2;
		return `M${sx},${s.y} C${sx + dx},${s.y} ${tx - dx},${t.y} ${tx},${t.y}`;
	}

	// ── Data loading & simulation init ─────────────────────────────
	async function loadGraph() {
		loading = true;
		try {
			const [graphData, runsData] = await Promise.all([api.graph(), api.runs.list(undefined, 500)]);

			// Run counts + last status per script
			const runCounts = new Map<string, number>();
			const lastStatus = new Map<string, string>();
			for (const r of runsData) {
				runCounts.set(r.script_id, (runCounts.get(r.script_id) ?? 0) + 1);
				if (r.start_time) {
					const prev = lastStatus.get(r.script_id);
					if (!prev) lastStatus.set(r.script_id, r.status);
				}
			}

			// Script nodes only (language/tag nodes not in D3 graph)
			simNodes = graphData.nodes
				.filter(n => n.type === 'script')
				.map(n => {
					const count = runCounts.get(n.id) ?? 0;
					const h = heightScale(count);
					return { id: n.id, name: (n.data.name as string) ?? n.id,
						runtime: (n.data.runtime as string) ?? '?',
						description: (n.data.description as string | null) ?? null,
						runCount: count, nodeWidth: h * 2.57, nodeHeight: h,
						lastStatus: lastStatus.get(n.id) };
				});

			// Explicit edges (script-script only)
			const scriptIds = new Set(simNodes.map(n => n.id));
			simLinks = graphData.edges
				.filter(e => scriptIds.has(e.source) && scriptIds.has(e.target))
				.map(e => ({ id: e.id, source: e.source, target: e.target,
					relation: e.type, implicit: false }));

			// Implicit edges from shared tags (computed client-side)
			const tagEdges = graphData.edges.filter(e => e.type === 'labeled_as');
			const scriptTagMap = new Map<string, Set<string>>();
			for (const e of tagEdges) {
				if (!scriptTagMap.has(e.source)) scriptTagMap.set(e.source, new Set());
				scriptTagMap.get(e.source)!.add(e.target);
			}
			const nodeArr = simNodes;
			for (let i = 0; i < nodeArr.length; i++) {
				for (let j = i + 1; j < nodeArr.length; j++) {
					const a = nodeArr[i], b = nodeArr[j];
					const ta = scriptTagMap.get(a.id) ?? new Set<string>();
					const tb = scriptTagMap.get(b.id) ?? new Set<string>();
					const shared = [...ta].filter(t => tb.has(t));
					if (shared.length >= 2) {
						simLinks.push({ id: `imp-${a.id}-${b.id}`, source: a.id, target: b.id,
							relation: 'shared_tags', implicit: true });
					}
				}
			}

			nodeCount = simNodes.length;
			edgeCount = simLinks.filter(l => !l.implicit).length;
			initSimulation();
		} finally { loading = false; }
	}

	function initSimulation() {
		if (!svgEl) return;
		const W = svgEl.clientWidth, H = svgEl.clientHeight;

		// Seed positions in a grid to reduce initial chaos
		const cols = Math.ceil(Math.sqrt(simNodes.length));
		simNodes.forEach((n, i) => {
			if (!n.x) { n.x = 100 + (i % cols) * 200; n.y = 100 + Math.floor(i / cols) * 160; }
		});

		// Arrowhead defs
		const svgSel = d3.select(svgEl);
		svgSel.select('defs').remove();
		const defs = svgSel.append('defs');
		['cs-success', 'cs-accent'].forEach(c => {
			defs.append('marker').attr('id', `arrow-${c}`)
				.attr('viewBox', '0 -5 10 10').attr('refX', 10).attr('refY', 0)
				.attr('markerWidth', 6).attr('markerHeight', 6).attr('orient', 'auto')
				.append('path').attr('d', 'M0,-5L10,0L0,5').attr('fill', `var(--color-${c})`);
		});

		// Inner group for zoom/pan
		svgSel.select('g.g-main').remove();
		gMain = svgSel.append('g').attr('class', 'g-main').style('will-change', 'transform');

		// Zoom behaviour
		zoomBehavior = d3.zoom<SVGSVGElement, unknown>()
			.scaleExtent([0.2, 3])
			.on('zoom', (e) => gMain!.attr('transform', e.transform));
		svgSel.call(zoomBehavior);
		svgSel.on('dblclick.zoom', () => resetZoom());

		// Simulation
		const useCollision = simNodes.length <= 80;
		simulation = d3.forceSimulation<SimNode>(simNodes)
			.force('link', d3.forceLink<SimNode, SimLink>(simLinks)
				.id(d => d.id)
				.distance(d => d.implicit ? 220 : 140)
				.strength(d => d.implicit ? 0.3 : 0.6))
			.force('charge', d3.forceManyBody<SimNode>().strength(-450).distanceMax(400))
			.force('center', d3.forceCenter(W / 2, H / 2).strength(0.05))
			.force('collision', useCollision
				? d3.forceCollide<SimNode>(d => Math.hypot(d.nodeWidth, d.nodeHeight) / 2 + 20)
				: null)
			.alphaDecay(0.028)
			.velocityDecay(0.4)
			.on('tick', ticked);

		renderElements();
		// Fit view after simulation cools
		setTimeout(resetZoom, 1800);
	}

	function renderElements() {
		if (!gMain) return;
		const visibleLinks = $showImplicitEdges ? simLinks : simLinks.filter(l => !l.implicit);

		// ── Edges ──────────────────────────────────────────────────
		gMain.select('g.edges').remove();
		const edgeG = gMain.append('g').attr('class', 'edges');
		edgeG.selectAll<SVGPathElement, SimLink>('path.edge')
			.data(visibleLinks, d => d.id)
			.join('path')
			.attr('class', 'edge')
			.attr('fill', 'none')
			.attr('stroke', d => edgeStyle[d.relation]?.stroke ?? 'var(--color-cs-border)')
			.attr('stroke-width', d => edgeStyle[d.relation]?.strokeWidth ?? 1)
			.attr('stroke-dasharray', d => edgeStyle[d.relation]?.dasharray ?? null)
			.attr('opacity', d => d.implicit ? 0.35 : 0.85)
			.attr('marker-end', d => {
				if (d.relation === 'data_flow') return 'url(#arrow-cs-success)';
				if (d.relation === 'sequential') return 'url(#arrow-cs-accent)';
				return null;
			})
			.on('click', (event, d) => {
				const src = (d.source as SimNode).name, tgt = (d.target as SimNode).name;
				tooltip = { x: event.offsetX, y: event.offsetY, text: `${src} → ${tgt} (${d.relation})` };
				event.stopPropagation();
			});

		// ── Nodes ──────────────────────────────────────────────────
		gMain.select('g.nodes').remove();
		const nodeG = gMain.append('g').attr('class', 'nodes');

		const nodeEnter = nodeG.selectAll<SVGGElement, SimNode>('g.node')
			.data(simNodes, d => d.id)
			.join('g')
			.attr('class', d => {
				let cls = 'node cursor-pointer';
				if (d.lastStatus === 'running') cls += ' node--running';
				else if (d.lastStatus === 'failure') cls += ' node--error';
				if ($graphSelectedNode === d.id) cls += ' node--selected';
				return cls;
			})
			.call(d3.drag<SVGGElement, SimNode>()
				.on('start', (event, d) => { if (!event.active) simulation?.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
				.on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
				.on('end', (event, d) => {
					if (!event.active) simulation?.alphaTarget(0);
					setTimeout(() => { d.fx = null; d.fy = null; }, 2000);
				}))
			.on('mouseenter', (_, d) => dimExcept(d.id))
			.on('mouseleave', () => undim())
			.on('click', (event, d) => {
				event.stopPropagation();
				graphSelectedNode.set(d.id);
				flyoutOpen.set(true);
				tooltip = null;
			});

		// Background rect
		nodeEnter.append('rect')
			.attr('rx', 8).attr('ry', 8)
			.attr('width', d => d.nodeWidth)
			.attr('height', d => d.nodeHeight)
			.attr('x', d => -d.nodeWidth / 2)
			.attr('y', d => -d.nodeHeight / 2)
			.attr('fill', 'var(--color-cs-surface)')
			.attr('stroke', 'var(--color-cs-border)')
			.attr('stroke-width', 1);

		// Status dot
		nodeEnter.append('circle')
			.attr('r', 4)
			.attr('cx', d => d.nodeWidth / 2 - 10)
			.attr('cy', d => -d.nodeHeight / 2 + 10)
			.attr('fill', d => statusColor(d.lastStatus));

		// Script name
		nodeEnter.append('text')
			.attr('text-anchor', 'middle').attr('dominant-baseline', 'middle')
			.attr('y', d => -6)
			.attr('font-family', 'JetBrains Mono, monospace')
			.attr('font-size', 11)
			.attr('fill', 'var(--color-cs-text)')
			.text(d => d.name.length > 20 ? d.name.slice(0, 18) + '…' : d.name);

		// Meta line (runtime + run count)
		nodeEnter.append('text')
			.attr('text-anchor', 'middle').attr('dominant-baseline', 'middle')
			.attr('y', d => 10)
			.attr('font-family', 'Inter, system-ui, sans-serif')
			.attr('font-size', 10)
			.attr('fill', 'var(--color-cs-text-muted)')
			.text(d => `${d.runtime.toUpperCase()} · ${d.runCount} runs`);
	}

	function ticked() {
		if (!gMain) return;
		gMain.selectAll<SVGPathElement, SimLink>('path.edge').attr('d', curvePath);
		gMain.selectAll<SVGGElement, SimNode>('g.node').attr('transform', d => `translate(${d.x},${d.y})`);
		// Update selected class reactively
		gMain.selectAll<SVGGElement, SimNode>('g.node').classed('node--selected', d => d.id === $graphSelectedNode);
	}

	function dimExcept(nodeId: string) {
		if (!gMain) return;
		const linkedIds = new Set<string>([nodeId]);
		simLinks.forEach(l => {
			const s = (l.source as SimNode).id, t = (l.target as SimNode).id;
			if (s === nodeId) linkedIds.add(t);
			if (t === nodeId) linkedIds.add(s);
		});
		gMain.selectAll<SVGGElement, SimNode>('g.node').classed('dimmed', d => !linkedIds.has(d.id));
		gMain.selectAll<SVGPathElement, SimLink>('path.edge')
			.attr('opacity', d => {
				const s = (d.source as SimNode).id, t = (d.target as SimNode).id;
				return (s === nodeId || t === nodeId) ? 1 : 0.08;
			});
	}

	function undim() {
		if (!gMain) return;
		gMain.selectAll('.node').classed('dimmed', false);
		gMain.selectAll<SVGPathElement, SimLink>('path.edge')
			.attr('opacity', d => d.implicit ? 0.35 : 0.85);
	}

	function resetZoom() {
		if (!svgEl || !zoomBehavior || !simNodes.length) return;
		const W = svgEl.clientWidth, H = svgEl.clientHeight;
		const xs = simNodes.map(n => n.x ?? 0), ys = simNodes.map(n => n.y ?? 0);
		const x0 = Math.min(...xs) - 80, x1 = Math.max(...xs) + 80;
		const y0 = Math.min(...ys) - 60, y1 = Math.max(...ys) + 60;
		const scale = Math.min(0.95, 0.95 / Math.max((x1-x0)/W, (y1-y0)/H));
		const tx = (W - scale*(x0+x1)) / 2, ty = (H - scale*(y0+y1)) / 2;
		d3.select(svgEl).transition().duration(500).call(
			zoomBehavior.transform, d3.zoomIdentity.translate(tx, ty).scale(scale)
		);
	}

	function smartZoomTo(nodeId: string) {
		if (!svgEl || !zoomBehavior || !simNodes.length) return;
		const W = svgEl.clientWidth, H = svgEl.clientHeight;
		const linkedIds = new Set([nodeId]);
		simLinks.forEach(l => {
			const s = (l.source as SimNode).id, t = (l.target as SimNode).id;
			if (s === nodeId) linkedIds.add(t);
			if (t === nodeId) linkedIds.add(s);
		});
		const focus = simNodes.filter(n => linkedIds.has(n.id));
		if (!focus.length) return;
		const xs = focus.map(n => n.x ?? 0), ys = focus.map(n => n.y ?? 0);
		const x0 = Math.min(...xs) - 100, x1 = Math.max(...xs) + 100;
		const y0 = Math.min(...ys) - 80,  y1 = Math.max(...ys) + 80;
		const scale = Math.min(1.8, 0.9 / Math.max((x1-x0)/W, (y1-y0)/H));
		const tx = (W - scale*(x0+x1)) / 2, ty = (H - scale*(y0+y1)) / 2;
		d3.select(svgEl).transition().duration(400).call(
			zoomBehavior.transform, d3.zoomIdentity.translate(tx, ty).scale(scale)
		);
	}

	// Watch graphSelectedNode for smart zoom
	$effect(() => {
		const id = $graphSelectedNode;
		if (id && !loading) setTimeout(() => smartZoomTo(id), 50);
	});

	// Re-render edges when implicit visibility changes
	$effect(() => {
		$showImplicitEdges; // track
		if (!loading) renderElements();
	});

	onMount(() => { loadGraph(); });
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

	const relationColors: Record<string, string> = {
		data_flow: 'text-cs-success', shared_env: 'text-cs-running',
		manual: 'text-cs-text-muted', sequential: 'text-cs-accent'
	};
</script>

<div class="relative flex h-full flex-col" style="background: var(--color-cs-bg);">
	<!-- Toolbar -->
	<div class="flex flex-shrink-0 items-center gap-2 border-b border-cs-border px-4 py-2"
		style="background: var(--color-cs-surface);">
		<GitBranch size={14} strokeWidth={2} style="color: var(--color-cs-text-muted);" />
		<h2 class="font-mono text-xs font-semibold text-cs-text">Knowledge Graph</h2>
		<div class="flex-1"></div>
		<button class="ghost-btn flex items-center gap-1.5 text-xs"
			onclick={() => (showAddEdge = !showAddEdge)}>
			<Plus size={12} strokeWidth={2} /> Add Edge
		</button>
	</div>

	<!-- Add Edge panel -->
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

	<!-- Canvas + Edge list -->
	<div class="flex flex-1 overflow-hidden">
		<!-- SVG Graph canvas -->
		<div
			class="relative flex-1 overflow-hidden"
			role="presentation"
			onclick={() => (tooltip = null)}
			onkeydown={(e) => e.key === 'Escape' && (tooltip = null)}
		>
			{#if loading}
				<div class="flex h-full items-center justify-center text-sm text-cs-text-muted">
					Loading graph…
				</div>
			{:else}
				<svg bind:this={svgEl} class="h-full w-full" style="cursor: grab;"></svg>
				<GraphControls {nodeCount} {edgeCount} onResetZoom={resetZoom} />
			{/if}

			<!-- Edge tooltip -->
			{#if tooltip}
				<div
					class="pointer-events-none absolute z-20 rounded border border-cs-border px-2.5 py-1.5 text-[11px] text-cs-text"
					style="background: var(--color-cs-surface); left: {tooltip.x + 12}px; top: {tooltip.y + 8}px;"
				>{tooltip.text}</div>
			{/if}
		</div>

		<!-- Edge list panel -->
		<div class="w-56 flex-shrink-0 overflow-y-auto border-l border-cs-border p-3"
			style="background: var(--color-cs-surface);">
			<h4 class="mb-2 text-[10px] font-semibold uppercase tracking-wider text-cs-text-muted">
				Connections
			</h4>
			{#if $edges.length === 0}
				<p class="text-xs text-cs-text-muted">No connections yet</p>
			{:else}
				{#each $edges as edge}
					{@const src = $scripts.find(s => s.id === edge.source_id)}
					{@const tgt = $scripts.find(s => s.id === edge.target_id)}
					<div class="mb-2 flex items-start gap-2 rounded p-2 text-xs"
						style="background: var(--color-cs-surface-2);">
						<div class="min-w-0 flex-1">
							<div class="truncate font-mono text-cs-text">{src?.name ?? '?'}</div>
							<div class="my-0.5 {relationColors[edge.relation] ?? 'text-cs-text-muted'} text-[10px]">
								↓ {edge.relation}
							</div>
							<div class="truncate font-mono text-cs-text">{tgt?.name ?? '?'}</div>
						</div>
						<button class="mt-0.5 text-cs-text-muted transition-colors hover:text-cs-error"
							onclick={() => removeEdge(edge.id)}>
							<Trash2 size={11} />
						</button>
					</div>
				{/each}
			{/if}
		</div>
	</div>
</div>
