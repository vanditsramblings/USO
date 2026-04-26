<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { onDestroy } from 'svelte';
	import * as api from '$lib/api/client';
	import { scripts as scriptStore } from '$lib/stores';
	import type { Workflow, WorkflowRun, WorkflowNodeRun, WorkflowMetrics } from '$lib/types';
	import { Splitpanes, Pane } from 'svelte-splitpanes';
	import { ArrowLeft, Play, Square } from 'lucide-svelte';

	type Tab = 'overview' | 'pipeline' | 'history' | 'metrics';

	const id = $derived(page.params.id);
	const activeTab = $derived<Tab>((page.url.searchParams.get('tab') as Tab) || 'overview');

	let workflow = $state<Workflow | null>(null);
	let executing = $state(false);
	let nodeStatuses = $state<Record<string, string>>({});
	let nodeLogs = $state<Record<string, string>>({});
	let nodeConfigs = $state<Record<string, { expanded: boolean }>>({});
	let progress = $state({ completed: 0, total: 0 });
	let ws: WebSocket | null = null;

	let runHistory = $state<WorkflowRun[]>([]);
	let historyLoading = $state(false);
	let wfMetrics = $state<WorkflowMetrics | null>(null);
	let metricsLoading = $state(false);

	// Collapsible history state
	let expandedRunId = $state<string | null>(null);
	let expandedNodeRunIds = $state<Set<string>>(new Set());
	let nodeLogsCache = $state<Record<string, string | null>>({});

	$effect(() => { if (id) api.workflows.get(id!).then((wf) => { workflow = wf; }); });
	onDestroy(() => { ws?.close(); });

	function setTab(t: Tab) {
		const url = new URL(window.location.href);
		url.searchParams.set('tab', t);
		goto(url.toString(), { replaceState: true, keepFocus: true });
	}

	// Always reload on tab switch — no "only if empty" guard
	$effect(() => {
		if (activeTab === 'history' && workflow) loadHistory();
		if (activeTab === 'metrics' && workflow) loadMetrics();
	});

	async function loadHistory() {
		if (!workflow) return;
		historyLoading = true;
		expandedRunId = null;
		expandedNodeRunIds = new Set();
		nodeLogsCache = {};
		runHistory = await api.workflows.runs(workflow.id);
		historyLoading = false;
	}

	async function loadMetrics() {
		if (!workflow) return;
		metricsLoading = true;
		wfMetrics = await api.workflows.getMetrics(workflow.id);
		metricsLoading = false;
	}

	function toggleRun(runId: string) {
		expandedRunId = expandedRunId === runId ? null : runId;
	}

	async function toggleNodeLog(nr: WorkflowNodeRun) {
		const next = new Set(expandedNodeRunIds);
		if (next.has(nr.id)) {
			next.delete(nr.id);
		} else {
			next.add(nr.id);
			if (nr.run_id && !(nr.id in nodeLogsCache)) {
				const run = await api.runs.get(nr.run_id);
				nodeLogsCache = { ...nodeLogsCache, [nr.id]: run.logs ?? '' };
			} else if (!nr.run_id) {
				nodeLogsCache = { ...nodeLogsCache, [nr.id]: null };
			}
		}
		expandedNodeRunIds = next;
	}

	function nodeLabel(nodeId: string): string {
		const node = workflow?.nodes.find((n) => n.id === nodeId);
		if (!node) return nodeId.slice(0, 8);
		const script = $scriptStore.find((s) => s.id === node.script_id);
		return script?.name ?? node.script_id.slice(0, 8);
	}

	function executeChain() {
		if (!workflow || executing) return;
		executing = true; nodeStatuses = {}; nodeLogs = {};
		progress = { completed: 0, total: workflow.nodes.length };
		const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
		ws = new WebSocket(`${proto}//${location.host}/api/workflows/${workflow.id}/ws`);
		ws.onmessage = (event) => {
			const data = JSON.parse(event.data);
			if (data.type === 'workflow_start') {
				for (const nodeId of data.order) nodeStatuses[nodeId] = 'pending';
				nodeStatuses = { ...nodeStatuses };
			} else if (data.type === 'node_start') {
				nodeStatuses[data.node_id] = 'running'; nodeStatuses = { ...nodeStatuses };
			} else if (data.type === 'node_complete') {
				nodeStatuses[data.node_id] = data.status; nodeStatuses = { ...nodeStatuses };
				progress.completed += 1; progress = { ...progress };
				if (data.run_id) api.runs.get(data.run_id).then((run) => { nodeLogs[data.node_id] = run.logs ?? ''; nodeLogs = { ...nodeLogs }; });
			} else if (data.type === 'workflow_complete') {
				executing = false; ws?.close();
			}
		};
		ws.onerror = () => { executing = false; };
		ws.onclose = () => { executing = false; };
	}

	function stop() { ws?.close(); executing = false; }

	function statusBorder(nodeId: string): string {
		const map: Record<string, string> = { pending: 'border-cs-border', running: 'border-warning', success: 'border-success', failure: 'border-danger', skipped: 'border-cs-border opacity-40' };
		return map[nodeStatuses[nodeId]] ?? 'border-cs-border';
	}

	const statusColors: Record<string, string> = { success: 'text-success', failure: 'text-cs-error', running: 'text-accent', pending: 'text-cs-text-muted', skipped: 'text-cs-text-muted' };

	function fmtDate(d: string | null) {
		if (!d) return '—';
		return new Date(d.includes('T') ? d : d + 'Z').toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
	}

	function fmtDur(start: string | null, end: string | null) {
		if (!start || !end) return '—';
		const s = (new Date(end + 'Z').getTime() - new Date(start + 'Z').getTime()) / 1000;
		return s < 60 ? `${s.toFixed(1)}s` : `${Math.floor(s / 60)}m ${(s % 60).toFixed(0)}s`;
	}

	const TABS: { key: Tab; label: string }[] = [
		{ key: 'overview', label: 'Overview' },
		{ key: 'pipeline', label: 'Pipeline' },
		{ key: 'history', label: 'Run History' },
		{ key: 'metrics', label: 'Metrics' },
	];
