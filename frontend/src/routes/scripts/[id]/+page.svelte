<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { tags as allTags, activeScriptId, drawerOpen } from '$lib/stores';
	import * as api from '$lib/api/client';
	import { loadScripts, loadTags } from '$lib/stores';
	import type { Script, Run, Tag, DetectionResult, ScriptMetrics } from '$lib/types';
	import { Play, Save, Scan, Trash2, Tag as TagIcon } from 'lucide-svelte';
	import CodeEditor from '$lib/components/CodeEditor.svelte';
	import RunHistoryTable from '$lib/components/RunHistoryTable.svelte';
	import MetricsPanel from '$lib/components/MetricsPanel.svelte';
	import LogPanel from '$lib/components/LogPanel.svelte';

	type Tab = 'overview' | 'execute' | 'detect' | 'history' | 'logs' | 'metrics';

	let script = $state<Script | null>(null);
	let editContent = $state('');
	let editDesc = $state('');
	let dirty = $state(false);
	let saving = $state(false);

	let envValues = $state<Record<string, string>>({});
	let timeout = $state(60);
	let running = $state(false);
	let streamLogs = $state('');
	let runResult = $state<Run | null>(null);

	let detection = $state<DetectionResult | null>(null);
	let detecting = $state(false);
	let scriptTags = $state<Tag[]>([]);
	let newTagInput = $state('');
	let showTags = $state(false);

	let runHistory = $state<Run[]>([]);
	let selectedRun = $state<Run | null>(null);
	let metrics = $state<ScriptMetrics | null>(null);
	let metricsRange = $state<'1d' | '7d' | '30d' | 'all'>('7d');
	let historyLoading = $state(false);
	let metricsLoading = $state(false);

	const id = $derived(page.params.id);
	const activeTab = $derived<Tab>((page.url.searchParams.get('tab') as Tab) || 'overview');

	function setTab(t: Tab) {
		const url = new URL(window.location.href);
		url.searchParams.set('tab', t);
		goto(url.toString(), { replaceState: true, keepFocus: true });
	}

	async function loadScript() {
		script = await api.scripts.get(id!);
		if (script) {
			editContent = script.content;
			editDesc = script.description ?? '';
			activeScriptId.set(script.id);
			drawerOpen.set(true);
			envValues = {};
			for (const p of script.parameters) envValues[p.key] = '';
			scriptTags = await api.tags.forScript(script.id);
		}
	}

	async function loadHistory() {
		if (!script) return;
		historyLoading = true;
		runHistory = await api.scripts.getRuns(script.id, { limit: 100 });
		historyLoading = false;
	}

	async function loadMetrics() {
		if (!script) return;
		metricsLoading = true;
		metrics = await api.scripts.getMetrics(script.id, metricsRange);
		metricsLoading = false;
	}

	$effect(() => { if (id) loadScript(); });
	$effect(() => { dirty = script ? editContent !== script.content || editDesc !== (script.description ?? '') : false; });
	// Always reload when switching to data tabs — removing the "only if empty" guard ensures fresh data on every tab click
	$effect(() => {
		if (activeTab === 'history' && script) loadHistory();
		if (activeTab === 'metrics' && script) loadMetrics();
	});

	async function save() {
		if (!script || !dirty) return;
		saving = true;
		try {
			await api.scripts.update(script.id, { content: editContent, description: editDesc });
			await loadScript(); await loadScripts(); dirty = false;
		} finally { saving = false; }
	}

	async function runScript() {
		if (!script) return;
		running = true; streamLogs = ''; runResult = null;
		try {
			const wsUrl = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/runs/${script.id}`;
			const ws = new WebSocket(wsUrl);
			ws.onopen = () => ws.send(JSON.stringify({ env: envValues, timeout }));
			ws.onmessage = (event) => {
				const msg = JSON.parse(event.data);
				if (msg.type === 'log') streamLogs += msg.data;
				else if (msg.type === 'complete') {
					runResult = { id: msg.run_id, script_id: script!.id, status: msg.status, exit_code: msg.exit_code, start_time: null, end_time: null, logs: streamLogs, trigger: 'manual' } as Run;
					running = false;
				} else if (msg.type === 'error') { streamLogs += `\nError: ${msg.detail}`; running = false; }
			};
			ws.onerror = async () => {
				ws.close();
				try { const r = await api.runs.create({ script_id: script!.id, env: envValues, timeout }); runResult = r; streamLogs = r.logs ?? ''; } finally { running = false; }
			};
			ws.onclose = () => { if (running) running = false; };
		} catch {
			try { const r = await api.runs.create({ script_id: script!.id, env: envValues, timeout }); runResult = r; streamLogs = r.logs ?? ''; } finally { running = false; }
		}
	}

	async function detectScript() {
		if (!script) return;
		detecting = true;
		detection = await api.detect(editContent, script.runtime);
		detecting = false;
	}

	async function addTag(name: string) {
		if (!script) return;
		const tag = await api.tags.create(name).catch(() => api.tags.list().then((all) => all.find((t) => t.name === name)!));
		if (tag && !scriptTags.some((t) => t.id === tag.id)) {
			await api.tags.tagScript(script.id, tag.id);
			scriptTags = await api.tags.forScript(script.id);
			await loadTags();
		}
	}

	async function removeTag(tagId: string) {
		if (!script) return;
		await api.tags.untagScript(script.id, tagId);
		scriptTags = await api.tags.forScript(script.id);
	}

	function handleNewTag() {
		const name = newTagInput.trim().replace(/\s+/g, '-');
		if (name) addTag(name);
		newTagInput = '';
	}

	async function deleteScript() {
		if (!script || !confirm(`Delete "${script.name}"?`)) return;
		await api.scripts.delete(script.id);
		await loadScripts();
		window.location.href = '/scripts';
	}

	function statusColor(s: string) {
		const m: Record<string, string> = { success: 'text-success', failure: 'text-cs-error', timeout: 'text-cs-warning' };
		return m[s] ?? 'text-cs-text-muted';
	}

	function fmtDate(d: string) {
		return new Date(d.includes('T') ? d : d + 'Z').toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
	}

	const runtimeBadge: Record<string, string> = {
		py: 'bg-blue-500/20 text-blue-400',
		sh: 'bg-yellow-500/20 text-yellow-400',
		js: 'bg-green-500/20 text-green-400',
	};

	function selectRun(run: Run) { selectedRun = run; setTab('logs'); }

	const streamLogLines = $derived(streamLogs ? streamLogs.split('\n') : []);
	const selectedRunLogLines = $derived(selectedRun?.logs ? selectedRun.logs.split('\n') : []);

	const TABS: { key: Tab; label: string }[] = [
		{ key: 'overview', label: 'Overview' },
		{ key: 'execute', label: 'Execute' },
		{ key: 'detect', label: 'Detect' },
		{ key: 'history', label: 'History' },
		{ key: 'logs', label: 'Logs' },
		{ key: 'metrics', label: 'Metrics' },
	];
</script>

{#if script}
<div class="flex h-full flex-col">
	<!-- Header -->
	<div class="flex items-center gap-2 border-b border-cs-border px-4 py-2">
		<nav class="flex items-center gap-1 text-xs text-cs-text-muted">
			<a href="/scripts" class="hover:text-cs-text">Scripts</a>
			<span>/</span>
			<span class="font-medium text-cs-text">{script.name}</span>
		</nav>
		<span class="rounded px-1.5 py-0.5 text-[11px] font-medium {runtimeBadge[script.runtime] ?? ''}">{script.runtime}</span>
		<span class="text-xs text-cs-text-muted">v{script.version}</span>
		<div class="flex-1"></div>
		<button class="ghost-btn flex items-center gap-1.5 text-xs" onclick={() => (showTags = !showTags)}>
			<TagIcon size={12}/> Tags
			{#if scriptTags.length > 0}<span class="rounded-full bg-accent/20 px-1.5 text-[10px] text-accent">{scriptTags.length}</span>{/if}
		</button>
		{#if dirty}<button class="btn-primary flex items-center gap-1.5 text-xs" onclick={save} disabled={saving}><Save size={12}/> {saving ? 'Saving…' : 'Save'}</button>{/if}
		<button class="ghost-btn text-cs-error" onclick={deleteScript} title="Delete"><Trash2 size={13}/></button>
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

	<!-- Tags dropdown panel -->
	{#if showTags}
		<div class="border-b border-cs-border bg-cs-surface-2 px-4 py-3">
			<div class="mb-2 flex items-start gap-3">
				<span class="mt-0.5 w-16 shrink-0 text-[11px] font-semibold uppercase tracking-wider text-cs-text-muted">Applied</span>
				<div class="flex min-h-[24px] flex-1 flex-wrap gap-1.5">
					{#each scriptTags as tag}<span class="tag-pill flex items-center gap-1">{tag.name}<button class="ml-0.5 hover:text-cs-error" onclick={() => removeTag(tag.id)}>×</button></span>
					{:else}<span class="text-xs italic text-cs-text-muted">None applied</span>{/each}
				</div>
			</div>
			{#if $allTags.filter((t) => !scriptTags.some((st) => st.id === t.id)).length > 0}
				<div class="mb-2 flex items-start gap-3">
					<span class="mt-0.5 w-16 shrink-0 text-[11px] font-semibold uppercase tracking-wider text-cs-text-muted">Add</span>
					<div class="flex flex-1 flex-wrap gap-1.5">
						{#each $allTags.filter((t) => !scriptTags.some((st) => st.id === t.id)) as av}
							<button class="inline-flex items-center rounded-full border border-cs-border px-2.5 py-1 text-xs text-cs-text-muted transition-colors hover:border-cs-accent hover:text-cs-accent" onclick={() => addTag(av.name)}>{av.name} +</button>
						{/each}
					</div>
				</div>
			{/if}
			<div class="flex items-center gap-2">
				<span class="w-16 shrink-0 text-[11px] font-semibold uppercase tracking-wider text-cs-text-muted">New</span>
				<input class="input w-32 text-xs" placeholder="tag-name…" bind:value={newTagInput} onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), handleNewTag())} />
				<button class="ghost-btn text-xs" onclick={handleNewTag}>Add</button>
			</div>
		</div>
	{/if}

	<!-- Tab content -->
	<div class="flex-1 overflow-hidden">
		{#if activeTab === 'overview'}
			<div class="flex items-center gap-4 border-b border-cs-border bg-cs-surface-2 px-4 py-1.5 text-xs text-cs-text-muted">
				<span>Created <strong class="text-cs-text">{fmtDate(script.created_at)}</strong></span>
				<span>Updated <strong class="text-cs-text">{fmtDate(script.updated_at)}</strong></span>
				{#if script.parameters.length > 0}<span>{script.parameters.length} param(s)</span>{/if}
			</div>
			<div class="flex h-[calc(100%-33px)] flex-col overflow-hidden">
				<div class="border-b border-cs-border px-4 py-2">
					<input class="input text-xs" placeholder="Description…" bind:value={editDesc} />
				</div>
				<div class="flex-1 overflow-hidden bg-bg">
					<CodeEditor content={editContent} language={script.runtime} onChange={(val) => { editContent = val; }} />
				</div>
			</div>

		{:else if activeTab === 'execute'}
			<div class="flex h-full overflow-hidden">
				<div class="flex w-60 shrink-0 flex-col overflow-y-auto border-r border-cs-border">
					<div class="border-b border-cs-border p-3">
						<h4 class="mb-2 text-xs font-semibold uppercase tracking-wider text-cs-text-muted">Environment</h4>
						{#if script.parameters.length === 0}
							<p class="text-xs text-cs-text-muted">No parameters defined</p>
						{:else}
							{#each script.parameters as param, i}
								<div class="mb-2">
									<label for="param-{i}" class="mb-0.5 flex items-center gap-1 text-xs text-cs-text-muted">
										{param.key}{#if param.is_secret}<span class="text-cs-warning">🔒</span>{/if}
									</label>
									<input id="param-{i}" class="input font-mono text-xs" type={param.is_secret ? 'password' : 'text'} bind:value={envValues[param.key]} />
								</div>
							{/each}
						{/if}
					</div>
					<div class="border-b border-cs-border p-3">
						<label for="exec-timeout" class="mb-0.5 block text-xs text-cs-text-muted">Timeout (s)</label>
						<input id="exec-timeout" class="input text-xs" type="number" min="5" max="300" bind:value={timeout} />
					</div>
					<div class="p-3">
						<button class="btn-primary flex w-full items-center justify-center gap-1.5 text-xs" onclick={runScript} disabled={running}>
							<Play size={13}/> {running ? 'Running…' : 'Execute'}
						</button>
					</div>
					{#if runResult}
						<div class="border-t border-cs-border p-3">
							<div class="flex items-center gap-2 text-xs">
								<span class={statusColor(runResult.status)}>● {runResult.status}</span>
								{#if runResult.exit_code !== null}<span class="text-cs-text-muted">exit {runResult.exit_code}</span>{/if}
							</div>
						</div>
					{/if}
				</div>
				<div class="flex flex-1 flex-col overflow-hidden">
					<LogPanel lines={streamLogLines} title="Output" subtitle={running ? '● Running…' : undefined} empty="Run the script to see output here." />
				</div>
			</div>

		{:else if activeTab === 'detect'}
			<div class="flex h-full flex-col">
				<div class="flex items-center gap-3 border-b border-cs-border px-3 py-2">
					<span class="text-xs font-medium text-cs-text">Auto-Detection</span>
					<button class="ghost-btn flex items-center gap-1.5 text-xs" onclick={detectScript} disabled={detecting}>
						<Scan size={12}/> {detecting ? 'Scanning…' : 'Scan Script'}
					</button>
				</div>
				{#if detection}
					<div class="overflow-auto p-4">
						{#if detection.description}
							<div class="mb-4">
								<p class="text-[11px] font-semibold uppercase tracking-wider text-cs-text-muted">Description</p>
								<p class="mt-1 text-xs text-cs-text">{detection.description}</p>
							</div>
						{/if}
						{#if detection.parameters.length > 0}
							<div class="mb-4">
								<p class="text-[11px] font-semibold uppercase tracking-wider text-cs-text-muted">Detected Parameters</p>
								<div class="mt-2 flex flex-wrap gap-1.5">
									{#each detection.parameters as p}
										<span class="badge font-mono {p.is_secret ? 'border-warning/40 text-cs-warning' : ''}">{p.key} <span class="text-cs-text-muted">({p.source})</span></span>
									{/each}
								</div>
							</div>
						{/if}
						{#if detection.tags.length > 0}
							<div>
								<p class="text-[11px] font-semibold uppercase tracking-wider text-cs-text-muted">Suggested Tags</p>
								<div class="mt-2 flex flex-wrap gap-1.5">
									{#each detection.tags as t}
										<button class="badge border-accent/30 text-accent hover:bg-accent/10" onclick={() => addTag(t)}>{t} +</button>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{:else}
					<p class="p-4 text-xs italic text-cs-text-muted">Click "Scan Script" to auto-detect parameters, tags, and description from the script header.</p>
				{/if}
			</div>

		{:else if activeTab === 'history'}
			{#if historyLoading}
				<div class="flex h-full items-center justify-center text-xs text-cs-text-muted">Loading…</div>
			{:else}
				<RunHistoryTable runs={runHistory} selectedRunId={selectedRun?.id} onSelect={selectRun} />
			{/if}

		{:else if activeTab === 'logs'}
			<div class="flex h-full flex-col">
				<div class="flex items-center gap-2 border-b border-cs-border px-3 py-1.5">
					<span class="text-xs text-cs-text-muted">Run:</span>
					{#if selectedRun}
						<span class="font-mono text-xs">{selectedRun.id.slice(0, 8)}…</span>
						<span class="text-xs {statusColor(selectedRun.status)}">● {selectedRun.status}</span>
						{#if selectedRun.exit_code !== null}<span class="text-xs text-cs-text-muted">exit {selectedRun.exit_code}</span>{/if}
						<span class="text-xs text-cs-text-muted capitalize">{selectedRun.trigger}</span>
					{:else}
						<span class="text-xs italic text-cs-text-muted">Select a run from the History tab</span>
					{/if}
				</div>
				<div class="flex-1 overflow-hidden">
					<LogPanel
						lines={selectedRun ? selectedRunLogLines : streamLogLines}
						downloadName={selectedRun ? `run-${selectedRun.id.slice(0, 8)}.log` : undefined}
						empty={selectedRun ? 'No logs captured for this run.' : 'Select a run from the History tab.'}
					/>
				</div>
			</div>

		{:else if activeTab === 'metrics'}
			<div class="flex h-full flex-col">
				<div class="flex items-center gap-2 border-b border-cs-border px-3 py-1.5">
					<span class="text-xs text-cs-text-muted">Range:</span>
					{#each (['1d', '7d', '30d', 'all'] as const) as r}
						<button
							class="rounded px-2 py-0.5 text-xs {metricsRange === r ? 'bg-accent/20 text-accent' : 'text-cs-text-muted hover:text-cs-text'}"
							onclick={() => { metricsRange = r; loadMetrics(); }}
						>{r === 'all' ? 'All' : r}</button>
					{/each}
					{#if metricsLoading}<span class="ml-2 animate-pulse text-xs text-cs-text-muted">Loading…</span>{/if}
				</div>
				{#if metrics}
					<MetricsPanel {metrics} />
				{:else if !metricsLoading}
					<p class="p-4 text-xs italic text-cs-text-muted">No metrics yet — run the script first.</p>
				{/if}
			</div>
		{/if}
	</div>
</div>
{:else}
<div class="flex h-full items-center justify-center text-cs-text-muted">Loading…</div>
{/if}
