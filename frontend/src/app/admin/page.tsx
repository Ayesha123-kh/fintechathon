"use client";

import clsx from "clsx";
import { Bot, Check, ListChecks, RefreshCw, Search, Shield, Tag, Trash2, Users, Wallet, X } from "lucide-react";
import { useState } from "react";
import useSWR from "swr";
import { AppShell } from "@/components/AppShell";
import { Button, Card, Input, Spinner } from "@/components/ui";
import { api, errorText, fetcher, rs } from "@/lib/api";
import { useSession } from "@/lib/session";

const TABS = [
  { id: "overview", label: "Overview", icon: Shield },
  { id: "users", label: "Users", icon: Users },
  { id: "agents", label: "Agents", icon: Bot },
  { id: "deals", label: "Deals", icon: Tag },
  { id: "watch", label: "Watchlists", icon: ListChecks },
  { id: "plans", label: "Plans", icon: Wallet },
] as const;
type TabId = (typeof TABS)[number]["id"];

export default function AdminPage() {
  const [tab, setTab] = useState<TabId>("overview");
  const { user } = useSession();
  return (
    <AppShell>
      {user?.role !== "admin" ? <Spinner /> : (
        <div className="space-y-5">
          <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Admin</h1>
          <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1" role="tablist">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id)}
                className={clsx("inline-flex shrink-0 items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold",
                  tab === id ? "bg-forest text-forest-ink" : "bg-surface text-ink-2")}>
                <Icon className="size-4" aria-hidden /> {label}
              </button>
            ))}
          </div>
          {tab === "overview" && <Overview />}
          {tab === "users" && <UsersTab />}
          {tab === "agents" && <AgentsTab />}
          {tab === "deals" && <DealsTab />}
          {tab === "watch" && <WatchTab />}
          {tab === "plans" && <PlansTab />}
        </div>
      )}
    </AppShell>
  );
}

