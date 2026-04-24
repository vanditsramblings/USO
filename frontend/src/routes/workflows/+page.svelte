<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import {
		SvelteFlow,
		Controls,
		Background,
		BackgroundVariant,
		type Node,
		type Edge,
		type Connection
	} from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import { Plus, Trash2, Zap, Play, Square, X, ChevronRight } from 'lucide-svelte';
	import * as api from '$lib/api/client';
	import { scripts, loadWorkflows, workflows } from '$lib/stores';
	import type { Workflow, WorkflowNode as WFNode } from '$lib/types';
	import WorkflowNode from '$lib/components/WorkflowNode.svelte';

	// ─── Node types registration ──────────────────────────────────────────────────
	const nodeTypes = { scriptNode: WorkflowNode };

	// ─── State ───────────────────────────────────────────────────────────────────
	let loading = $state(true);
	let showCreate = $state(false);
	let newName = $state('');
	let newDesc = $state('');
	let creating = $state(false);

	let selectedWf = $state<Workflow | null>(null);
	let addNodeScriptId = $state('');

	let nodes = $state<Node[]>([]);
	let edges = $state<Edge[]>([]);

	let executing = $state(false);
	let nodeStatuses = $state<Record<string, string>>({});
	let executionProgress = $state({ completed: 0, total: 0 });
	let ws: WebSocket | null = null;

	type PanelNode = { backendId: string; label: string; config: Record<string, string> };
	let panelNode = $state<PanelNode | null>(null);
	let panelConfigText = $state('');
	let panelSaving = $state(false);

	let errorMsg = $state('');

	// Derived: script info for the currently open panel node
	const panelScriptInfo = $derived(
		panelNode
			? (() => {
					const nodeInfo = selectedWf?.nodes.find((n) => n.id === panelNode?.backendId);
					return $scripts.find((s) => s.id === nodeInfo?.script_id) ?? null;
				})()
			: null
	);

	// ─── Lifecycle ────────────────────────────────────────────────────────────────
	onMount(async () => {
		await loadWorkflows();
		loading = false;
	});

	onDestroy(() => { ws?.close(); });

	// ─── Helpers: map backend → XYFlow ───────────────────────────────────────────
	function buildNodes(wf: Workflow, statuses: Record<string, string>): Node[] {
		return wf.nodes.map((n) => {
			const script = $scripts.find((s) => s.id === n.script_id);
			return {
				id: n.id,
				type: 'scriptNode',
				position: { x: n.position_x, y: n.position_y },
				data: {
					script,
					config: n.config,
					status: (statuses[n.id] ?? undefined) as never,
					onDelete: () => deleteNode(n.id),
					onClick: () => openPanel(n)
				}
			} satisfies Node;
		});
	}

	function buildEdges(wf: Workflow): Edge[] {
		return wf.edges.map((e) => ({
			id: e.id,
			source: e.source_node_id,
			target: e.target_node_id,
			animated: false,
			style: 'stroke:#34d399;stroke-width:2px;',
			markerEnd: { type: 'arrowclosed', color: '#34d399' }
		}));
	}

	function syncToFlow(wf: Workflow) {
		nodes = buildNodes(wf, nodeStatuses);
		edges = buildEdges(wf);
	}

	// ─── Workflow CRUD ────────────────────────────────────────────────────────────
	async function createWorkflow() {
		if (!newName) return;
		creating = true;
		errorMsg = '';
		try {
			const wf = await api.workflows.create({ name: newName, description: newDesc });
			await loadWorkflows();
			await selectWorkflow(wf);
			showCreate = false;
			newName = '';
			newDesc = '';
		} catch (e) {
			errorMsg = String(e);
		} finally {
			creating = false;
		}
	}

	async function deleteWorkflow(id: string) {
		if (!confirm('Delete this workflow?')) return;
		await api.workflows.delete(id);
		if (selectedWf?.id === id) {
			selectedWf = null;
			nodes = [];
			edges = [];
		}
		await loadWorkflows();
	}

	async function selectWorkflow(wf: Workflow) {
		const fresh = await api.workflows.get(wf.id);
		selectedWf = fresh;
		nodeStatuses = {};
		executionProgress = { completed: 0, total: 0 };
		executing = false;
		ws?.close();
		syncToFlow(fresh);
	}

	// ─── Node management ──────────────────────────────────────────────────────────
	async function addNode() {
		if (!selectedWf || !addNodeScriptId) return;
		errorMsg = '';
		const nodeCount = selectedWf.nodes.length;
		try {
			await api.workflows.addNode(selectedWf.id, {
				script_id: addNodeScriptId,
				position_x: 80 + (nodeCount % 4) * 220,
				position_y: 80 + Math.floor(nodeCount / 4) * 160
			});
			const fresh = await api.workflows.get(selectedWf.id);
			selectedWf = fresh;
			syncToFlow(fresh);
			addNodeScriptId = '';
		} catch (e) {
			errorMsg = String(e);
		}
	}

	async function deleteNode(nodeId: string) {
		if (!selectedWf) return;
		try {
			await api.workflows.deleteNode(selectedWf.id, nodeId);
			const fresh = await api.workflows.get(selectedWf.id);
			selectedWf = fresh;
			syncToFlow(fresh);
			if (panelNode?.backendId === nodeId) panelNode = null;
		} catch (e) {
			errorMsg = String(e);
		}
	}

	async function onNodeDragStop({ targetNode }: { targetNode: Node | null; nodes: Node[]; event: MouseEvent | TouchEvent }) {
		if (!selectedWf || !targetNode) return;
		const n = targetNode;
		try {
			await api.workflows.updateNode(selectedWf.id, n.id, {
				position_x: Math.round(n.position.x),
				position_y: Math.round(n.position.y)
			});
			const idx = selectedWf.nodes.findIndex((bn) => bn.id === n.id);
			if (idx >= 0) {
				selectedWf.nodes[idx].position_x = Math.round(n.position.x);
				selectedWf.nodes[idx].position_y = Math.round(n.position.y);
			}
		} catch {
			// Non-critical
		}
	}

	// ─── Edge management ──────────────────────────────────────────────────────────
	async function onConnect(connection: Connection) {
		if (!selectedWf) return;
		const { source, target } = connection;
		if (!source || !target) return;
		if (selectedWf.edges.some((e) => e.source_node_id === source && e.target_node_id === target))
			return;
		try {
			await api.workflows.addEdge(selectedWf.id, {
				source_node_id: source,
				target_node_id: target,
				condition: { type: 'status', value: 'success' }
			});
			const fresh = await api.workflows.get(selectedWf.id);
			selectedWf = fresh;
			syncToFlow(fresh);
		} catch (e) {
			errorMsg = String(e);
		}
	}

	async function onEdgeClick({ edge }: { edge: Edge; event: MouseEvent }) {
		const edgeId = edge.id;
		if (!selectedWf) return;
		if (!confirm('Remove this connection?')) return;
		try {
			await api.workflows.deleteEdge(selectedWf.id, edgeId);
			const fresh = await api.workflows.get(selectedWf.id);
			selectedWf = fresh;
			syncToFlow(fresh);
		} catch (e) {
			errorMsg = String(e);
		}
	}

	// ─── Config side panel ────────────────────────────────────────────────────────
	function openPanel(backendNode: WFNode) {
		const config = (backendNode.config ?? {}) as Record<string, string>;
		const script = $scripts.find((s) => s.id === backendNode.script_id);
		panelNode = { backendId: backendNode.id, label: script?.name ?? backendNode.id, config };
		panelConfigText = Object.entries(config)
			.map(([k, v]) => `${k}=${v}`)
			.join('\n');
	}

	async function savePanel() {
		if (!panelNode || !selectedWf) return;
		panelSaving = true;
		try {
			const config: Record<string, string> = {};
			for (const line of panelConfigText.split('\n')) {
				const eqIdx = line.indexOf('=');
				if (eqIdx < 1) continue;
				const k = line.slice(0, eqIdx).trim();
				const v = line.slice(eqIdx + 1).trim();
				if (k) config[k] = v;
			}
			await api.workflows.updateNode(selectedWf.id, panelNode.backendId, {
				config: Object.keys(config).length > 0 ? config : null
			});
			const fresh = await api.workflows.get(selectedWf.id);
			selectedWf = fresh;
			syncToFlow(fresh);
			panelNode = null;
		} catch (e) {
			errorMsg = String(e);
		} finally {
			panelSaving = false;
		}
	}

	// ─── Execution ────────────────────────────────────────────────────────────────
	function executeWorkflow() {
		if (!selectedWf || executing) return;
		executing = true;
		nodeStatuses = {};
		executionProgress = { completed: 0, total: selectedWf.nodes.length };
		nodes = buildNodes(selectedWf, {});

		const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
		ws = new WebSocket(`${proto}//${location.host}/api/workflows/${selectedWf!.id}/ws`);

		ws.onmessage = (event) => {
			const data = JSON.parse(event.data);
			if (data.type === 'workflow_start') {
				for (const nodeId of data.order) nodeStatuses[nodeId] = 'pending';
				nodeStatuses = { ...nodeStatuses };
				nodes = buildNodes(selectedWf!, nodeStatuses);
			} else if (data.type === 'node_start') {
				nodeStatuses[data.node_id] = 'running';
				nodeStatuses = { ...nodeStatuses };
				nodes = buildNodes(selectedWf!, nodeStatuses);
			} else if (data.type === 'node_complete') {
				nodeStatuses[data.node_id] = data.status;
				nodeStatuses = { ...nodeStatuses };
				executionProgress.completed += 1;
				executionProgress = { ...executionProgress };
				nodes = buildNodes(selectedWf!, nodeStatuses);
			} else if (data.type === 'workflow_complete') {
				executing = false;
				ws?.close();
			}
		};
		ws.onerror = () => { executing = false; };
		ws.onclose = () => { executing = false; };
	}

	function stopExecution() {
		ws?.close();
		executing = false;
	}
