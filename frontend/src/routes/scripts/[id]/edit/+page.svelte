<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { loadScripts, loadTags, tags as allTags } from '$lib/stores';
	import * as api from '$lib/api/client';
	import type { Script, Tag, DetectionResult } from '$lib/types';
	import { ArrowLeft, Save, Scan, X } from 'lucide-svelte';
	import CodeEditor from '$lib/components/CodeEditor.svelte';
	import { onMount } from 'svelte';

	let script = $state<Script | null>(null);
	let editContent = $state('');
	let editDesc = $state('');
	let dirty = $state(false);
	let saving = $state(false);
	let saveError = $state('');

	let detection = $state<DetectionResult | null>(null);
	let detecting = $state(false);

	let scriptTags = $state<Tag[]>([]);
	let newTagInput = $state('');

	// Confirm-leave guard
	let showLeaveConfirm = $state(false);

	const id = $derived(page.params.id);

	async function loadScript() {
		script = await api.scripts.get(id!);
		if (script) {
			editContent = script.content;
			editDesc = script.description ?? '';
			scriptTags = await api.tags.forScript(script.id);
		}
	}

	onMount(loadScript);
	$effect(() => {
		if (id) loadScript();
	});

	$effect(() => {
		dirty = script
			? editContent !== script.content || editDesc !== (script.description ?? '')
			: false;
	});

	async function save() {
		if (!script) return;
		saving = true;
		saveError = '';
		try {
			await api.scripts.update(script.id, { content: editContent, description: editDesc });
			await loadScripts();
			dirty = false;
			goto(`/scripts/${script.id}`);
		} catch (err) {
			saveError = err instanceof Error ? err.message : 'Save failed.';
		} finally {
			saving = false;
		}
	}

	function cancel() {
		if (dirty) {
			showLeaveConfirm = true;
		} else {
			goto(`/scripts/${id}`);
		}
	}

	async function detect() {
		if (!script) return;
		detecting = true;
		try {
			detection = await api.detect(editContent, script.runtime);
		} finally {
			detecting = false;
		}
	}

	async function addTag(name: string) {
		if (!script) return;
		const tag = await api.tags
			.create(name)
			.catch(() => api.tags.list().then((all) => all.find((t) => t.name === name)!));
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
</script>

{#if script}
	<div class="flex h-full flex-col">
		<!-- ── Toolbar ─────────────────────────────────────── -->
		<div
			class="flex flex-shrink-0 items-center gap-2 border-b border-cs-border px-4 py-2"
			style="background: var(--color-cs-surface);"
		>
			<nav class="flex items-center gap-1 text-xs text-cs-text-muted">
				<a href="/scripts" class="hover:text-cs-text">Scripts</a>
				<span>/</span>
				<a href="/scripts/{script.id}" class="hover:text-cs-text">{script.name}</a>
				<span>/</span>
				<span class="text-cs-text">Edit</span>
			</nav>
			<div class="flex-1"></div>

			{#if dirty}
				<span class="text-xs text-cs-text-muted">Unsaved changes</span>
			{/if}

			<button
				class="ghost-btn flex items-center gap-1.5 text-xs"
				onclick={detect}
				disabled={detecting}
				title="Auto-detect parameters and tags"
			>
				<Scan size={13} strokeWidth={2} />
				{detecting ? 'Detecting…' : 'Detect'}
			</button>

			<button class="ghost-btn text-sm" onclick={cancel}>Cancel</button>

			<button
				class="btn-primary flex items-center gap-1.5"
				onclick={save}
				disabled={saving || !dirty}
			>
				<Save size={13} strokeWidth={2} />
				{saving ? 'Saving…' : 'Save'}
			</button>
		</div>

		<!-- ── Save error ─────────────────────────────────── -->
		{#if saveError}
			<div class="border-b border-cs-error/40 bg-cs-error/10 px-4 py-2 text-xs text-cs-error">
				{saveError}
			</div>
		{/if}

		<!-- ── Detection banner ───────────────────────────── -->
		{#if detection}
			<div class="border-b border-cs-border bg-cs-surface-2 px-4 py-2">
				<div class="mb-1 text-xs font-medium text-cs-accent">Auto-Detected</div>
				{#if detection.description}
					<p class="mb-1 text-xs text-cs-text-muted">{detection.description}</p>
				{/if}
				{#if detection.parameters.length > 0}
					<div class="flex flex-wrap gap-1">
						{#each detection.parameters as p}
							<span
								class="badge font-mono {p.is_secret
									? 'border-warning/40 text-cs-warning'
									: ''}"
							>
								{p.key}
							</span>
						{/each}
					</div>
				{/if}
				{#if detection.tags.length > 0}
					<div class="mt-1 flex flex-wrap gap-1">
						{#each detection.tags as t}
							<button
								class="badge border-cs-accent/30 text-cs-accent hover:bg-cs-accent/10"
								onclick={() => addTag(t)}
							>{t} +</button>
						{/each}
					</div>
				{/if}
			</div>
		{/if}

		<!-- ── Main edit area ─────────────────────────────── -->
		<div class="flex flex-1 flex-col overflow-hidden">
			<!-- Description field -->
			<div class="flex-shrink-0 border-b border-cs-border px-4 py-2">
				<input
					class="input text-sm"
					placeholder="Description…"
					bind:value={editDesc}
				/>
			</div>

			<!-- Code editor -->
			<div class="flex-1 overflow-hidden" style="background: var(--color-cs-bg);">
				<CodeEditor
					content={editContent}
					language={script.runtime}
					onChange={(val) => {
						editContent = val;
					}}
				/>
			</div>

			<!-- Tags strip -->
			<div class="flex flex-shrink-0 items-center gap-2 border-t border-cs-border px-4 py-2">
				<span class="text-xs text-cs-text-muted shrink-0">Tags:</span>
				<div class="flex flex-wrap gap-1 flex-1">
					{#each scriptTags as tag}
						<span class="badge border-cs-accent/30 text-cs-accent">
							{tag.name}
							<button
								class="ml-1 hover:text-cs-error"
								onclick={() => removeTag(tag.id)}
								aria-label="Remove tag {tag.name}"
							><X size={10} /></button>
						</span>
					{/each}
					{#each $allTags.filter((t) => !scriptTags.some((st) => st.id === t.id)) as available}
						<button
							class="badge cursor-pointer hover:border-cs-accent/30 hover:text-cs-accent"
							onclick={() => addTag(available.name)}
						>{available.name}</button>
					{/each}
				</div>
				<div class="flex gap-1 shrink-0">
					<input
						class="input text-xs w-28"
						placeholder="New tag…"
						bind:value={newTagInput}
						onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), handleNewTag())}
					/>
					<button class="ghost-btn text-xs" onclick={handleNewTag}>+</button>
				</div>
			</div>
		</div>
	</div>

	<!-- ── Leave confirmation ─────────────────────────────── -->
	{#if showLeaveConfirm}
		<div
			class="fixed inset-0 z-50 flex items-center justify-center"
			style="background: rgba(0,0,0,0.5);"
		>
			<div
				class="mx-4 max-w-sm rounded-lg border border-cs-border p-5"
				style="background: var(--color-cs-surface);"
			>
				<h2 class="mb-2 text-sm font-semibold text-cs-text">Discard changes?</h2>
				<p class="mb-4 text-xs text-cs-text-muted">
					You have unsaved changes. Leaving will discard them.
				</p>
				<div class="flex gap-2 justify-end">
					<button
						class="ghost-btn text-xs"
						onclick={() => (showLeaveConfirm = false)}
					>Keep editing</button>
					<button
						class="btn-danger text-xs"
						onclick={() => goto(`/scripts/${id}`)}
					>Discard</button>
				</div>
			</div>
		</div>
	{/if}
{:else}
	<div class="flex h-full items-center justify-center text-cs-text-muted">Loading…</div>
{/if}
