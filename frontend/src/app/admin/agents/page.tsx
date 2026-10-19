"use client";

import clsx from "clsx";
import { Check, RefreshCw, X } from "lucide-react";
import { useState } from "react";
import useSWR from "swr";
import { Button, Card, Spinner } from "@/components/ui";
import { api, errorText, fetcher } from "@/lib/api";
import { PageHeader } from "@/components/admin";

type Agents = {
  gateway: { ok?: boolean; error?: string; relay_connected?: boolean; last_sync?: string; last_sync_error?: string; bot_count?: number; rooms_watched?: number };
  agents: { name: string; team: string; kind: string; status: string; last_run_at: string | null; soul_hash: string; last_error: string | null }[];
};

function AgentsTab() {
  const { data, mutate } = useSWR<Agents>("/admin/agents", fetcher, { refreshInterval: 30_000 });
  const { data: usage } = useSWR<Record<string, unknown>>("/admin/usage", fetcher);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const sync = async () => {
    setBusy(true);
    setMsg("");
    try {
      const r = await api<{ shared: { applied: boolean; bots: number }; users_updated: number }>("/admin/agents/sync", { method: "POST" });
      setMsg(`Synced ${r.shared.bots} shared agents, ${r.users_updated} user teams updated.`);
      mutate();
    } catch (e) {
      setMsg(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  if (!data) return <Spinner />;
  const g = data.gateway;
  const teams = [...new Set(data.agents.map((a) => a.team))];
  return (
    <div className="space-y-5">
      <Card className="flex flex-wrap items-center gap-x-8 gap-y-3">
        <Status ok={!!g.ok} label="OpenMausBot" />
        <Status ok={!!g.relay_connected} label="Event relay" />
        <div className="text-sm"><p className="text-xs text-muted">Bots</p><p className="font-semibold">{g.bot_count ?? "—"}</p></div>
        <div className="text-sm"><p className="text-xs text-muted">User rooms</p><p className="font-semibold">{g.rooms_watched ?? "—"}</p></div>
        <div className="text-sm"><p className="text-xs text-muted">Last sync</p><p className="font-semibold">{g.last_sync ? new Date(g.last_sync).toLocaleString() : "—"}</p></div>
        <Button className="ml-auto" variant="forest" onClick={sync} loading={busy}><RefreshCw className="size-4" aria-hidden /> Re-sync agents</Button>
        {(g.error || g.last_sync_error) && <p className="w-full text-sm text-danger">{g.error || g.last_sync_error}</p>}
        {msg && <p className="w-full text-sm">{msg}</p>}
      </Card>
      {teams.map((team) => (
        <Card key={team}>
          <h2 className="mb-3 font-bold capitalize">{team.replace("_", " ")}</h2>
          <ul className="divide-y divide-line text-sm">
            {data.agents.filter((a) => a.team === team).map((a) => (
              <li key={a.name} className="flex flex-wrap items-center gap-3 py-2.5">
                <span className={clsx("size-2.5 rounded-full", a.status === "ok" ? "bg-chart-save" : "bg-danger")} aria-label={a.status} />
                <span className="flex-1 font-medium">{a.name}</span>
                <span className="rounded-full bg-surface-2 px-2 py-0.5 text-xs">{a.kind}</span>
                <span className="text-xs text-muted">last run {a.last_run_at ? new Date(a.last_run_at).toLocaleString() : "never"}</span>
                {a.last_error && <p className="w-full text-xs text-danger">{a.last_error}</p>}
              </li>
            ))}
          </ul>
        </Card>
      ))}
      <Card>
        <h2 className="mb-2 font-bold">LLM usage</h2>
        <pre className="max-h-72 overflow-auto rounded-2xl bg-surface-2 p-3 text-xs">{usage ? JSON.stringify(usage, null, 2) : "Loading…"}</pre>
      </Card>
    </div>
  );
}

function Status({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      {ok ? <Check className="size-4 text-forest dark:text-primary" aria-hidden /> : <X className="size-4 text-danger" aria-hidden />}
      <span className="font-semibold">{label}</span><span className="text-muted">{ok ? "online" : "offline"}</span>
    </div>
  );
}

export default function Page() {
  return (
    <div className="space-y-5">
      <PageHeader title="Agents" subtitle="The shared desks and the gateway that runs them." />
      <AgentsTab />
    </div>
  );
}