</script>

<div class="flex h-full flex-col">
	<!-- Top bar -->
	<div class="flex items-center gap-2 border-b border-cs-border px-4 py-2">
		<Zap size={14} strokeWidth={2} class="text-cs-text-muted" />
		<h2 class="text-sm font-medium">Workflow DAGs</h2>
		<div class="flex-1"></div>

		{#if selectedWf && selectedWf.nodes.length > 0}
			{#if executing}
				<div class="flex items-center gap-2 text-xs text-cs-text-muted">
					<div class="h-1.5 w-24 overflow-hidden rounded-full bg-cs-surface-2">
						<div
							class="h-full rounded-full bg-cs-accent transition-all"
							style="width:{executionProgress.total
								? (executionProgress.completed / executionProgress.total) * 100
								: 0}%"
						></div>
					</div>
					{executionProgress.completed}/{executionProgress.total}
				</div>
				<button class="ghost-btn flex items-center gap-1.5 text-cs-error" onclick={stopExecution}>
					<Square size={13} strokeWidth={2} /> Stop
				</button>
			{:else}
				<button class="btn-primary flex items-center gap-1.5 text-xs" onclick={executeWorkflow}>
					<Play size={13} strokeWidth={2} /> Execute Chain
				</button>
				<button class="ghost-btn text-xs" onclick={() => goto(`/workflows/${selectedWf?.id}`)}>
					Pipeline View
				</button>
			{/if}
		{/if}

		<button class="ghost-btn flex items-center gap-1.5" onclick={() => (showCreate = !showCreate)}>
			<Plus size={13} strokeWidth={2} /> New Workflow
		</button>
	</div>

	<!-- Create form -->
	{#if showCreate}
		<div class="flex items-end gap-2 border-b border-cs-border bg-cs-surface-2 px-4 py-3">
			<div>
				<label for="wf-name" class="mb-0.5 block text-xs text-cs-text-muted">Name</label>
				<input id="wf-name" class="input text-xs" bind:value={newName} placeholder="pipeline-name" />
			</div>
			<div class="flex-1">
				<label for="wf-desc" class="mb-0.5 block text-xs text-cs-text-muted">Description</label>
				<input id="wf-desc" class="input text-xs" bind:value={newDesc} placeholder="Optional description" />
			</div>
			<button class="btn-primary text-xs" onclick={createWorkflow} disabled={creating}>Create</button>
		</div>
	{/if}

	{#if errorMsg}
		<div class="flex items-center gap-2 border-b border-cs-error/30 bg-cs-error/10 px-4 py-2 text-xs text-cs-error">
			<span class="flex-1">{errorMsg}</span>
			<button onclick={() => (errorMsg = '')} class="ghost-btn p-0.5"><X size={12} /></button>
		</div>
	{/if}

	<!-- Main layout -->
	<div class="flex flex-1 overflow-hidden">
		<!-- Workflow sidebar -->
		<div class="w-52 shrink-0 overflow-y-auto border-r border-cs-border bg-cs-surface">
			{#if loading}
				{#each Array(3) as _}
					<div class="animate-pulse border-b border-cs-border px-3 py-3">
						<div class="h-3 w-3/4 rounded bg-cs-surface-2"></div>
					</div>
				{/each}
			{:else if $workflows.length === 0}
				<div class="p-4 text-center text-xs text-cs-text-muted">No workflows yet</div>
			{:else}
				{#each $workflows as wf}
					<div
						class="flex w-full items-center justify-between border-b border-cs-border px-3 py-2.5 transition-colors hover:bg-cs-surface-2 {selectedWf?.id === wf.id ? 'bg-cs-surface-2' : ''}"
					>
						<button class="min-w-0 flex-1 text-left" onclick={() => selectWorkflow(wf)}>
							<div class="flex items-center gap-1.5">
								{#if selectedWf?.id === wf.id}
									<ChevronRight size={10} class="text-cs-accent shrink-0" />
								{/if}
								<span class="truncate text-sm font-medium">{wf.name}</span>
							</div>
							<div class="text-xs text-cs-text-muted">{wf.nodes.length} nodes · {wf.edges.length} edges</div>
						</button>
						<button class="ghost-btn p-0.5 text-cs-error" onclick={() => deleteWorkflow(wf.id)}>
							<Trash2 size={11} />
						</button>
					</div>
				{/each}
			{/if}
		</div>

		<!-- Canvas area -->
		<div class="relative flex flex-1 flex-col overflow-hidden">
			{#if !selectedWf}
				<div class="flex flex-1 items-center justify-center text-xs text-cs-text-muted">
					Select a workflow from the sidebar, or create a new one.
				</div>
			{:else}
				<!-- Add node toolbar -->
				<div class="flex items-center gap-2 border-b border-cs-border bg-cs-surface-2 px-3 py-2">
					<label for="add-node-script" class="shrink-0 text-xs text-cs-text-muted">Add node:</label>
					<select id="add-node-script" class="input flex-1 text-xs" bind:value={addNodeScriptId}>
						<option value="">Select script…</option>
						{#each $scripts as s}
							<option value={s.id}>{s.name} ({s.runtime})</option>
						{/each}
					</select>
					<button class="btn-primary text-xs" onclick={addNode} disabled={!addNodeScriptId}>
						<Plus size={12} /> Add
					</button>
					<span class="text-[10px] text-cs-text-muted hidden lg:block">
						Drag handles → connect · click edge → remove · click node → configure
					</span>
				</div>

				<!-- XYFlow canvas -->
				<div class="relative flex-1">
					<SvelteFlow
						{nodes}
						{edges}
						{nodeTypes}
						fitView
						snapGrid={[20, 20]}
						onconnect={onConnect}
						onnodedragstop={onNodeDragStop}
						onedgeclick={onEdgeClick}
						style="background: var(--color-cs-bg);"
						defaultEdgeOptions={{
							animated: false,
							style: 'stroke:#34d399;stroke-width:2px;',
							markerEnd: { type: 'arrowclosed', color: '#34d399' }
						}}
					>
						<Controls />
						<Background variant={BackgroundVariant.Dots} gap={20} size={1} patternColor="#333942" />
					</SvelteFlow>

					{#if selectedWf.nodes.length === 0}
						<div class="pointer-events-none absolute inset-0 flex items-center justify-center">
							<div class="rounded-lg border border-dashed border-cs-border px-8 py-6 text-center text-xs text-cs-text-muted">
								<div class="mb-1 text-lg">⬡</div>
								Add script nodes above, then drag handles to connect them.
							</div>
						</div>
					{/if}
				</div>
			{/if}
		</div>

		<!-- Config side panel -->
		{#if panelNode}
			<div class="flex w-72 shrink-0 flex-col border-l border-cs-border bg-cs-surface">
				<div class="flex items-center gap-2 border-b border-cs-border px-4 py-2">
					<span class="flex-1 truncate text-sm font-medium">{panelNode.label}</span>
					<button class="ghost-btn p-0.5" onclick={() => (panelNode = null)}>
						<X size={14} />
					</button>
				</div>

				<div class="flex-1 space-y-4 overflow-y-auto p-4">
					<div>
						<label for="panel-config" class="mb-1.5 block text-xs font-medium text-cs-text-muted">
							Environment / Config
							<span class="ml-1 font-normal">(KEY=VALUE, one per line)</span>
						</label>
						<textarea
							id="panel-config"
							class="input w-full font-mono text-xs leading-relaxed"
							rows={8}
							bind:value={panelConfigText}
							placeholder={"DB_HOST=localhost\nDB_PORT=5432\nDEBUG=true"}
						></textarea>
						<p class="mt-1 text-[10px] text-cs-text-muted">
							Passed as env vars when this node executes.
						</p>
					</div>

					{#if panelScriptInfo}
						<div class="rounded-md border border-cs-border bg-cs-surface-2 p-3">
							<div class="mb-2 text-[10px] font-medium uppercase tracking-wider text-cs-text-muted">Script Info</div>
							<div class="mb-1 flex items-center gap-2">
								<span class="font-mono text-xs font-medium">{panelScriptInfo.name}</span>
								<span class="rounded bg-cs-surface px-1 py-0.5 font-mono text-[10px] text-cs-text-muted">{panelScriptInfo.runtime}</span>
							</div>
							{#if panelScriptInfo.description}
								<p class="text-xs text-cs-text-muted">{panelScriptInfo.description}</p>
							{/if}
							{#if panelScriptInfo.parameters?.length}
								<div class="mt-2 border-t border-cs-border pt-2">
									<div class="mb-1 text-[10px] text-cs-text-muted">Declared parameters:</div>
									{#each panelScriptInfo.parameters as param}
										<div class="font-mono text-[10px] text-cs-text-muted">
											{param.key}{param.is_secret ? ' 🔒' : ''}
										</div>
									{/each}
								</div>
							{/if}
						</div>
					{/if}
				</div>

				<div class="flex gap-2 border-t border-cs-border px-4 py-3">
					<button class="btn-primary flex-1 text-xs" onclick={savePanel} disabled={panelSaving}>
						{panelSaving ? 'Saving…' : 'Save Config'}
					</button>
					<button
						class="ghost-btn text-xs text-cs-error"
						onclick={() => panelNode && deleteNode(panelNode.backendId)}
					>
						<Trash2 size={12} />
					</button>
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	:global(.svelte-flow__node-scriptNode) {
		border-radius: 0.5rem;
	}
	:global(.svelte-flow__edge:hover .svelte-flow__edge-path) {
		stroke: #f9e2af !important;
		stroke-width: 3px !important;
		cursor: pointer;
	}
	:global(.svelte-flow__controls) {
		background: var(--color-cs-surface) !important;
		border: 1px solid var(--color-cs-border) !important;
		border-radius: 0.5rem !important;
		overflow: hidden;
	}
	:global(.svelte-flow__controls-button) {
		background: var(--color-cs-surface) !important;
		border-color: var(--color-cs-border) !important;
		color: var(--color-cs-text-muted) !important;
		fill: var(--color-cs-text-muted) !important;
	}
	:global(.svelte-flow__controls-button:hover) {
		background: var(--color-cs-surface-2) !important;
	}
</style>