</script>

{#if workflow}
<div class="flex h-full flex-col">
	<!-- Header — breadcrumb only, no action buttons (moved to Pipeline tab) -->
	<div class="flex items-center gap-3 border-b border-cs-border px-4 py-2">
		<button class="ghost-btn p-1" onclick={() => goto('/workflows')}><ArrowLeft size={14}/></button>
		<h2 class="text-sm font-medium">{workflow.name}</h2>
		{#if workflow.description}<span class="text-xs text-cs-text-muted">— {workflow.description}</span>{/if}
		<div class="flex-1"></div>
		<span class="text-xs text-cs-text-muted">{workflow.nodes.length} nodes · {workflow.edges.length} edges</span>
	</div>

	<!-- Top-level Tab bar -->
	<div class="flex items-center border-b border-cs-border px-4">
		{#each TABS as t}
			<button
				class="border-b-2 px-4 py-2 text-xs font-medium transition-colors {activeTab === t.key ? 'border-accent text-accent' : 'border-transparent text-cs-text-muted hover:text-cs-text'}"
				onclick={() => setTab(t.key)}
			>{t.label}</button>
		{/each}
	</div>

	<!-- Tab content -->
	<div class="flex-1 overflow-hidden">
		{#if activeTab === 'overview'}
			<div class="overflow-auto p-6">
				<div class="grid max-w-xl grid-cols-2 gap-4">
					<div class="flex flex-col gap-1 rounded border border-cs-border bg-cs-surface-2 p-4">
						<span class="text-[11px] font-semibold uppercase tracking-wider text-cs-text-muted">Name</span>
						<span class="text-sm font-medium">{workflow.name}</span>
					</div>
					<div class="flex flex-col gap-1 rounded border border-cs-border bg-cs-surface-2 p-4">
						<span class="text-[11px] font-semibold uppercase tracking-wider text-cs-text-muted">Description</span>
						<span class="text-xs text-cs-text">{workflow.description ?? '—'}</span>
					</div>
					<div class="flex flex-col gap-1 rounded border border-cs-border bg-cs-surface-2 p-4">
						<span class="text-[11px] font-semibold uppercase tracking-wider text-cs-text-muted">Created</span>
						<span class="text-xs">{fmtDate(workflow.created_at)}</span>
					</div>
					<div class="flex flex-col gap-1 rounded border border-cs-border bg-cs-surface-2 p-4">
						<span class="text-[11px] font-semibold uppercase tracking-wider text-cs-text-muted">Updated</span>
						<span class="text-xs">{fmtDate(workflow.updated_at)}</span>
					</div>
					<div class="flex flex-col gap-1 rounded border border-cs-border bg-cs-surface-2 p-4">
						<span class="text-[11px] font-semibold uppercase tracking-wider text-cs-text-muted">Nodes</span>
						<span class="text-2xl font-mono font-semibold">{workflow.nodes.length}</span>
					</div>
					<div class="flex flex-col gap-1 rounded border border-cs-border bg-cs-surface-2 p-4">
						<span class="text-[11px] font-semibold uppercase tracking-wider text-cs-text-muted">Edges</span>
						<span class="text-2xl font-mono font-semibold">{workflow.edges.length}</span>
					</div>
				</div>
				<div class="mt-4">
					<button class="ghost-btn text-xs" onclick={() => setTab('pipeline')}>→ Go to Pipeline</button>
				</div>
			</div>

		{:else if activeTab === 'pipeline'}
			<!-- Pipeline actions bar -->
			<div class="flex items-center gap-3 border-b border-cs-border px-3 py-1.5">
				{#if executing}
					<div class="flex items-center gap-2 text-xs text-cs-text-muted">
						<div class="h-1.5 w-24 overflow-hidden rounded-full bg-cs-surface-2">
							<div class="h-full rounded-full bg-accent transition-all" style="width:{progress.total ? (progress.completed / progress.total) * 100 : 0}%"></div>
						</div>
						{progress.completed}/{progress.total} steps
					</div>
					<button class="ghost-btn flex items-center gap-1.5 text-xs text-cs-error" onclick={stop}><Square size={13}/> Stop</button>
				{:else}
					<button class="btn-primary flex items-center gap-1.5 text-xs" onclick={executeChain} disabled={workflow.nodes.length === 0}><Play size={13}/> Execute Chain</button>
				{/if}
			</div>

			{#if workflow.nodes.length === 0}
				<div class="flex h-full items-center justify-center text-xs text-cs-text-muted">No nodes in this workflow</div>
			{:else}
				<Splitpanes class="h-[calc(100%-37px)]">
					{#each workflow.nodes as node, i}
						{@const script = $scriptStore.find((s) => s.id === node.script_id)}
						<Pane minSize={10}>
							<div class="flex h-full flex-col border-l-2 transition-colors {statusBorder(node.id)}">
								<div class="flex items-center gap-2 border-b border-cs-border px-3 py-2">
									<span class="rounded bg-cs-surface-2 px-1.5 py-0.5 font-mono text-xs">{i + 1}</span>
									<span class="text-xs font-medium">{script?.name ?? '?'}</span>
									<span class="rounded bg-cs-surface-2 px-1 py-0.5 text-xs text-cs-text-muted">{script?.runtime}</span>
									<div class="flex-1"></div>
									<button class="text-xs text-cs-text-muted hover:text-cs-text"
										onclick={() => { nodeConfigs[node.id] = { expanded: !nodeConfigs[node.id]?.expanded }; nodeConfigs = { ...nodeConfigs }; }}>
										{nodeConfigs[node.id]?.expanded ? '▾ Config' : '▸ Config'}
									</button>
									<span class="text-xs {statusColors[nodeStatuses[node.id]] ?? 'text-cs-text-muted'}">● {nodeStatuses[node.id] ?? 'idle'}</span>
								</div>
								{#if nodeConfigs[node.id]?.expanded}
									{@const inEdges = workflow.edges.filter((e) => e.target_node_id === node.id)}
									<div class="border-b border-cs-border bg-cs-surface-2 px-3 py-2 text-xs">
										{#if inEdges.length > 0}
											<div class="mb-1"><span class="text-cs-text-muted">Runs after:</span>
												{#each inEdges as ie}
													{@const srcNode = workflow.nodes.find((n) => n.id === ie.source_node_id)}
													{@const srcScript = $scriptStore.find((s) => s.id === srcNode?.script_id)}
													<span class="ml-1 rounded bg-bg px-1.5 py-0.5 text-cs-text-muted">{srcScript?.name ?? '?'}{#if ie.condition} ({ie.condition.type}: {ie.condition.value}){/if}</span>
												{/each}
											</div>
										{/if}
										{#if node.config}<div class="text-cs-text-muted">Config: <code>{JSON.stringify(node.config)}</code></div>{:else}<span class="text-cs-text-muted">No custom config</span>{/if}
									</div>
								{/if}
								<div class="border-b border-cs-border bg-bg px-3 py-2 overflow-hidden" style="max-height:120px">
									<pre class="overflow-hidden text-ellipsis whitespace-pre font-mono text-xs leading-relaxed text-cs-text-muted">{script?.content.slice(0, 500) ?? ''}</pre>
								</div>
								<div class="flex-1 overflow-auto bg-bg p-3">
									{#if nodeLogs[node.id]}
										<pre class="whitespace-pre-wrap font-mono text-xs leading-relaxed text-cs-text-muted">{nodeLogs[node.id]}</pre>
									{:else if nodeStatuses[node.id] === 'running'}
										<div class="flex items-center gap-2 text-xs text-cs-warning"><span class="animate-pulse">●</span> Running…</div>
									{:else if nodeStatuses[node.id] === 'skipped'}
										<p class="text-xs text-cs-text-muted">Skipped</p>
									{:else}
										<p class="text-xs text-cs-text-muted">No output</p>
									{/if}
								</div>
							</div>
						</Pane>
					{/each}
				</Splitpanes>
			{/if}

		{:else if activeTab === 'history'}
			{#if historyLoading}
				<div class="flex h-full items-center justify-center text-xs text-cs-text-muted">Loading…</div>
			{:else}
				<div class="flex h-full flex-col overflow-hidden">
					<div class="shrink-0 border-b border-cs-border px-3 py-1.5 text-xs text-cs-text-muted">
						{runHistory.length} workflow runs — click a row to expand node details
					</div>
					<div class="flex-1 overflow-auto">
						{#each runHistory as run (run.id)}
							<!-- Workflow run row -->
							<div class="border-b border-cs-border">
								<button
									class="flex w-full items-center gap-3 px-3 py-2 text-xs transition-colors hover:bg-cs-surface-2"
									onclick={() => toggleRun(run.id)}
								>
									<span class="text-cs-text-muted">{expandedRunId === run.id ? '▾' : '▸'}</span>
									<span class="font-mono text-cs-text-muted">{run.id.slice(0, 8)}…</span>
									<span class="font-medium {statusColors[run.status] ?? 'text-cs-text-muted'}">● {run.status}</span>
									<span class="text-cs-text-muted">{fmtDate(run.started_at)}</span>
									<span class="font-mono">{fmtDur(run.started_at, run.finished_at)}</span>
									<span class="ml-auto text-cs-text-muted">{run.node_runs.length} steps</span>
								</button>

								{#if expandedRunId === run.id}
									<div class="border-t border-cs-border/50 bg-cs-surface-2">
										{#each run.node_runs as nr (nr.id)}
											<div class="border-b border-cs-border/30">
												<!-- Node run row -->
												<button
													class="flex w-full items-center gap-3 py-1.5 pl-8 pr-3 text-xs transition-colors hover:bg-cs-surface {nr.run_id ? 'cursor-pointer' : 'cursor-default opacity-60'}"
													onclick={() => toggleNodeLog(nr)}
													disabled={!nr.run_id}
												>
													{#if nr.run_id}
														<span class="text-cs-text-muted">{expandedNodeRunIds.has(nr.id) ? '▾' : '▸'}</span>
													{:else}
														<span class="w-3"></span>
													{/if}
													<span class="w-5 text-center font-mono text-cs-text-muted">{nr.execution_order + 1}</span>
													<span class="font-medium">{nodeLabel(nr.node_id)}</span>
													<span class="{statusColors[nr.status] ?? 'text-cs-text-muted'}">● {nr.status}</span>
													{#if !nr.run_id}<span class="text-[10px] text-cs-text-muted italic">no script run</span>{/if}
												</button>

												<!-- Inline log panel for this node -->
												{#if expandedNodeRunIds.has(nr.id)}
													<div class="max-h-64 overflow-auto border-t border-cs-border/30 bg-bg px-4 py-2 pl-16 font-mono text-xs leading-relaxed">
														{#if nr.id in nodeLogsCache}
															{#if nodeLogsCache[nr.id]}
																<pre class="whitespace-pre-wrap text-cs-text-muted">{nodeLogsCache[nr.id]}</pre>
															{:else}
																<p class="italic text-cs-text-muted">No logs captured for this run.</p>
															{/if}
														{:else}
															<p class="animate-pulse text-cs-text-muted">Loading logs…</p>
														{/if}
													</div>
												{/if}
											</div>
										{:else}
											<p class="py-4 pl-8 text-xs italic text-cs-text-muted">No node runs recorded.</p>
										{/each}
									</div>
								{/if}
							</div>
						{:else}
							<div class="flex items-center justify-center py-12 text-xs text-cs-text-muted">
								No runs yet — execute the workflow from the Pipeline tab first.
							</div>
						{/each}
					</div>
				</div>
			{/if}

		{:else if activeTab === 'metrics'}
			<div class="flex h-full flex-col">
				{#if metricsLoading}
					<div class="flex h-full items-center justify-center text-xs text-cs-text-muted">Loading…</div>
				{:else if wfMetrics}
					<div class="grid grid-cols-2 gap-4 overflow-auto p-4">
						<div class="flex flex-col items-center gap-2 rounded border border-cs-border bg-cs-surface-2 p-4">
							<span class="text-xs font-medium uppercase tracking-wider text-cs-text-muted">Success Rate</span>
							<span class="text-4xl font-mono font-semibold {wfMetrics.success_rate >= 0.8 ? 'text-success' : wfMetrics.success_rate >= 0.5 ? 'text-cs-warning' : 'text-cs-error'}">{(wfMetrics.success_rate * 100).toFixed(0)}%</span>
							<span class="text-xs text-cs-text-muted">{wfMetrics.total_runs} total runs</span>
						</div>
						<div class="flex flex-col items-center justify-center gap-1 rounded border border-cs-border bg-cs-surface-2 p-4">
							<span class="text-xs font-medium uppercase tracking-wider text-cs-text-muted">Avg Duration</span>
							<span class="text-3xl font-mono font-semibold">{wfMetrics.avg_duration_s !== null ? (wfMetrics.avg_duration_s < 60 ? `${wfMetrics.avg_duration_s.toFixed(1)}s` : `${Math.floor(wfMetrics.avg_duration_s/60)}m`) : '—'}</span>
						</div>
						<div class="col-span-2 flex flex-col gap-2 rounded border border-cs-border bg-cs-surface-2 p-4">
							<span class="text-xs font-medium uppercase tracking-wider text-cs-text-muted">Runs by Status</span>
							<div class="flex flex-wrap gap-4">
								{#each Object.entries(wfMetrics.runs_by_status) as [status, count]}
									<div class="flex items-center gap-1.5">
										<span class="h-2.5 w-2.5 rounded-full {status === 'success' ? 'bg-success' : status === 'failure' ? 'bg-cs-error' : 'bg-cs-text-muted'}"></span>
										<span class="text-xs capitalize">{status}</span>
										<span class="text-xs font-mono font-medium">{count}</span>
									</div>
								{/each}
							</div>
							{#if wfMetrics.total_runs > 0}
								<div class="flex h-3 w-full overflow-hidden rounded-full">
									{#each Object.entries(wfMetrics.runs_by_status) as [status, count]}
										<div style="width:{(count / wfMetrics.total_runs * 100).toFixed(1)}%;background:{status === 'success' ? '#22c55e' : status === 'failure' ? '#ef4444' : '#6b7280'}" title="{status}: {count}"></div>
									{/each}
								</div>
							{/if}
						</div>
					</div>
				{:else}
					<p class="p-4 text-xs italic text-cs-text-muted">No metrics yet — execute the workflow first.</p>
				{/if}
			</div>
		{/if}
	</div>
</div>
{:else}
<div class="flex h-full items-center justify-center text-cs-text-muted">Loading…</div>
{/if}
