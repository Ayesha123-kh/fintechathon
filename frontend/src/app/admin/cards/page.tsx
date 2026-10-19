"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { Badge, Chips, PageHeader, SearchBox, Stat, TableWrap, td, th } from "@/components/admin";
import { Card, Spinner } from "@/components/ui";
import { fetcher } from "@/lib/api";

type CardRow = {
  id: string; name: string; bank: string; bank_short: string; network: string | null; tier: string | null;
  card_type: string; islamic: boolean; confidence: string; source_url: string | null; verified_on: string | null;
  held_by_users: number;
};
type Catalog = { total: number; by_confidence: Record<string, number>; cards: CardRow[] };

const CONFIDENCE = {
  official: { tone: "good", hint: "bank page read in full" },
  bank_site: { tone: "neutral", hint: "seen in the bank's own pages or fee schedule" },
  weak: { tone: "bad", hint: "sources disagree or third-party only" },
} as const;

export default function CardsPage() {
  const { data } = useSWR<Catalog>("/admin/cards?limit=1000", fetcher);
  const [q, setQ] = useState("");
  const [type, setType] = useState("all");
  const [conf, setConf] = useState("all");
  const [bank, setBank] = useState("all");

  const banks = useMemo(() => [...new Map((data?.cards ?? []).map((c) => [c.bank_short, c.bank])).entries()].sort((a, b) => a[1].localeCompare(b[1])), [data]);
  const shown = useMemo(() => (data?.cards ?? []).filter((c) =>
    (type === "all" || c.card_type === type) && (conf === "all" || c.confidence === conf) && (bank === "all" || c.bank_short === bank) &&
    (!q || `${c.name} ${c.bank} ${c.network ?? ""} ${c.tier ?? ""}`.toLowerCase().includes(q.toLowerCase()))), [data, q, type, conf, bank]);

  if (!data) return <Spinner />;
  const noNetwork = data.cards.filter((c) => !c.network).length;
  return (
    <div className="space-y-5">
      <PageHeader title="Cards" subtitle="The catalog of card products each bank issues, with how sure we are of each one." />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Card products" value={data.total} hint={`${data.cards.filter((c) => c.card_type === "debit").length} debit · ${data.cards.filter((c) => c.card_type === "credit").length} credit`} />
        <Stat label="Official" value={data.by_confidence.official ?? 0} hint={CONFIDENCE.official.hint} />
        <Stat label="Weak" value={data.by_confidence.weak ?? 0} hint={CONFIDENCE.weak.hint} />
        <Stat label="Network not stated" value={noNetwork} hint="the bank's page did not say" />
      </div>
      <Card className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <SearchBox value={q} onChange={setQ} placeholder="Search card, bank, network or tier" label="Search cards" />
          <select value={bank} onChange={(e) => setBank(e.target.value)} aria-label="Bank"
            className="h-10 rounded-2xl border border-line bg-surface-2 px-3 text-sm">
            <option value="all">All banks</option>
            {banks.map(([short, name]) => <option key={short} value={short}>{name}</option>)}
          </select>
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-2">
          <Chips label="Type" value={type} onChange={setType}
            options={[{ id: "all", label: "All types" }, { id: "debit", label: "Debit" }, { id: "credit", label: "Credit" }]} />
          <Chips label="Confidence" value={conf} onChange={setConf}
            options={[{ id: "all", label: "Any confidence" }, ...Object.keys(CONFIDENCE).map((id) => ({ id, label: id.replace("_", " "), count: data.by_confidence[id] ?? 0 }))]} />
        </div>
        <TableWrap min={900}>
          <thead><tr>
            <th className={th}>Card</th><th className={th}>Bank</th><th className={th}>Network</th><th className={th}>Tier</th>
            <th className={th}>Type</th><th className={th}>Confidence</th><th className={th}>Held by users</th><th className={th}>Source</th>
          </tr></thead>
          <tbody className="divide-y divide-line">
            {shown.map((c) => (
              <tr key={c.id}>
                <td className={td}>
                  <p className="font-semibold">{c.name}</p>
                  {c.islamic && <span className="text-xs text-muted">Islamic</span>}
                </td>
                <td className={td}>{c.bank_short}</td>
                <td className={td}>{c.network ?? <span className="text-muted">not stated</span>}</td>
                <td className={td}>{c.tier ?? "—"}</td>
                <td className={td}>{c.card_type}</td>
                <td className={td}>
                  <Badge tone={CONFIDENCE[c.confidence as keyof typeof CONFIDENCE]?.tone ?? "neutral"}>{c.confidence.replace("_", " ")}</Badge>
                </td>
                <td className={`${td} tabular`}>{c.held_by_users}</td>
                <td className={`${td} text-xs`}>
                  {c.source_url ? <a href={c.source_url} target="_blank" rel="noopener noreferrer" className="underline">source</a> : "—"}
                  {c.verified_on && <span className="text-muted"> · {c.verified_on}</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </TableWrap>
        <p className="text-xs text-muted">Showing {shown.length} of {data.total}</p>
      </Card>
    </div>
  );
}
