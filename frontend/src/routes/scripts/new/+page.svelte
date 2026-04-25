<script lang="ts">
	import { goto } from '$app/navigation';
	import { loadScripts, loadTags, tags as allTags } from '$lib/stores';
	import * as api from '$lib/api/client';
	import { ArrowLeft, X } from 'lucide-svelte';
	import CodeEditor from '$lib/components/CodeEditor.svelte';

	type Runtime = 'py' | 'sh' | 'js';

	let name = $state('');
	let runtime = $state<Runtime>('py');
	let description = $state('');
	let content = $state('');
	let creating = $state(false);
	let error = $state('');

	let selectedTags = $state<string[]>([]);
	let newTagInput = $state('');

	function toggleTag(tagName: string) {
		selectedTags = selectedTags.includes(tagName)
			? selectedTags.filter((t) => t !== tagName)
			: [...selectedTags, tagName];
	}

	function addCustomTag() {
		const tag = newTagInput.trim().replace(/\s+/g, '-');
		if (tag && !selectedTags.includes(tag)) selectedTags = [...selectedTags, tag];
		newTagInput = '';
	}

	async function handleCreate(e: Event) {
		e.preventDefault();
		if (!name.trim() || !content.trim()) {
			error = 'Name and content are required.';
			return;
		}
		error = '';
		creating = true;
		try {
			const script = await api.scripts.create({
				name: name.trim(),
				runtime,
				content,
				description: description.trim() || undefined,
				tags: selectedTags
			});
			await Promise.all([loadScripts(), loadTags()]);
			goto(`/scripts/${script.id}`);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to create script.';
		} finally {
			creating = false;
		}
	}
</script>

<div class="flex h-full flex-col">
	<!-- Header -->
	<div
		class="flex flex-shrink-0 items-center gap-3 border-b border-cs-border px-6 py-3"
		style="background: var(--color-cs-surface);"
	>
		<a href="/scripts" class="ghost-btn flex items-center gap-1.5 text-xs">
			<ArrowLeft size={13} /> Scripts
		</a>
		<span class="text-cs-text-muted">/</span>
		<h1 class="font-mono text-base font-semibold text-cs-text">New Script</h1>
	</div>

	<!-- Form -->
	<div class="flex-1 overflow-auto px-6 py-6">
		<form onsubmit={handleCreate} class="mx-auto max-w-2xl flex flex-col gap-5">
			{#if error}
				<div class="rounded border border-cs-error/40 bg-cs-error/10 px-4 py-2 text-xs text-cs-error">
					{error}
				</div>
			{/if}

			<!-- Name + Runtime row -->
			<div class="flex gap-3">
				<div class="flex-1">
					<label for="script-name" class="mb-1 block text-xs font-medium text-cs-text-muted"
						>Name <span class="text-cs-error">*</span></label
					>
					<input
						id="script-name"
						class="input"
						placeholder="my_script"
						bind:value={name}
						required
					/>
				</div>
				<div class="w-40">
					<label for="script-runtime" class="mb-1 block text-xs font-medium text-cs-text-muted"
						>Runtime</label
					>
					<select id="script-runtime" class="input" bind:value={runtime}>
						<option value="py">Python</option>
						<option value="sh">Shell</option>
						<option value="js">JavaScript</option>
					</select>
				</div>
			</div>

			<!-- Description -->
			<div>
				<label for="script-desc" class="mb-1 block text-xs font-medium text-cs-text-muted"
					>Description</label
				>
				<input
					id="script-desc"
					class="input"
					placeholder="What does this script do?"
					bind:value={description}
				/>
			</div>

			<!-- Content -->
			<div>
				<p class="mb-1 text-xs font-medium text-cs-text-muted">Content <span class="text-cs-error">*</span></p>
				<div
					class="overflow-hidden rounded border border-cs-border"
					style="height: 320px;"
				>
					<CodeEditor
						{content}
						language={runtime}
						onChange={(val) => {
							content = val;
						}}
					/>
				</div>
			</div>

			<!-- Tags -->
			<div>
				<p class="mb-1 text-xs font-medium text-cs-text-muted">Tags</p>
				<div class="flex flex-wrap gap-1.5 mb-2">
					{#each $allTags as tag}
						<button
							type="button"
							class="rounded px-2 py-0.5 text-xs border cursor-pointer transition-colors
								{selectedTags.includes(tag.name)
									? 'border-cs-accent text-cs-accent bg-cs-accent-dim'
									: 'border-cs-border text-cs-text-muted hover:border-cs-accent hover:text-cs-accent'}"
							onclick={() => toggleTag(tag.name)}
						>{tag.name}</button>
					{/each}
				</div>
				<div class="flex gap-2">
					<input
						class="input text-xs flex-1 max-w-xs"
						placeholder="New tag…"
						bind:value={newTagInput}
						onkeydown={(e) =>
							e.key === 'Enter' && (e.preventDefault(), addCustomTag())}
					/>
					<button type="button" class="ghost-btn text-xs" onclick={addCustomTag}>Add</button>
				</div>
				{#if selectedTags.length > 0}
					<div class="mt-2 flex flex-wrap gap-1.5">
						{#each selectedTags as tag}
							<span class="flex items-center gap-1 rounded bg-cs-accent-dim px-2 py-0.5 text-xs text-cs-accent">
								{tag}
								<button
									type="button"
									class="hover:text-cs-error"
									onclick={() => (selectedTags = selectedTags.filter((t) => t !== tag))}
									aria-label="Remove tag {tag}"
								><X size={10} /></button>
							</span>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Actions -->
			<div class="flex items-center gap-3 pt-2 border-t border-cs-border">
				<button type="submit" class="btn-primary" disabled={creating}>
					{creating ? 'Creating…' : 'Create Script'}
				</button>
				<a href="/scripts" class="ghost-btn text-sm">Cancel</a>
			</div>
		</form>
	</div>
</div>