function Overview() {
  const { data } = useSWR<Record<string, number>>("/admin/stats", fetcher, { refreshInterval: 30_000 });
  const { data: audit } = useSWR<{ action: string; target: string; actor: string; at: string }[]>("/admin/audit", fetcher);
  if (!data) return <Spinner />;
  const tiles: [string, string][] = [
    ["users", "Users"], ["active_24h", "Active (24h)"], ["onboarded", "Onboarded"], ["rooms_ready", "Assistants ready"],
    ["rooms_error", "Assistant errors"], ["email_connections", "Email connections"], ["transactions_24h", "Transactions (24h)"],
    ["deals_active", "Active deals"], ["deals_review", "Deals to review"], ["merchants", "Merchants"],
    ["signals_24h", "Signals (24h)"], ["research_24h", "Research notes (24h)"], ["coverage_open", "Coverage requests"],
  ];
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {tiles.map(([k, label]) => (
          <Card key={k} className="p-4">
            <p className="text-xs text-muted">{label}</p>
            <p className={clsx("tabular mt-1 text-2xl font-bold", k === "rooms_error" && data[k] > 0 && "text-danger")}>{data[k] ?? 0}</p>
          </Card>
        ))}
      </div>
      <Card>
        <h2 className="mb-3 font-bold">Recent admin activity</h2>
        {!audit?.length ? <p className="text-sm text-muted">Nothing yet.</p> : (
          <ul className="divide-y divide-line text-sm">
            {audit.slice(0, 15).map((a, i) => (
              <li key={i} className="flex flex-wrap justify-between gap-2 py-2">
                <span><span className="font-semibold">{a.action}</span> <span className="text-muted">{a.target}</span></span>
                <span className="text-xs text-muted">{a.actor} · {new Date(a.at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

type AdminUser = { id: string; email: string; full_name: string; role: string; is_active: boolean; onboarding_completed: boolean;
  created_at: string; last_login_at: string | null; assistant: string };

function UsersTab() {
  const [q, setQ] = useState("");
  const { data, mutate } = useSWR<{ total: number; users: AdminUser[] }>(`/admin/users?q=${encodeURIComponent(q)}`, fetcher);
  const [error, setError] = useState("");
  const patch = async (id: string, body: object) => {
    setError("");
    try {
      await api(`/admin/users/${id}`, { method: "PATCH", json: body });
      mutate();
    } catch (e) {
      setError(errorText(e));
    }
  };
  const remove = async (u: AdminUser) => {
    if (!window.confirm(`Permanently delete ${u.email}? All their data and their assistant team will be removed. This cannot be undone.`)) return;
    setError("");
    try {
      await api(`/admin/users/${u.id}`, { method: "DELETE" });
      mutate();
    } catch (e) {
      setError(errorText(e));
    }
  };
  return (
    <Card className="space-y-4">
      <div className="relative">
        <Search className="pointer-events-none absolute top-1/2 left-4 size-4 -translate-y-1/2 text-muted" aria-hidden />
        <Input placeholder="Search by name or email" value={q} onChange={(e) => setQ(e.target.value)} className="pl-10" aria-label="Search users" />
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      {!data ? <Spinner /> : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="text-xs text-muted"><tr>
              <th className="py-2 font-medium">User</th><th className="font-medium">Role</th><th className="font-medium">Onboarded</th>
              <th className="font-medium">Assistant</th><th className="font-medium">Last login</th><th className="font-medium" />
            </tr></thead>
            <tbody className="divide-y divide-line">
              {data.users.map((u) => (
                <tr key={u.id} className={clsx(!u.is_active && "opacity-50")}>
                  <td className="py-2.5"><p className="font-semibold">{u.full_name || "—"}</p><p className="text-xs text-muted">{u.email}</p></td>
                  <td><span className={clsx("rounded-full px-2.5 py-1 text-xs font-semibold", u.role === "admin" ? "bg-forest text-forest-ink" : "bg-surface-2")}>{u.role}</span></td>
                  <td>{u.onboarding_completed ? "Yes" : "No"}</td>
                  <td className={clsx(u.assistant === "error" && "text-danger")}>{u.assistant}</td>
                  <td className="text-xs text-muted">{u.last_login_at ? new Date(u.last_login_at).toLocaleDateString() : "—"}</td>
                  <td className="space-x-1 text-right whitespace-nowrap">
                    <Button size="sm" variant="outline" onClick={() => patch(u.id, { role: u.role === "admin" ? "user" : "admin" })}>
                      {u.role === "admin" ? "Make user" : "Make admin"}
                    </Button>
                    <Button size="sm" variant={u.is_active ? "ghost" : "outline"} onClick={() => patch(u.id, { is_active: !u.is_active })}>
                      {u.is_active ? "Disable" : "Enable"}
                    </Button>
                    <button aria-label={`Delete ${u.email}`} onClick={() => remove(u)}
                      className="inline-grid size-9 place-items-center rounded-full align-middle text-danger hover:bg-hover">
                      <Trash2 className="size-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-3 text-xs text-muted">{data.total} users</p>
        </div>
      )}
    </Card>
  );
}

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

type Deal = { id: string; merchant: string; title: string; category: string; deal_type: string | null; discount_type: string;
  discount_value: string | null; requires_card: boolean; card_network: string | null; card_tier: string | null;
  valid_until: string | null; status: string; verified: boolean; confidence: string | null; source_url: string | null };

function DealsTab() {
  const [status, setStatus] = useState("pending_review");
  const [q, setQ] = useState("");
  const { data, mutate } = useSWR<Deal[]>(`/admin/deals?status=${status}&q=${encodeURIComponent(q)}`, fetcher);
  const act = async (id: string, body: object | null) => {
    if (body) await api(`/admin/deals/${id}`, { method: "PATCH", json: body });
    else await api(`/admin/deals/${id}`, { method: "DELETE" });
    mutate();
  };
  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {["pending_review", "active", "expired", "rejected"].map((s) => (
          <button key={s} onClick={() => setStatus(s)}
            className={clsx("rounded-full px-3 py-1.5 text-xs font-semibold", status === s ? "bg-forest text-forest-ink" : "bg-surface-2")}>
            {s.replace("_", " ")}
          </button>
        ))}
        <Input placeholder="Search merchant or title" value={q} onChange={(e) => setQ(e.target.value)} className="h-9 min-w-48 flex-1" aria-label="Search deals" />
      </div>
      {!data ? <Spinner /> : data.length === 0 ? <p className="text-sm text-muted">No deals here.</p> : (
        <ul className="space-y-2">
          {data.map((d) => (
            <li key={d.id} className="rounded-2xl border-2 border-forest dark:border-primary bg-surface-2 p-3.5 text-sm">
              <div className="flex flex-wrap items-start gap-2">
                <div className="min-w-0 flex-1">
                  <p className="font-semibold">{d.merchant} · {d.title}</p>
                  <p className="text-xs text-muted">
                    {d.deal_type ?? d.category} · {d.discount_type} {d.discount_value ?? ""}
                    {d.requires_card && ` · card: ${[d.card_network, d.card_tier].filter(Boolean).join(" ") || "bank specific"}`}
                    {d.valid_until && ` · until ${d.valid_until}`} · confidence {d.confidence ?? "—"}
                  </p>
                  {d.source_url && <a href={d.source_url} target="_blank" rel="noopener noreferrer" className="text-xs underline">source</a>}
                </div>
                <div className="flex gap-1">
                  {d.status !== "active" && <Button size="sm" onClick={() => act(d.id, { status: "active", verified: true })}>Approve</Button>}
                  {d.status !== "rejected" && <Button size="sm" variant="outline" onClick={() => act(d.id, { status: "rejected" })}>Reject</Button>}
                  <button aria-label="Delete deal" onClick={() => act(d.id, null)} className="grid size-9 place-items-center rounded-full text-danger hover:bg-hover"><Trash2 className="size-4" /></button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

type Clusters = {
  clusters: { id: string; slug: string; asset_class: string; name: string; symbols: string[]; active: boolean }[];
  coverage_requests: { asset_class: string; symbol: string; requests: number }[];
};

function WatchTab() {
  const { data, mutate } = useSWR<Clusters>("/admin/clusters", fetcher);
  const [edit, setEdit] = useState<Record<string, string>>({});
  const [form, setForm] = useState({ asset_class: "psx", slug: "", name: "", symbols: "" });
  const save = async (id: string) => {
    await api(`/admin/clusters/${id}`, { method: "PATCH", json: { symbols: edit[id].split(",").map((s) => s.trim()) } });
    setEdit((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    mutate();
  };
  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    await api("/admin/clusters", { method: "POST", json: { ...form, symbols: form.symbols.split(",").map((s) => s.trim()).filter(Boolean) } });
    setForm({ asset_class: "psx", slug: "", name: "", symbols: "" });
    mutate();
  };
  if (!data) return <Spinner />;
  return (
    <div className="space-y-5">
      {data.coverage_requests.length > 0 && (
        <Card>
          <h2 className="mb-2 font-bold">Users asked to watch</h2>
          <div className="flex flex-wrap gap-2">
            {data.coverage_requests.map((r) => (
              <span key={r.asset_class + r.symbol} className="rounded-full bg-primary/40 px-3 py-1 text-sm">
                {r.symbol} <span className="text-xs text-muted">({r.asset_class}, {r.requests})</span>
              </span>
            ))}
          </div>
          <p className="mt-2 text-xs text-muted">Analysts assign these to clusters automatically; add a new cluster when none fits.</p>
        </Card>
      )}
      <Card>
        <h2 className="mb-3 font-bold">Watch clusters (one watcher agent each)</h2>
        <ul className="divide-y divide-line text-sm">
          {data.clusters.map((c) => (
            <li key={c.id} className="flex flex-wrap items-center gap-3 py-2.5">
              <div className="min-w-48 flex-1">
                <p className="font-semibold">{c.name}</p>
                <p className="text-xs text-muted">{c.asset_class} · {c.slug}</p>
              </div>
              {edit[c.id] !== undefined ? (
                <>
                  <Input value={edit[c.id]} onChange={(e) => setEdit({ ...edit, [c.id]: e.target.value })} className="h-9 flex-1" aria-label="Symbols" />
                  <Button size="sm" onClick={() => save(c.id)}>Save</Button>
                </>
              ) : (
                <button className="flex-1 text-left text-xs text-ink-2" onClick={() => setEdit({ ...edit, [c.id]: c.symbols.join(", ") })}>
                  {c.symbols.join(", ")}
                </button>
              )}
              <Button size="sm" variant="ghost" onClick={async () => { await api(`/admin/clusters/${c.id}`, { method: "PATCH", json: { active: !c.active } }); mutate(); }}>
                {c.active ? "Pause" : "Resume"}
              </Button>
            </li>
          ))}
        </ul>
      </Card>
      <Card>
        <h2 className="mb-3 font-bold">New cluster</h2>
        <form onSubmit={create} className="grid gap-3 sm:grid-cols-2">
          <label className="block text-sm"><span className="mb-1.5 block font-medium text-ink-2">Asset class</span>
            <select value={form.asset_class} onChange={(e) => setForm({ ...form, asset_class: e.target.value })}
              className="h-12 w-full rounded-2xl border border-line bg-surface-2 px-3">
              {["gold_silver", "psx", "foreign_stocks", "crypto", "pk_real_estate"].map((a) => <option key={a}>{a}</option>)}
            </select>
          </label>
          <Input label="Slug" placeholder="psx-autos" value={form.slug} onChange={(e) => setForm({ ...form, slug: e.target.value })} required />
          <Input label="Name" placeholder="PSX Automobiles" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          <Input label="Symbols (comma separated)" placeholder="INDU, HCAR, PSMC" value={form.symbols} onChange={(e) => setForm({ ...form, symbols: e.target.value })} />
          <Button type="submit" className="sm:col-span-2">Create (watcher is added on next agent sync)</Button>
        </form>
      </Card>
    </div>
  );
}

type Plan = { id: string; code: string; name: string; price_monthly: string; currency: string; features: object; is_active: boolean; subscribers: number };

function PlansTab() {
  const { data } = useSWR<Plan[]>("/admin/plans", fetcher);
  if (!data) return <Spinner />;
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {data.map((p) => (
        <Card key={p.id}>
          <div className="flex items-baseline justify-between">
            <h2 className="text-lg font-bold">{p.name}</h2>
            <p className="tabular font-semibold">{Number(p.price_monthly) ? `${rs(p.price_monthly)}/mo` : "Free"}</p>
          </div>
          <p className="mt-1 text-sm text-muted">{p.subscribers} active subscribers · code {p.code}</p>
          <pre className="mt-3 overflow-auto rounded-2xl bg-surface-2 p-3 text-xs">{JSON.stringify(p.features, null, 2)}</pre>
        </Card>
      ))}
      <Card className="md:col-span-2">
        <p className="text-sm text-muted">
          Payments aren&apos;t live yet. Subscriptions and payments tables already store provider, customer and subscription ids,
          so a gateway (e.g. a Pakistani PSP or Stripe) can be connected later without schema changes.
        </p>
      </Card>
    </div>
  );
}
