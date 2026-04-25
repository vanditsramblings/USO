<script lang="ts">
	import { onMount } from 'svelte';
	import * as api from '$lib/api/client';
	import { scripts } from '$lib/stores';
	import type { Schedule } from '$lib/types';
	import { Plus, Trash2, Clock, Pause, Play } from 'lucide-svelte';

	let allSchedules = $state<Schedule[]>([]);
	let loading = $state(true);
	let showCreate = $state(false);

	// Create form
	let scriptId = $state('');
	let triggerType = $state<'cron' | 'interval' | 'date'>('cron');
	let cronMinute = $state('0');
	let cronHour = $state('*');
	let cronDow = $state('*');
	let intervalMinutes = $state(60);
	let runDate = $state('');
	let misfireGrace = $state(60);
	let creating = $state(false);

	onMount(async () => {
		allSchedules = await api.schedules.list();
		loading = false;
	});

	async function createSchedule() {
		if (!scriptId) return;
		creating = true;
		let trigger_args: Record<string, string> = {};
		if (triggerType === 'cron') {
			trigger_args = { minute: cronMinute, hour: cronHour, day_of_week: cronDow };
		} else if (triggerType === 'interval') {
			trigger_args = { minutes: String(intervalMinutes) };
		} else {
			trigger_args = { run_date: runDate };
		}
		try {
			await api.schedules.create({
				script_id: scriptId,
				trigger_type: triggerType,
				trigger_args,
				misfire_grace_time: misfireGrace
			});
			allSchedules = await api.schedules.list();
			showCreate = false;
		} finally {
			creating = false;
		}
	}

	async function toggle(sched: Schedule) {
		await api.schedules.toggle(sched.id, !sched.enabled);
		allSchedules = await api.schedules.list();
	}

	async function remove(id: string) {
		if (!confirm('Delete this schedule?')) return;
		await api.schedules.delete(id);
		allSchedules = allSchedules.filter((s) => s.id !== id);
	}
</script>

