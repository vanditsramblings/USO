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

<div class="p-6">
	<div class="mb-6 flex items-center gap-2">
		<Clock size={16} strokeWidth={2} class="text-cs-text-muted" />
		<h1 class="text-sm font-medium">Schedules</h1>
		<div class="flex-1"></div>
		<button class="ghost-btn flex items-center gap-1.5" onclick={() => (showCreate = !showCreate)}>
			<Plus size={13} strokeWidth={2} /> New Schedule
		</button>
	</div>

	{#if showCreate}
		<div class="mb-6 rounded-lg border border-cs-border bg-cs-surface p-4">
			<div class="grid grid-cols-4 gap-3">
				<div>
					<label for="sched-script" class="mb-0.5 block text-xs text-cs-text-muted">Script</label>
					<select id="sched-script" class="input text-xs" bind:value={scriptId}>
						<option value="">Select…</option>
						{#each $scripts as s}
							<option value={s.id}>{s.name}</option>
						{/each}
					</select>
				</div>
				<div>
					<label for="sched-trigger" class="mb-0.5 block text-xs text-cs-text-muted">Trigger</label>
					<select id="sched-trigger" class="input text-xs" bind:value={triggerType}>
						<option value="cron">Cron</option>
						<option value="interval">Interval</option>
						<option value="date">Date</option>
					</select>
				</div>
				{#if triggerType === 'cron'}
					<div>
						<label for="cron-min" class="mb-0.5 block text-xs text-cs-text-muted">Minute / Hour / DOW</label>
						<div class="flex gap-1">
							<input id="cron-min" class="input text-xs" bind:value={cronMinute} placeholder="0" />
							<input id="cron-hour" class="input text-xs" bind:value={cronHour} placeholder="*" />
							<input id="cron-dow" class="input text-xs" bind:value={cronDow} placeholder="*" />
						</div>
					</div>
				{:else if triggerType === 'interval'}
					<div>
						<label for="interval-min" class="mb-0.5 block text-xs text-cs-text-muted">Minutes</label>
						<input id="interval-min" class="input text-xs" type="number" bind:value={intervalMinutes} min="1" />
					</div>
				{:else}
					<div>
						<label for="run-date" class="mb-0.5 block text-xs text-cs-text-muted">Run Date</label>
						<input id="run-date" class="input text-xs" bind:value={runDate} placeholder="2026-01-01 12:00:00" />
					</div>
				{/if}
				<div class="flex items-end">
					<button class="btn-primary text-xs" onclick={createSchedule} disabled={creating}>
						{creating ? 'Creating…' : 'Create'}
					</button>
				</div>
			</div>
		</div>
	{/if}

	{#if loading}
		<div class="space-y-3">
			{#each Array(3) as _}
				<div class="animate-pulse rounded-lg border border-cs-border bg-cs-surface p-4">
					<div class="h-4 w-1/3 rounded bg-cs-surface-2"></div>
				</div>
			{/each}
		</div>
	{:else if allSchedules.length === 0}
		<div class="rounded-lg border border-dashed border-cs-border p-8 text-center text-xs text-cs-text-muted">
			No schedules configured
		</div>
	{:else}
		<div class="overflow-hidden rounded-lg border border-cs-border">
			<table class="w-full text-xs">
				<thead class="bg-cs-surface-2">
					<tr>
						<th class="px-3 py-2 text-left font-medium text-cs-text-muted">Script</th>
						<th class="px-3 py-2 text-left font-medium text-cs-text-muted">Trigger</th>
						<th class="px-3 py-2 text-left font-medium text-cs-text-muted">Args</th>
						<th class="px-3 py-2 text-left font-medium text-cs-text-muted">Next Run</th>
						<th class="px-3 py-2 text-left font-medium text-cs-text-muted">Status</th>
						<th class="px-3 py-2 text-right font-medium text-cs-text-muted">Actions</th>
					</tr>
				</thead>
				<tbody>
					{#each allSchedules as sched}
						{@const script = $scripts.find((s) => s.id === sched.script_id)}
						<tr class="border-t border-cs-border hover:bg-bg-hover">
							<td class="px-3 py-2 font-mono">{script?.name ?? '—'}</td>
							<td class="px-3 py-2"><span class="badge">{sched.trigger_type}</span></td>
							<td class="px-3 py-2 font-mono text-cs-text-muted">{JSON.stringify(sched.trigger_args)}</td>
							<td class="px-3 py-2 text-cs-text-muted">{sched.next_run_time ?? '—'}</td>
							<td class="px-3 py-2">
								{#if sched.enabled}
									<span class="text-success">● Active</span>
								{:else}
									<span class="text-cs-text-muted">⏸ Paused</span>
								{/if}
							</td>
							<td class="flex items-center justify-end gap-1 px-3 py-2">
								<button class="ghost-btn p-1" onclick={() => toggle(sched)} title={sched.enabled ? 'Pause' : 'Resume'}>
									{#if sched.enabled}
										<Pause size={12} />
									{:else}
										<Play size={12} />
									{/if}
								</button>
								<button class="ghost-btn p-1 text-cs-error" onclick={() => remove(sched.id)}>
									<Trash2 size={12} />
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
