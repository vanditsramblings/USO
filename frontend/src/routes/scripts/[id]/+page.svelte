<script lang="ts">
	import { page } from '$app/state';
	import { graphSelectedNode, flyoutOpen, tags as allTags } from '$lib/stores';
	import * as api from '$lib/api/client';
	import { loadScripts, loadTags } from '$lib/stores';
	import type { Script, Run, Tag, DetectionResult } from '$lib/types';
	import { Play, Save, Scan, Trash2, Terminal, Tag as TagIcon } from 'lucide-svelte';
	import { Splitpanes, Pane } from 'svelte-splitpanes';
	import CodeEditor from '$lib/components/CodeEditor.svelte';
	import VirtualLog from '$lib/components/VirtualLog.svelte';
	import { onMount } from 'svelte';

	let script = $state<Script | null>(null);
	let editContent = $state('');
	let editDesc = $state('');
	let dirty = $state(false);
	let saving = $state(false);

	// Execution
	let envValues = $state<Record<string, string>>({});
	let timeout = $state(60);
	let running = $state(false);
	let logs = $state('');
	let logLines = $derived(logs ? logs.split('\n') : []);
	let runResult = $state<Run | null>(null);
	let showExec = $state(false);

	// Detection
	let detection = $state<DetectionResult | null>(null);

	// Tags
	let scriptTags = $state<Tag[]>([]);
	let newTagInput = $state('');
	let showTags = $state(false);

	const id = $derived(page.params.id);

	async function loadScript() {
		script = await api.scripts.get(id!);
		if (script) {
			editContent = script.content;
			editDesc = script.description ?? '';
			activeScriptId.set(script.id);
			drawerOpen.set(true);
			envValues = {};
			for (const p of script.parameters) {
				envValues[p.key] = '';
			}
			scriptTags = await api.tags.forScript(script.id);
		}
	}

	onMount(loadScript);
	$effect(() => { if (id) loadScript(); });

	$effect(() => {
		dirty = script ? editContent !== script.content || editDesc !== (script.description ?? '') : false;
	});

	async function save() {
		if (!script || !dirty) return;
		saving = true;
		try {
			await api.scripts.update(script.id, { content: editContent, description: editDesc });
			await loadScript();
			await loadScripts();
			dirty = false;
		} finally {
			saving = false;
		}
	}

	async function runScript() {
		if (!script) return;
		running = true;
		logs = '';
		runResult = null;
		showExec = true;

		try {
			// Try WebSocket first
			const wsUrl = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/runs/${script.id}`;
			const ws = new WebSocket(wsUrl);

			ws.onopen = () => {
				ws.send(JSON.stringify({ env: envValues, timeout }));
			};

			ws.onmessage = (event) => {
				const msg = JSON.parse(event.data);
				if (msg.type === 'log') {
					logs += msg.data;
				} else if (msg.type === 'complete') {
					runResult = { id: msg.run_id, script_id: script!.id, status: msg.status, exit_code: msg.exit_code, start_time: null, end_time: null, logs } as Run;
					running = false;
				} else if (msg.type === 'error') {
					logs += `\nError: ${msg.detail}`;
					running = false;
				}
			};

			ws.onerror = async () => {
				// Fallback to REST
				ws.close();
				try {
					const result = await api.runs.create({ script_id: script!.id, env: envValues, timeout });
					runResult = result;
					logs = result.logs ?? '';
				} finally {
					running = false;
				}
			};

			ws.onclose = () => {
				if (running) running = false;
			};
		} catch {
			// REST fallback
			try {
				const result = await api.runs.create({ script_id: script.id, env: envValues, timeout });
				runResult = result;
				logs = result.logs ?? '';
			} finally {
				running = false;
			}
		}
	}

	async function detectScript() {
		if (!script) return;
		detection = await api.detect(editContent, script.runtime);
	}

	async function addTag(name: string) {
		if (!script) return;
		const tag = await api.tags.create(name).catch(() =>
			api.tags.list().then((all) => all.find((t) => t.name === name)!)
		);
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
		window.location.href = '/';
	}

	function statusColor(status: string) {
		switch (status) {
			case 'success': return 'text-success';
			case 'failure': return 'text-cs-error';
			case 'timeout': return 'text-cs-warning';
			default: return 'text-cs-text-muted';
		}
	}
</script>

{#if script}
	<div class="flex h-full flex-col">
		<!-- Toolbar -->
		<div class="flex items-center gap-2 border-b border-cs-border px-4 py-2">
			<nav class="flex items-center gap-1 text-xs text-cs-text-muted">
				<a href="/" class="hover:text-text">Scripts</a>
				<span>/</span>
				<span class="text-text">{script.name}</span>
			</nav>
			<div class="flex-1"></div>
			<button class="ghost-btn flex items-center gap-1.5" onclick={detectScript} title="Auto-detect parameters">
				<Scan size={13} strokeWidth={2} /> Detect
			</button>
			<button class="ghost-btn flex items-center gap-1.5" onclick={() => (showExec = !showExec)}>
				<Terminal size={13} strokeWidth={2} /> Execute
			</button>
			<button class="ghost-btn flex items-center gap-1.5" onclick={() => (showTags = !showTags)}>
				<TagIcon size={13} strokeWidth={2} /> Tags
				{#if scriptTags.length > 0}
					<span class="rounded-full bg-accent/20 px-1.5 text-[10px] text-accent">{scriptTags.length}</span>
				{/if}
			</button>
			{#if dirty}
				<button class="btn-primary flex items-center gap-1.5" onclick={save} disabled={saving}>
					<Save size={13} strokeWidth={2} /> {saving ? 'Saving…' : 'Save'}
				</button>
			{/if}
			<button class="ghost-btn text-cs-error" onclick={deleteScript} title="Delete">
				<Trash2 size={13} strokeWidth={2} />
			</button>
		</div>

		<!-- Detection banner -->
		{#if detection}
			<div class="border-b border-cs-border bg-cs-surface-2 px-4 py-2">
				<div class="mb-1 text-xs font-medium text-accent">Auto-Detected</div>
				{#if detection.description}
					<p class="mb-1 text-xs text-cs-text-muted">📝 {detection.description}</p>
				{/if}
				{#if detection.parameters.length > 0}
					<div class="flex flex-wrap gap-1">
						{#each detection.parameters as p}
							<span class="badge font-mono {p.is_secret ? 'border-warning/40 text-cs-warning' : ''}">
								{p.key} <span class="text-cs-text-muted">({p.source})</span>
							</span>
						{/each}
					</div>
				{/if}
				{#if detection.tags.length > 0}
					<div class="mt-1 flex gap-1">
						{#each detection.tags as t}
							<button
								class="badge border-accent/30 text-accent hover:bg-accent/10"
								onclick={() => addTag(t)}
								title="Click to apply tag"
							>{t} +</button>
						{/each}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Tag management panel -->
		{#if showTags}
			<div class="flex items-center gap-2 border-b border-cs-border bg-cs-surface-2 px-4 py-2">
				<span class="text-xs text-cs-text-muted shrink-0">Tags:</span>
				<div class="flex flex-wrap gap-1 flex-1">
					{#each scriptTags as tag}
						<span class="badge border-accent/30 text-accent">
							{tag.name}
							<button class="ml-1 hover:text-cs-error" onclick={() => removeTag(tag.id)}>×</button>
						</span>
					{/each}
					{#each $allTags.filter((t) => !scriptTags.some((st) => st.id === t.id)) as available}
						<button
							class="badge cursor-pointer hover:border-accent/30 hover:text-accent"
							onclick={() => addTag(available.name)}
						>{available.name}</button>
					{/each}
				</div>
				<div class="flex gap-1 shrink-0">
					<input
						class="input text-xs w-24"
						placeholder="New tag…"
						bind:value={newTagInput}
						onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), handleNewTag())}
					/>
					<button class="ghost-btn text-xs" onclick={handleNewTag}>+</button>
				</div>
			</div>
		{/if}

		<!-- Main content -->
		<Splitpanes class="flex-1 overflow-hidden">
			<Pane minSize={30}>
				<Splitpanes horizontal>
					<!-- Code editor pane -->
					<Pane minSize={20} size={showExec ? 60 : 100}>
						<div class="flex h-full flex-col overflow-hidden">
							<div class="border-b border-cs-border px-4 py-2">
								<input
									class="input text-xs"
									placeholder="Description…"
									bind:value={editDesc}
								/>
							</div>
							<div class="flex-1 overflow-hidden bg-bg">
								<CodeEditor
									content={editContent}
									language={script.runtime}
									onChange={(val) => { editContent = val; }}
								/>
							</div>
						</div>
					</Pane>
					<!-- Log stream pane (visible when exec panel is open) -->
					{#if showExec}
						<Pane minSize={15} size={40}>
							<div class="flex h-full flex-col overflow-hidden bg-bg">
								<div class="flex items-center gap-2 border-b border-cs-border px-3 py-1.5">
									<Terminal size={12} class="text-cs-text-muted" />
									<span class="text-xs font-medium uppercase tracking-wider text-cs-text-muted">Output</span>
									{#if runResult}
										<span class={`text-xs ${statusColor(runResult.status)}`}>● {runResult.status}</span>
										{#if runResult.exit_code !== null}
											<span class="text-xs text-cs-text-muted">exit: {runResult.exit_code}</span>
										{/if}
									{/if}
								</div>
								<div class="flex-1 overflow-hidden">
									{#if logLines.length}
										<VirtualLog lines={logLines} />
									{:else}
										<p class="p-3 text-xs text-cs-text-muted">No output yet</p>
									{/if}
								</div>
							</div>
						</Pane>
					{/if}
				</Splitpanes>
			</Pane>
			<!-- Execution Panel (right pane) -->
			{#if showExec}
				<Pane size={25} minSize={15} maxSize={40}>
					<div class="flex h-full flex-col border-l border-cs-border overflow-hidden">
						<div class="border-b border-cs-border p-3">
							<h4 class="mb-2 text-xs font-medium uppercase tracking-wider text-cs-text-muted">Environment</h4>
							{#if script.parameters.length === 0}
								<p class="text-xs text-cs-text-muted">No parameters defined</p>
							{:else}
								{#each script.parameters as param, i}
									<div class="mb-2">
										<label for="param-{i}" class="mb-0.5 flex items-center gap-1 text-xs text-cs-text-muted">
											{param.key}
											{#if param.is_secret}
												<span class="text-cs-warning">🔒</span>
											{/if}
										</label>
										<input
											id="param-{i}"
											class="input font-mono text-xs"
											type={param.is_secret ? 'password' : 'text'}
											bind:value={envValues[param.key]}
										/>
									</div>
								{/each}
							{/if}
						</div>
						<div class="border-b border-cs-border p-3">
							<label for="timeout" class="mb-0.5 block text-xs text-cs-text-muted">Timeout (s)</label>
							<input id="timeout" class="input text-xs" type="number" min="5" max="300" bind:value={timeout} />
						</div>
						<div class="p-3">
							<button class="btn-primary flex w-full items-center justify-center gap-1.5" onclick={runScript} disabled={running}>
								<Play size={13} strokeWidth={2} /> {running ? 'Running…' : 'Execute'}
							</button>
						</div>
					</div>
				</Pane>
			{/if}
		</Splitpanes>
	</div>
{:else}
	<div class="flex h-full items-center justify-center text-cs-text-muted">Loading…</div>
{/if}