<div class="flex h-full flex-col">
	<!-- ── Page header ────────────────────────────────────── -->
	<div
		class="flex flex-shrink-0 items-center justify-between border-b border-cs-border px-6 py-3"
		style="background: var(--color-cs-surface);"
	>
		<div>
			<h1 class="font-mono text-base font-semibold text-cs-text">Schedules</h1>
			<p class="text-xs text-cs-text-muted">
				{allSchedules.length} schedule{allSchedules.length !== 1 ? 's' : ''}
			</p>
		</div>
		<button class="btn-primary flex items-center gap-1.5 text-xs" onclick={() => (showCreate = !showCreate)}>
			<Plus size={13} strokeWidth={2.5} /> New Schedule
		</button>
	</div>

	<!-- ── Create form ────────────────────────────────────── -->
	{#if showCreate}
		<div
			class="flex-shrink-0 border-b border-cs-border px-6 py-4"
			style="background: var(--color-cs-surface);"
		>
			<div class="grid grid-cols-4 gap-3">
				<div>
					<label for="sched-script" class="mb-1 block text-xs font-medium text-cs-text-muted">Script</label>
					<select id="sched-script" class="input text-xs" bind:value={scriptId}>
						<option value="">Select…</option>
						{#each $scripts as s}
							<option value={s.id}>{s.name}</option>
						{/each}
					</select>
				</div>
				<div>
					<label for="sched-trigger" class="mb-1 block text-xs font-medium text-cs-text-muted">Trigger</label>
					<select id="sched-trigger" class="input text-xs" bind:value={triggerType}>
						<option value="cron">Cron</option>
						<option value="interval">Interval</option>
						<option value="date">Date</option>
					</select>
				</div>
				{#if triggerType === 'cron'}
					<div>
						<label for="cron-min" class="mb-1 block text-xs font-medium text-cs-text-muted">Minute / Hour / DOW</label>
						<div class="flex gap-1">
							<input id="cron-min" class="input text-xs" bind:value={cronMinute} placeholder="0" />
							<input id="cron-hour" class="input text-xs" bind:value={cronHour} placeholder="*" />
							<input id="cron-dow" class="input text-xs" bind:value={cronDow} placeholder="*" />
						</div>
					</div>
				{:else if triggerType === 'interval'}
					<div>
						<label for="interval-min" class="mb-1 block text-xs font-medium text-cs-text-muted">Minutes</label>
						<input id="interval-min" class="input text-xs" type="number" bind:value={intervalMinutes} min="1" />
					</div>
				{:else}
					<div>
						<label for="run-date" class="mb-1 block text-xs font-medium text-cs-text-muted">Run Date</label>
						<input id="run-date" class="input text-xs" bind:value={runDate} placeholder="2026-01-01 12:00:00" />
					</div>
				{/if}
				<div class="flex items-end gap-2">
					<button class="btn-primary text-xs" onclick={createSchedule} disabled={creating}>
						{creating ? 'Creating…' : 'Create Schedule'}
					</button>
					<button class="ghost-btn text-xs" onclick={() => (showCreate = false)}>Cancel</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- ── Inventory table ────────────────────────────────── -->
	<div class="flex-1 overflow-auto">
		{#if loading}
			<div class="flex flex-col">
				{#each Array(5) as _}
					<div class="animate-pulse border-b border-cs-border px-6 py-4">
						<div class="flex items-center gap-4">
							<div class="h-2.5 w-2.5 rounded-full bg-cs-surface-2"></div>
							<div class="h-3.5 w-40 rounded bg-cs-surface-2"></div>
							<div class="h-3 w-24 rounded bg-cs-surface-2 ml-8"></div>
							<div class="ml-auto h-3 w-20 rounded bg-cs-surface-2"></div>
						</div>
					</div>
				{/each}
			</div>
		{:else if allSchedules.length === 0}
			<div class="flex flex-col items-center justify-center py-20 text-center">
				<Clock size={32} strokeWidth={1} class="mb-3 text-cs-text-muted opacity-40" />
				<p class="mb-1 text-sm text-cs-text-muted">No schedules configured</p>
				<button class="btn-primary mt-3 text-xs" onclick={() => (showCreate = true)}>
					<Plus size={12} /> Create first schedule
				</button>
			</div>
		{:else}
			<!-- Column headers -->
			<div
				class="grid grid-cols-[2fr_1fr_2fr_1.5fr_1fr_auto] gap-4 border-b border-cs-border px-6 py-2 text-[11px] font-medium uppercase tracking-wider text-cs-text-muted"
				style="background: var(--color-cs-surface);"
			>
				<span>Script</span>
				<span>Trigger</span>
				<span>Args</span>
				<span>Next Run</span>
				<span>Status</span>
				<span class="text-right">Actions</span>
			</div>

			{#each allSchedules as sched (sched.id)}
				{@const script = $scripts.find((s) => s.id === sched.script_id)}
				<div
					class="grid grid-cols-[2fr_1fr_2fr_1.5fr_1fr_auto] items-center gap-4 border-b border-cs-border px-6 py-3.5 text-sm transition-colors hover:bg-cs-surface-2"
					style="min-height: 56px;"
				>
					<div class="min-w-0 flex items-center gap-2">
						<span class="status-dot {sched.enabled ? 'status-dot--running' : 'status-dot--pending'}"></span>
						<span class="truncate font-mono text-sm font-medium text-cs-text">{script?.name ?? '—'}</span>
					</div>

					<span class="badge w-fit">{sched.trigger_type}</span>

					<span class="truncate font-mono text-xs text-cs-text-muted">
						{Object.entries(sched.trigger_args ?? {}).map(([k,v]) => `${k}=${v}`).join(' ')}
					</span>

					<span class="text-xs text-cs-text-muted">
						{sched.next_run_time
							? new Date(sched.next_run_time).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
							: '—'}
					</span>

					<span class="text-xs {sched.enabled ? 'text-cs-success' : 'text-cs-text-muted'}">
						{sched.enabled ? '● Active' : '⏸ Paused'}
					</span>

					<div class="flex items-center justify-end gap-1">
						<button
							class="ghost-btn p-1.5"
							onclick={() => toggle(sched)}
							title={sched.enabled ? 'Pause' : 'Resume'}
						>
							{#if sched.enabled}
								<Pause size={13} strokeWidth={1.75} />
							{:else}
								<Play size={13} strokeWidth={1.75} />
							{/if}
						</button>
						<button class="ghost-btn p-1.5 text-cs-error" onclick={() => remove(sched.id)} title="Delete">
							<Trash2 size={13} strokeWidth={1.75} />
						</button>
					</div>
				</div>
			{/each}
		{/if}
	</div>
</div>
