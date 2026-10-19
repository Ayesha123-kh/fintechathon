"use client";

import clsx from "clsx";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import useSWR from "swr";
import { Button, Card, Input, Spinner } from "@/components/ui";
import { api, fetcher } from "@/lib/api";
import { PageHeader } from "@/components/admin";

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

export default function Page() {
  return (
    <div className="space-y-5">
      <PageHeader title="Deals" subtitle="Review, approve or reject the deals the bots found." />
      <DealsTab />
    </div>
  );
}
