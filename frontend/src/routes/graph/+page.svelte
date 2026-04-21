<script lang="ts">
	import { onMount } from 'svelte';
	import { SvelteFlow, Controls, Background, MiniMap, type Node, type Edge as FlowEdge, type Connection, MarkerType, Position } from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import { scripts, edges, loadEdges, activeScriptId, drawerOpen } from '$lib/stores';
	import * as api from '$lib/api/client';
	import { Plus, Trash2, GitBranch } from 'lucide-svelte';
	import { goto } from '$app/navigation';
	import ScriptNode from '$lib/components/graph/ScriptNode.svelte';
	import TagNode from '$lib/components/graph/TagNode.svelte';
	import LanguageNode from '$lib/components/graph/LanguageNode.svelte';

	const nodeTypes = { script: ScriptNode, tag: TagNode, language: LanguageNode };

	let flowNodes = $state<Node[]>([]);
	let flowEdges = $state<FlowEdge[]>([]);
	let loading = $state(true);

	// Edge creation dialog
	let showEdgeDialog = $state(false);
	let pendingConnection = $state<{ source: string; target: string } | null>(null);
	let edgeRelation = $state<'data_flow' | 'shared_env' | 'manual' | 'sequential'>('sequential');

	// Manual edge form
	let showAddEdge = $state(false);
	let sourceId = $state('');
	let targetId = $state('');
	let manualRelation = $state<'data_flow' | 'shared_env' | 'manual' | 'sequential'>('manual');

	onMount(async () => {
		await loadGraph();
	});

	async function loadGraph() {
		loading = true;
		try {
			const graphData = await api.graph();
			autoLayout(graphData.nodes, graphData.edges);
		} finally {
			loading = false;
		}
	}

	function autoLayout(
		rawNodes: { id: string; type: string; data: Record<string, unknown> }[],
		rawEdges: { id: string; source: string; target: string; type: string; data?: Record<string, unknown> }[]
	) {
		// Group by type for layout
		const scriptNodes = rawNodes.filter((n) => n.type === 'script');
		const tagNodes = rawNodes.filter((n) => n.type === 'tag');
		const langNodes = rawNodes.filter((n) => n.type === 'language');

		const nodes: Node[] = [];

		// Script nodes in a grid (center)
		const cols = Math.max(3, Math.ceil(Math.sqrt(scriptNodes.length)));
		scriptNodes.forEach((n, i) => {
			const col = i % cols;
			const row = Math.floor(i / cols);
			nodes.push({
				id: n.id,
				type: 'script',
				position: { x: 250 + col * 200, y: 80 + row * 120 },
				data: n.data
			});
		});

		// Language nodes on the left
		langNodes.forEach((n, i) => {
			nodes.push({
				id: n.id,
				type: 'language',
				position: { x: 30, y: 100 + i * 100 },
				data: n.data
			});
		});

		// Tag nodes on the right
		const maxScriptX = 250 + cols * 200;
		tagNodes.forEach((n, i) => {
			nodes.push({
				id: n.id,
				type: 'tag',
				position: { x: maxScriptX + 80, y: 80 + i * 60 },
				data: n.data
			});
		});

		// Edges with styling per type
		const edgeStyleMap: Record<string, Partial<FlowEdge>> = {
			data_flow: { animated: true, style: 'stroke: #34d399; stroke-width: 2;' },
			shared_env: { style: 'stroke: #818cf8; stroke-width: 2;' },
			manual: { style: 'stroke: #71717a; stroke-width: 1.5;' },
			sequential: { animated: true, style: 'stroke: #fbbf24; stroke-width: 2;' },
			labeled_as: { style: 'stroke: #34d399; stroke-width: 1; stroke-dasharray: 5 5;' },
			written_in: { style: 'stroke: #3f3f46; stroke-width: 1;' }
		};

		const edges: FlowEdge[] = rawEdges.map((e) => ({
			id: e.id,
			source: e.source,
			target: e.target,
			type: 'default',
			markerEnd: e.type === 'data_flow' || e.type === 'sequential' ? { type: MarkerType.ArrowClosed, color: e.type === 'data_flow' ? '#34d399' : '#fbbf24' } : undefined,
			label: e.type === 'data_flow' || e.type === 'shared_env' || e.type === 'manual' || e.type === 'sequential' ? e.type.replace('_', ' ') : '',
			...(edgeStyleMap[e.type] ?? {}),
			data: e.data
		}));

		flowNodes = nodes;
		flowEdges = edges;
	}

	// Click script node → select + navigate
	function handleNodeClick({ node }: { node: Node }) {
		if (node.type === 'script') {
			activeScriptId.set(node.id);
			drawerOpen.set(true);
			goto(`/scripts/${node.id}`);
		}
	}

	// Drag-and-drop connection between script nodes
	function handleConnect(conn: Connection) {
		if (!conn.source || !conn.target || conn.source === conn.target) return;
		const srcNode = flowNodes.find((n) => n.id === conn.source);
		const tgtNode = flowNodes.find((n) => n.id === conn.target);
		if (srcNode?.type !== 'script' || tgtNode?.type !== 'script') return;

		pendingConnection = { source: conn.source, target: conn.target };
		edgeRelation = 'sequential';
		showEdgeDialog = true;
	}

	async function confirmConnection() {
		if (!pendingConnection) return;
		await api.edges.create({
			source_id: pendingConnection.source,
			target_id: pendingConnection.target,
			relation: edgeRelation
		});
		showEdgeDialog = false;
		pendingConnection = null;
		await loadGraph();
	}

	function cancelConnection() {
		showEdgeDialog = false;
		pendingConnection = null;
	}

	async function addEdge() {
		if (!sourceId || !targetId || sourceId === targetId) return;
		await api.edges.create({ source_id: sourceId, target_id: targetId, relation: manualRelation });
		showAddEdge = false;
		sourceId = '';
		targetId = '';
		await loadGraph();
	}

	async function removeEdge(id: string) {
		await api.edges.delete(id);
		await loadEdges();
		await loadGraph();
	}

	const relationColors: Record<string, string> = {
		data_flow: 'text-accent',
		shared_env: 'text-indigo',
		manual: 'text-text-muted',
		sequential: 'text-warning'
	};
