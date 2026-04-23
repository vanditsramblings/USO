<script lang="ts">
	import { onMount } from 'svelte';
	import * as api from '$lib/api/client';
	import { scripts } from '$lib/stores';
	import type { Run } from '$lib/types';
	import { BarChart3, CheckCircle, XCircle, Clock, Timer } from 'lucide-svelte';

	let allRuns = $state<Run[]>([]);
	let loading = $state(true);

	onMount(async () => {
		allRuns = await api.runs.list(undefined, 500);
		loading = false;
	});

	let stats = $derived.by(() => {
		const total = allRuns.length;
		const success = allRuns.filter((r) => r.status === 'success').length;
		const failure = allRuns.filter((r) => r.status === 'failure').length;
		const timeout = allRuns.filter((r) => r.status === 'timeout').length;
		const pending = allRuns.filter((r) => r.status === 'pending' || r.status === 'running').length;
		return { total, success, failure, timeout, pending };
	});

	// Runs per script
	let scriptStats = $derived.by(() => {
		const map = new Map<string, { name: string; total: number; success: number; failure: number }>();
		for (const run of allRuns) {
			const script = $scripts.find((s) => s.id === run.script_id);
			const name = script?.name ?? run.script_id.slice(0, 8);
			const entry = map.get(run.script_id) ?? { name, total: 0, success: 0, failure: 0 };
			entry.total++;
			if (run.status === 'success') entry.success++;
			if (run.status === 'failure') entry.failure++;
			map.set(run.script_id, entry);
		}
		return [...map.values()].sort((a, b) => b.total - a.total);
	});

	// Execution time trend (last 20 runs with timing)
	let timeTrend = $derived.by(() => {
		return allRuns
			.filter((r) => r.start_time && r.end_time)
			.slice(0, 20)
			.map((r) => {
				const duration = (new Date(r.end_time!).getTime() - new Date(r.start_time!).getTime()) / 1000;
				return { id: r.id, duration, status: r.status, scriptId: r.script_id };
			});
	});

	function barWidth(count: number, max: number) {
		return max > 0 ? `${(count / max) * 100}%` : '0%';
	}
</script>

