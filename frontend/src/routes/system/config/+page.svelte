<script lang="ts">
	import { onMount } from 'svelte';
	import { config as configApi } from '$lib/api/client';
	import { Settings, RotateCcw, Save } from 'lucide-svelte';

	type ConfigData = Record<string, Record<string, unknown>>;

	let cfg = $state<ConfigData | null>(null);
	let dirty = $state<ConfigData>({});
	let saving = $state(false);
	let saved = $state(false);
	let error = $state('');

	onMount(async () => {
		cfg = (await configApi.get()) as ConfigData;
		dirty = JSON.parse(JSON.stringify(cfg));
	});

	async function save() {
		saving = true;
		error = '';
		try {
			const updated = (await configApi.patch(dirty)) as ConfigData;
			cfg = updated;
			dirty = JSON.parse(JSON.stringify(updated));
			saved = true;
			setTimeout(() => (saved = false), 2000);
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			saving = false;
		}
	}

	async function reset() {
		if (!confirm('Reset all settings to defaults?')) return;
		const updated = (await configApi.reset()) as ConfigData;
		cfg = updated;
		dirty = JSON.parse(JSON.stringify(updated));
	}

	function setField(section: string, key: string, value: unknown) {
		dirty[section] = { ...(dirty[section] ?? {}), [key]: value };
	}

	function boolVal(section: string, key: string): boolean {
		return !!(dirty[section]?.[key] ?? false);
	}

	function numVal(section: string, key: string): number {
		return Number(dirty[section]?.[key] ?? 0);
	}

	function strVal(section: string, key: string): string {
		return String(dirty[section]?.[key] ?? '');
	}

	const SECTIONS: Array<{
		id: string;
		label: string;
		icon: string;
		fields: Array<{
			key: string;
			label: string;
			type: string;
			hint?: string;
			options?: string[];
		}>;
	}> = [
		{
			id: 'general',
			label: 'General',
			icon: '⚙️',
			fields: [
				{ key: 'app_name', label: 'App Name', type: 'text' },
				{ key: 'base_url', label: 'Base URL', type: 'text' },
				{ key: 'debug', label: 'Debug Mode', type: 'bool' }
			]
		},
		{
			id: 'logging',
			label: 'Logging',
			icon: '📋',
			fields: [
				{
					key: 'level',
					label: 'Log Level',
					type: 'select',
					options: ['DEBUG', 'INFO', 'WARNING', 'ERROR']
				},
				{ key: 'format', label: 'Log Format', type: 'select', options: ['text', 'json'] },
				{
					key: 'max_log_bytes',
					label: 'Max Log Size (bytes)',
					type: 'number',
					hint: 'Max bytes stored per run log'
				}
			]
		},
		{
			id: 'execution',
			label: 'Execution',
			icon: '▶️',
			fields: [
				{
					key: 'default_timeout',
					label: 'Default Timeout (s)',
					type: 'number',
					hint: '5–3600s'
				},
				{ key: 'max_timeout', label: 'Max Timeout (s)', type: 'number' },
				{ key: 'max_concurrent_runs', label: 'Max Concurrent Runs', type: 'number' },
				{ key: 'allow_network', label: 'Allow Network Access', type: 'bool' }
			]
		},
		{
			id: 'persistence',
			label: 'Persistence',
			icon: '💾',
			fields: [
				{ key: 'db_path', label: 'Database Path', type: 'text' },
				{ key: 'uploads_dir', label: 'Uploads Directory', type: 'text' },
				{ key: 'outputs_dir', label: 'Outputs Directory', type: 'text' },
				{
					key: 'max_upload_bytes',
					label: 'Max Upload Size (bytes)',
					type: 'number'
				},
				{
					key: 'artifact_retention_days',
					label: 'Artifact Retention (days)',
					type: 'number'
				}
			]
		},
		{
			id: 'scheduler',
			label: 'Scheduler',
			icon: '🕐',
			fields: [
				{
					key: 'misfire_grace_seconds',
					label: 'Misfire Grace Period (s)',
					type: 'number',
					hint: 'How long after missed trigger to still run'
				},
				{ key: 'max_instances', label: 'Max Instances per Job', type: 'number' },
				{ key: 'coalesce', label: 'Coalesce Missed Runs', type: 'bool' }
			]
		}
	];
</script>

<svelte:head>
	<title>USO — System Configuration</title>
</svelte:head>

<div class="mx-auto max-w-3xl space-y-6 p-6">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-2">
			<Settings size={18} class="text-accent" />
			<h1 class="text-base font-semibold">System Configuration</h1>
		</div>
		<div class="flex gap-2">
			<button class="ghost-btn flex items-center gap-1" onclick={reset}>
				<RotateCcw size={13} />
				Reset to Defaults
			</button>
			<button
				class="btn-primary flex items-center gap-1"
				onclick={save}
				disabled={saving}
			>
				<Save size={13} />
				{saving ? 'Saving…' : saved ? '✓ Saved' : 'Save Changes'}
			</button>
		</div>
	</div>

	{#if error}
		<div class="rounded border border-red-500/30 bg-red-500/10 p-3 text-sm text-cs-error">{error}</div>
	{/if}

	{#if !cfg}
		<div class="text-sm text-cs-text-muted">Loading configuration…</div>
	{:else}
		{#each SECTIONS as section}
			<section class="rounded-lg border border-cs-border bg-cs-surface">
				<div class="flex items-center gap-2 border-b border-cs-border px-4 py-3">
					<span>{section.icon}</span>
					<h2 class="text-sm font-semibold">{section.label}</h2>
				</div>
				<div class="divide-y divide-border">
					{#each section.fields as field}
						<div class="flex items-center justify-between px-4 py-3">
							<div>
								<div class="text-sm font-medium">{field.label}</div>
								{#if field.hint}
									<div class="text-xs text-cs-text-muted">{field.hint}</div>
								{/if}
							</div>
							<div class="min-w-[200px]">
								{#if field.type === 'bool'}
									<label class="flex cursor-pointer items-center gap-2">
										<input
											type="checkbox"
											checked={boolVal(section.id, field.key)}
											onchange={(e) =>
												setField(section.id, field.key, (e.target as HTMLInputElement).checked)}
											class="h-4 w-4 rounded accent-accent"
										/>
										<span class="text-xs text-cs-text-muted">{boolVal(section.id, field.key) ? 'Enabled' : 'Disabled'}</span>
									</label>
								{:else if field.type === 'select'}
									<select
										class="input w-full"
										value={strVal(section.id, field.key)}
										onchange={(e) =>
											setField(section.id, field.key, (e.target as HTMLSelectElement).value)}
									>
										{#each field.options ?? [] as opt}
											<option value={opt}>{opt}</option>
										{/each}
									</select>
								{:else if field.type === 'number'}
									<input
										type="number"
										class="input w-full"
										value={numVal(section.id, field.key)}
										oninput={(e) =>
											setField(section.id, field.key, Number((e.target as HTMLInputElement).value))}
									/>
								{:else}
									<input
										type="text"
										class="input w-full"
										value={strVal(section.id, field.key)}
										oninput={(e) =>
											setField(section.id, field.key, (e.target as HTMLInputElement).value)}
									/>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			</section>
		{/each}
	{/if}
</div>