</script>

<div class="flex h-full flex-col">
	<div class="flex items-center gap-2 border-b border-border px-4 py-2">
		<GitBranch size={14} strokeWidth={2} class="text-text-dim" />
		<h2 class="text-sm font-medium">Knowledge Graph</h2>
		<div class="flex-1"></div>
		<button class="ghost-btn flex items-center gap-1.5" onclick={() => (showAddEdge = !showAddEdge)}>
			<Plus size={13} strokeWidth={2} /> Add Edge
		</button>
	</div>

	{#if showAddEdge}
		<div class="flex items-end gap-2 border-b border-border-subtle bg-bg-surface px-4 py-3">
			<div>
				<label class="mb-0.5 block text-xs text-text-dim">Source</label>
				<select class="input text-xs" bind:value={sourceId}>
					<option value="">Select…</option>
					{#each $scripts as s}
						<option value={s.id}>{s.name}</option>
					{/each}
				</select>
			</div>
			<div>
				<label class="mb-0.5 block text-xs text-text-dim">Relation</label>
				<select class="input text-xs" bind:value={manualRelation}>
					<option value="data_flow">Data Flow</option>
					<option value="shared_env">Shared Env</option>
					<option value="manual">Manual</option>
					<option value="sequential">Sequential</option>
				</select>
			</div>
			<div>
				<label class="mb-0.5 block text-xs text-text-dim">Target</label>
				<select class="input text-xs" bind:value={targetId}>
					<option value="">Select…</option>
					{#each $scripts as s}
						<option value={s.id}>{s.name}</option>
					{/each}
				</select>
			</div>
			<button class="btn-primary text-xs" onclick={addEdge}>Add</button>
		</div>
	{/if}

	<!-- Connection relation picker dialog -->
	{#if showEdgeDialog}
		<div class="absolute inset-0 z-50 flex items-center justify-center bg-black/50">
			<div class="rounded-lg border border-border bg-bg-elevated p-4 shadow-xl">
				<h3 class="mb-3 text-sm font-medium">Create Connection</h3>
				<div class="mb-3">
					<label class="mb-1 block text-xs text-text-dim">Relation Type</label>
					<select class="input text-xs" bind:value={edgeRelation}>
						<option value="sequential">Sequential</option>
						<option value="data_flow">Data Flow</option>
						<option value="shared_env">Shared Env</option>
						<option value="manual">Manual</option>
					</select>
				</div>
				<div class="flex gap-2">
					<button class="btn-primary text-xs" onclick={confirmConnection}>Create</button>
					<button class="ghost-btn text-xs" onclick={cancelConnection}>Cancel</button>
				</div>
			</div>
		</div>
	{/if}

	<div class="flex flex-1 overflow-hidden">
		<!-- Svelte Flow Graph -->
		<div class="flex-1">
			{#if loading}
				<div class="flex h-full items-center justify-center text-text-dim">Loading graph…</div>
			{:else}
				<SvelteFlow
					nodes={flowNodes}
					edges={flowEdges}
					{nodeTypes}
					fitView
					colorMode="dark"
					onnodeclick={handleNodeClick}
					onconnect={handleConnect}
					defaultEdgeOptions={{ type: 'default' }}
				>
					<Controls />
					<Background />
					<MiniMap />
				</SvelteFlow>
			{/if}
		</div>

		<!-- Edge List -->
		<div class="w-60 shrink-0 overflow-y-auto border-l border-border bg-bg-elevated p-3">
			<h4 class="mb-2 text-xs font-medium uppercase tracking-wider text-text-dim">Script Edges</h4>
			{#if $edges.length === 0}
				<p class="text-xs text-text-dim">No connections yet</p>
			{:else}
				{#each $edges as edge}
					{@const src = $scripts.find((s) => s.id === edge.source_id)}
					{@const tgt = $scripts.find((s) => s.id === edge.target_id)}
					<div class="mb-2 flex items-center gap-2 rounded bg-bg-surface p-2 text-xs">
						<div class="min-w-0 flex-1">
							<span class="font-mono">{src?.name ?? '?'}</span>
							<span class={relationColors[edge.relation]}> → </span>
							<span class="font-mono">{tgt?.name ?? '?'}</span>
							<div class={`mt-0.5 ${relationColors[edge.relation]}`}>{edge.relation}</div>
						</div>
						<button class="ghost-btn p-0.5 text-danger" onclick={() => removeEdge(edge.id)}>
							<Trash2 size={11} />
						</button>
					</div>
				{/each}
			{/if}
		</div>
	</div>
</div>
