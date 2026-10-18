"use client";

import { useState } from "react";
import useSWR from "swr";
import { Button, Card, Input, Spinner } from "@/components/ui";
import { api, fetcher } from "@/lib/api";
import { PageHeader } from "@/components/admin";

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

export default function Page() {
  return (
    <div className="space-y-5">
      <PageHeader title="Watchlists" subtitle="Watch clusters: each one has its own watcher agent." />
      <WatchTab />
    </div>
  );
}
