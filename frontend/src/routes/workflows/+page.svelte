<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import * as api from '$lib/api/client';
	import { scripts, loadWorkflows, workflows } from '$lib/stores';
	import type { Workflow, WorkflowNode, WorkflowNodeRun } from '$lib/types';
	import { Plus, Trash2, Zap, Play, Square } from 'lucide-svelte';

	let loading = $state(true);
	let showCreate = $state(false);
	let newName = $state('');
	let newDesc = $state('');
	let creating = $state(false);

	// Selected workflow detail
	let selectedWf = $state<Workflow | null>(null);

	// Add node
	let addNodeScriptId = $state('');

	// Execution state
	let executing = $state(false);
	let nodeStatuses = $state<Record<string, string>>({});
	let executionProgress = $state({ completed: 0, total: 0 });
	let ws: WebSocket | null = null;

	onMount(async () => {
		await loadWorkflows();
		loading = false;
	});

	onDestroy(() => { ws?.close(); });

	async function createWorkflow() {
		if (!newName) return;
		creating = true;
		try {
			const wf = await api.workflows.create({ name: newName, description: newDesc });
			await loadWorkflows();
			selectedWf = wf;
			showCreate = false;
			newName = '';
			newDesc = '';
		} finally {
			creating = false;
		}
	}

	async function deleteWorkflow(id: string) {
		if (!confirm('Delete this workflow?')) return;
		await api.workflows.delete(id);
		if (selectedWf?.id === id) selectedWf = null;
		await loadWorkflows();
	}

	async function selectWorkflow(wf: Workflow) {
		selectedWf = await api.workflows.get(wf.id);
		nodeStatuses = {};
		executionProgress = { completed: 0, total: 0 };
	}

	async function addNode() {
		if (!selectedWf || !addNodeScriptId) return;
		const nodeCount = selectedWf.nodes.length;
		await api.workflows.addNode(selectedWf.id, {
			script_id: addNodeScriptId,
			position_x: 100 + nodeCount * 200,
			position_y: 150
		});
		selectedWf = await api.workflows.get(selectedWf.id);
		addNodeScriptId = '';
	}

	async function addEdge(srcNodeId: string, tgtNodeId: string) {
		if (!selectedWf) return;
		await api.workflows.addEdge(selectedWf.id, {
			source_node_id: srcNodeId,
			target_node_id: tgtNodeId,
			condition: { type: 'status', value: 'success' }
		});
		selectedWf = await api.workflows.get(selectedWf.id);
	}

	function executeWorkflow() {
		if (!selectedWf || executing) return;
		executing = true;
		nodeStatuses = {};
		executionProgress = { completed: 0, total: selectedWf.nodes.length };

		const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
		ws = new WebSocket(`${proto}//${location.host}/api/workflows/${selectedWf.id}/ws`);

		ws.onmessage = (event) => {
			const data = JSON.parse(event.data);
			if (data.type === 'workflow_start') {
				for (const nodeId of data.order) {
					nodeStatuses[nodeId] = 'pending';
				}
				nodeStatuses = { ...nodeStatuses };
			} else if (data.type === 'node_start') {
				nodeStatuses[data.node_id] = 'running';
				nodeStatuses = { ...nodeStatuses };
			} else if (data.type === 'node_complete') {
				nodeStatuses[data.node_id] = data.status;
				nodeStatuses = { ...nodeStatuses };
				executionProgress.completed += 1;
				executionProgress = { ...executionProgress };
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

	const runtimeColor: Record<string, string> = { py: 'border-indigo', sh: 'border-accent', js: 'border-warning' };

	function nodeStatusClass(nodeId: string): string {
		const s = nodeStatuses[nodeId];
		if (!s) return '';
		const map: Record<string, string> = {
			pending: 'opacity-50',
			running: 'ring-2 ring-warning animate-pulse',
			success: 'ring-2 ring-success',
			failure: 'ring-2 ring-danger',
			skipped: 'opacity-30',
		};
		return map[s] ?? '';
	}

	function nodeStatusDot(nodeId: string): string {
		const s = nodeStatuses[nodeId];
		if (!s) return '';
		const map: Record<string, string> = {
			pending: 'text-text-dim',
			running: 'text-warning',
			success: 'text-success',
			failure: 'text-danger',
			skipped: 'text-text-dim',
		};
		return map[s] ?? '';
	}
</script>

<div class="flex h-full flex-col">
	<div class="flex items-center gap-2 border-b border-border px-4 py-2">
		<Zap size={14} strokeWidth={2} class="text-text-dim" />
		<h2 class="text-sm font-medium">Workflow DAGs</h2>
		<div class="flex-1"></div>
		{#if selectedWf && selectedWf.nodes.length > 0}
			{#if executing}
				<div class="flex items-center gap-2 text-xs text-text-muted">
					<div class="h-1.5 w-24 rounded-full bg-bg-surface overflow-hidden">
						<div
							class="h-full rounded-full bg-accent transition-all"
							style="width:{executionProgress.total ? (executionProgress.completed / executionProgress.total) * 100 : 0}%"
						></div>
					</div>
					{executionProgress.completed}/{executionProgress.total}
				</div>
				<button class="ghost-btn flex items-center gap-1.5 text-danger" onclick={stopExecution}>
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

	{#if showCreate}
		<div class="flex items-end gap-2 border-b border-border-subtle bg-bg-surface px-4 py-3">
			<div>
				<label class="mb-0.5 block text-xs text-text-dim">Name</label>
				<input class="input text-xs" bind:value={newName} placeholder="pipeline-name" />
			</div>
			<div class="flex-1">
				<label class="mb-0.5 block text-xs text-text-dim">Description</label>
				<input class="input text-xs" bind:value={newDesc} placeholder="Optional description" />
			</div>
			<button class="btn-primary text-xs" onclick={createWorkflow} disabled={creating}>Create</button>
		</div>
	{/if}

	<div class="flex flex-1 overflow-hidden">
		<!-- Workflow list -->
		<div class="w-56 shrink-0 overflow-y-auto border-r border-border bg-bg-elevated">
			{#if loading}
				{#each Array(3) as _}
					<div class="animate-pulse border-b border-border-subtle px-3 py-3">
						<div class="h-3 w-3/4 rounded bg-bg-surface"></div>
					</div>
				{/each}
			{:else if $workflows.length === 0}
				<div class="p-4 text-center text-xs text-text-dim">No workflows yet</div>
			{:else}
				{#each $workflows as wf}
					<div
						class="flex w-full items-center justify-between border-b border-border-subtle px-3 py-2.5 text-left transition-colors hover:bg-bg-hover {selectedWf?.id === wf.id ? 'bg-bg-surface' : ''}"
					>
						<button class="min-w-0 flex-1 text-left" onclick={() => selectWorkflow(wf)}>
							<div class="text-sm font-medium">{wf.name}</div>
							<div class="text-xs text-text-dim">{wf.nodes.length} nodes</div>
						</button>
						<button class="ghost-btn p-0.5 text-danger" onclick={() => deleteWorkflow(wf.id)}>
							<Trash2 size={11} />
						</button>
					</div>
				{/each}
			{/if}
		</div>

		<!-- DAG View -->
		<div class="flex-1 overflow-auto p-4">
			{#if selectedWf}
				<!-- Add node -->
				<div class="mb-4 flex items-end gap-2">
					<div>
						<label class="mb-0.5 block text-xs text-text-dim">Add Script Node</label>
						<select class="input text-xs" bind:value={addNodeScriptId}>
							<option value="">Select…</option>
							{#each $scripts as s}
								<option value={s.id}>{s.name}</option>
							{/each}
						</select>
					</div>
					<button class="btn-primary text-xs" onclick={addNode}>Add Node</button>
				</div>

				<!-- Visual DAG (simplified node view) -->
				{#if selectedWf.nodes.length === 0}
					<div class="flex h-48 items-center justify-center rounded-lg border border-dashed border-border text-xs text-text-dim">
						Add script nodes to build a workflow DAG
					</div>
				{:else}
					<div class="relative" style="min-height: 300px;">
						<!-- Edges as SVG lines -->
						<svg class="pointer-events-none absolute inset-0 h-full w-full">
							{#each selectedWf.edges as edge}
								{@const src = selectedWf.nodes.find((n) => n.id === edge.source_node_id)}
								{@const tgt = selectedWf.nodes.find((n) => n.id === edge.target_node_id)}
								{#if src && tgt}
									<line
										x1={src.position_x + 60}
										y1={src.position_y + 30}
										x2={tgt.position_x + 60}
										y2={tgt.position_y + 30}
										stroke="#34d399"
										stroke-width="2"
										marker-end="url(#arrow)"
									/>
								{/if}
							{/each}
							<defs>
								<marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto">
									<path d="M 0 0 L 10 5 L 0 10 z" fill="#34d399" />
								</marker>
							</defs>
						</svg>

						<!-- Nodes -->
						{#each selectedWf.nodes as node}
							{@const script = $scripts.find((s) => s.id === node.script_id)}
							<div
								class="absolute rounded-lg border-2 bg-bg-elevated p-3 shadow-lg transition-all {runtimeColor[script?.runtime ?? 'py']} {nodeStatusClass(node.id)}"
								style="left: {node.position_x}px; top: {node.position_y}px; width: 120px;"
							>
								<div class="flex items-center gap-1.5">
									{#if nodeStatuses[node.id]}
										<span class={nodeStatusDot(node.id)}>●</span>
									{/if}
									<span class="truncate font-mono text-xs font-medium">{script?.name ?? '?'}</span>
								</div>
								<div class="text-xs text-text-dim">{script?.runtime ?? '?'}</div>
								<!-- Connect button -->
								{#each selectedWf.nodes.filter((n) => n.id !== node.id) as other}
									{@const alreadyConnected = selectedWf.edges.some(
										(e) => e.source_node_id === node.id && e.target_node_id === other.id
									)}
									{#if !alreadyConnected}
										<button
											class="mt-1 block w-full truncate rounded bg-bg-surface px-1 py-0.5 text-left text-xs text-text-dim hover:text-accent"
											onclick={() => addEdge(node.id, other.id)}
										>
											→ {$scripts.find((s) => s.id === other.script_id)?.name ?? '?'}
										</button>
									{/if}
								{/each}
							</div>
						{/each}
					</div>
				{/if}
			{:else}
				<div class="flex h-full items-center justify-center text-xs text-text-dim">
					Select or create a workflow
				</div>
			{/if}
		</div>
	</div>
</div>
