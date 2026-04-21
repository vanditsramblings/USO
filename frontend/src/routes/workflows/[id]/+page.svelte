<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onMount, onDestroy } from 'svelte';
	import * as api from '$lib/api/client';
	import { scripts as scriptStore } from '$lib/stores';
	import type { Workflow, WorkflowNodeRun } from '$lib/types';
	import { Splitpanes, Pane } from 'svelte-splitpanes';
	import { ArrowLeft, Play, Square } from 'lucide-svelte';

	const id = $derived(page.params.id);

	let workflow = $state<Workflow | null>(null);
	let executing = $state(false);
	let nodeStatuses = $state<Record<string, string>>({});
	let nodeLogs = $state<Record<string, string>>({});
	let nodeConfigs = $state<Record<string, { expanded: boolean }>>({});
	let progress = $state({ completed: 0, total: 0 });
	let ws: WebSocket | null = null;

	onMount(async () => {
		workflow = await api.workflows.get(id!);
	});

	onDestroy(() => { ws?.close(); });

	function executeChain() {
		if (!workflow || executing) return;
		executing = true;
		nodeStatuses = {};
		nodeLogs = {};
		progress = { completed: 0, total: workflow.nodes.length };

		const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
		ws = new WebSocket(`${proto}//${location.host}/api/workflows/${workflow.id}/ws`);

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
				progress.completed += 1;
				progress = { ...progress };
				// Fetch run logs if available
				if (data.run_id) {
					api.runs.get(data.run_id).then((run) => {
						nodeLogs[data.node_id] = run.logs ?? '';
						nodeLogs = { ...nodeLogs };
					});
				}
			} else if (data.type === 'workflow_complete') {
				executing = false;
				ws?.close();
			}
		};
		ws.onerror = () => { executing = false; };
		ws.onclose = () => { executing = false; };
	}

	function stop() {
		ws?.close();
		executing = false;
	}

	function statusBorder(nodeId: string): string {
		const s = nodeStatuses[nodeId];
		const map: Record<string, string> = {
			pending: 'border-border',
			running: 'border-warning',
			success: 'border-success',
			failure: 'border-danger',
			skipped: 'border-border opacity-40',
		};
		return map[s] ?? 'border-border';
	}

	function statusLabel(nodeId: string): string {
		return nodeStatuses[nodeId] ?? 'idle';
	}
</script>

{#if workflow}
	<div class="flex h-full flex-col">
		<!-- Header -->
		<div class="flex items-center gap-3 border-b border-border px-4 py-2">
			<button class="ghost-btn p-1" onclick={() => goto('/workflows')}>
				<ArrowLeft size={14} />
			</button>
			<h2 class="text-sm font-medium">{workflow.name}</h2>
			{#if workflow.description}
				<span class="text-xs text-text-dim">— {workflow.description}</span>
			{/if}
			<div class="flex-1"></div>
			{#if executing}
				<div class="flex items-center gap-2 text-xs text-text-muted">
					<div class="h-1.5 w-24 overflow-hidden rounded-full bg-bg-surface">
						<div
							class="h-full rounded-full bg-accent transition-all"
							style="width:{progress.total ? (progress.completed / progress.total) * 100 : 0}%"
						></div>
					</div>
					{progress.completed}/{progress.total}
				</div>
				<button class="ghost-btn flex items-center gap-1.5 text-danger text-xs" onclick={stop}>
					<Square size={13} /> Stop
				</button>
			{:else}
				<button
					class="btn-primary flex items-center gap-1.5 text-xs"
					onclick={executeChain}
					disabled={workflow.nodes.length === 0}
				>
					<Play size={13} /> Execute Chain
				</button>
			{/if}
		</div>

		<!-- Pipeline: horizontal panes for each node -->
		{#if workflow.nodes.length === 0}
			<div class="flex flex-1 items-center justify-center text-xs text-text-dim">
				No nodes in this workflow
			</div>
		{:else}
			<Splitpanes class="flex-1">
				{#each workflow.nodes as node, i}
					{@const script = $scriptStore.find((s) => s.id === node.script_id)}
					<Pane minSize={10}>
						<div class="flex h-full flex-col border-l-2 transition-colors {statusBorder(node.id)}">
							<!-- Node header -->
							<div class="flex items-center gap-2 border-b border-border-subtle px-3 py-2">
								<span class="rounded bg-bg-surface px-1.5 py-0.5 font-mono text-xs">{i + 1}</span>
								<span class="text-xs font-medium">{script?.name ?? '?'}</span>
								<span class="rounded bg-bg-surface px-1 py-0.5 text-xs text-text-dim">{script?.runtime}</span>
								<div class="flex-1"></div>
								<button
									class="text-xs text-text-dim hover:text-text"
									onclick={() => {
										nodeConfigs[node.id] = { expanded: !nodeConfigs[node.id]?.expanded };
										nodeConfigs = { ...nodeConfigs };
									}}
								>
									{nodeConfigs[node.id]?.expanded ? '▾ Config' : '▸ Config'}
								</button>
								<span class="text-xs text-text-dim">{statusLabel(node.id)}</span>
							</div>
							<!-- Node config (collapsible) -->
							{#if nodeConfigs[node.id]?.expanded}
								{@const inEdges = workflow.edges.filter((e) => e.target_node_id === node.id)}
								<div class="border-b border-border-subtle bg-bg-surface px-3 py-2 text-xs">
									{#if inEdges.length > 0}
										<div class="mb-2">
											<span class="text-text-dim">Runs after:</span>
											{#each inEdges as ie}
												{@const srcNode = workflow.nodes.find((n) => n.id === ie.source_node_id)}
												{@const srcScript = $scriptStore.find((s) => s.id === srcNode?.script_id)}
												<span class="ml-1 rounded bg-bg px-1.5 py-0.5 text-text-muted">
													{srcScript?.name ?? '?'}
													{#if ie.condition}
														<span class="text-text-dim">({ie.condition.type}: {ie.condition.value})</span>
													{/if}
												</span>
											{/each}
										</div>
									{/if}
									{#if node.config}
										<div class="text-text-dim">
											Config: <code class="text-text-muted">{JSON.stringify(node.config)}</code>
										</div>
									{:else}
										<span class="text-text-dim">No custom config</span>
									{/if}
								</div>
							{/if}
							<!-- Mini code preview -->
							<div class="border-b border-border-subtle bg-bg px-3 py-2 overflow-hidden" style="max-height:120px">
								<pre class="overflow-hidden text-ellipsis whitespace-pre font-mono text-xs leading-relaxed text-text-muted">{script?.content.slice(0, 500) ?? ''}</pre>
							</div>
							<!-- Log output -->
							<div class="flex-1 overflow-auto bg-bg p-3">
								{#if nodeLogs[node.id]}
									<pre class="whitespace-pre-wrap font-mono text-xs leading-relaxed text-text-muted">{nodeLogs[node.id]}</pre>
								{:else if nodeStatuses[node.id] === 'running'}
									<div class="flex items-center gap-2 text-xs text-warning">
										<span class="animate-pulse">●</span> Running…
									</div>
								{:else if nodeStatuses[node.id] === 'skipped'}
									<p class="text-xs text-text-dim">Skipped</p>
								{:else}
									<p class="text-xs text-text-dim">No output</p>
								{/if}
							</div>
						</div>
					</Pane>
				{/each}
			</Splitpanes>
		{/if}
	</div>
{:else}
	<div class="flex h-full items-center justify-center text-text-dim">Loading…</div>
{/if}