<div class="p-6">
	<div class="mb-6 flex items-center gap-2">
		<BarChart3 size={16} strokeWidth={2} class="text-cs-text-muted" />
		<h1 class="text-sm font-medium">Run Analytics</h1>
	</div>

	{#if loading}
		<div class="grid grid-cols-4 gap-3">
			{#each Array(4) as _}
				<div class="animate-pulse rounded-lg border border-cs-border bg-cs-surface p-4">
					<div class="mb-2 h-3 w-1/2 rounded bg-cs-surface-2"></div>
					<div class="h-6 w-1/3 rounded bg-cs-surface-2"></div>
				</div>
			{/each}
		</div>
	{:else}
		<!-- Summary Cards -->
		<div class="mb-6 grid grid-cols-4 gap-3">
			<div class="rounded-lg border border-cs-border bg-cs-surface p-4">
				<div class="mb-1 flex items-center gap-1.5 text-cs-text-muted">
					<BarChart3 size={12} /><span class="text-xs uppercase tracking-wider">Total</span>
				</div>
				<span class="font-mono text-2xl font-bold">{stats.total}</span>
			</div>
			<div class="rounded-lg border border-cs-border bg-cs-surface p-4">
				<div class="mb-1 flex items-center gap-1.5 text-success">
					<CheckCircle size={12} /><span class="text-xs uppercase tracking-wider">Success</span>
				</div>
				<span class="font-mono text-2xl font-bold text-success">{stats.success}</span>
			</div>
			<div class="rounded-lg border border-cs-border bg-cs-surface p-4">
				<div class="mb-1 flex items-center gap-1.5 text-cs-error">
					<XCircle size={12} /><span class="text-xs uppercase tracking-wider">Failed</span>
				</div>
				<span class="font-mono text-2xl font-bold text-cs-error">{stats.failure}</span>
			</div>
			<div class="rounded-lg border border-cs-border bg-cs-surface p-4">
				<div class="mb-1 flex items-center gap-1.5 text-cs-warning">
					<Clock size={12} /><span class="text-xs uppercase tracking-wider">Timeout</span>
				</div>
				<span class="font-mono text-2xl font-bold text-cs-warning">{stats.timeout}</span>
			</div>
		</div>

		<div class="grid grid-cols-2 gap-6">
			<!-- Runs per Script -->
			<div>
				<h3 class="mb-3 text-xs font-medium uppercase tracking-wider text-cs-text-muted">Runs by Script</h3>
				{#if scriptStats.length === 0}
					<p class="text-xs text-cs-text-muted">No data</p>
				{:else}
					{@const maxTotal = Math.max(...scriptStats.map((s) => s.total))}
					<div class="flex flex-col gap-2">
						{#each scriptStats as entry}
							<div>
								<div class="mb-1 flex items-center justify-between text-xs">
									<span class="font-mono">{entry.name}</span>
									<span class="text-cs-text-muted">{entry.total} runs</span>
								</div>
								<div class="flex h-3 overflow-hidden rounded bg-cs-surface-2">
									<div class="bg-success/60 transition-all" style="width: {barWidth(entry.success, maxTotal)}"></div>
									<div class="bg-cs-error/20 transition-all" style="width: {barWidth(entry.failure, maxTotal)}"></div>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Execution Time Trend -->
			<div>
				<h3 class="mb-3 text-xs font-medium uppercase tracking-wider text-cs-text-muted">Execution Time (last 20)</h3>
				{#if timeTrend.length === 0}
					<p class="text-xs text-cs-text-muted">No timing data</p>
				{:else}
					{@const maxDur = Math.max(...timeTrend.map((t) => t.duration))}
					<div class="flex items-end gap-1" style="height: 120px;">
						{#each timeTrend as t}
							{@const h = maxDur > 0 ? (t.duration / maxDur) * 100 : 0}
							<div
								class="flex-1 rounded-t transition-all {t.status === 'success' ? 'bg-accent/60' : t.status === 'failure' ? 'bg-cs-error/20' : 'bg-warning/60'}"
								style="height: {h}%"
								title="{t.duration.toFixed(1)}s"
							></div>
						{/each}
					</div>
					<div class="mt-1 flex justify-between text-xs text-cs-text-muted">
						<span>oldest</span>
						<span>newest</span>
					</div>
				{/if}
			</div>
		</div>

		<!-- Recent Runs Table -->
		<div class="mt-8">
			<h3 class="mb-3 text-xs font-medium uppercase tracking-wider text-cs-text-muted">Recent Runs</h3>
			<div class="overflow-hidden rounded-lg border border-cs-border">
				<table class="w-full text-xs">
					<thead class="bg-cs-surface-2">
						<tr>
							<th class="px-3 py-2 text-left font-medium text-cs-text-muted">Script</th>
							<th class="px-3 py-2 text-left font-medium text-cs-text-muted">Status</th>
							<th class="px-3 py-2 text-left font-medium text-cs-text-muted">Exit</th>
							<th class="px-3 py-2 text-left font-medium text-cs-text-muted">Started</th>
						</tr>
					</thead>
					<tbody>
						{#each allRuns.slice(0, 20) as run}
							{@const script = $scripts.find((s) => s.id === run.script_id)}
							<tr class="border-t border-cs-border hover:bg-bg-hover">
								<td class="px-3 py-2 font-mono">{script?.name ?? '—'}</td>
								<td class="px-3 py-2">
									<span class={run.status === 'success' ? 'text-success' : run.status === 'failure' ? 'text-cs-error' : 'text-cs-warning'}>
										● {run.status}
									</span>
								</td>
								<td class="px-3 py-2 text-cs-text-muted">{run.exit_code ?? '—'}</td>
								<td class="px-3 py-2 text-cs-text-muted">{run.start_time ?? '—'}</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	{/if}
</div>
