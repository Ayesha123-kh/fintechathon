"use client";

import { useState } from "react";
import useSWR from "swr";
import { Badge, Chips, PageHeader, SearchBox, Stat, TableWrap, td, th } from "@/components/admin";
import { Button, Card, Spinner } from "@/components/ui";
import { fetcher } from "@/lib/api";

type Company = {
  id: string; name: string; category: string; subcategory: string | null; website: string | null; sources: string[];
  status: string; seen_in_transactions: number; last_crawled_at: string | null; live_deals: number;
};
type Companies = { total: number; by_status: Record<string, number>; companies: Company[] };

const PAGE = 50;
const STATUS_TONE: Record<string, "good" | "neutral" | "soft" | "bad"> = {
  ready: "good", pending: "neutral", discovering: "soft", failed: "bad", screening: "soft", personal: "bad",
};
const STATUS_HINT: Record<string, string> = {
  pending: "a business waiting for the Source Scout",
  discovering: "the Source Scout is looking for its sources",
  ready: "sources found, the Crawler visits it",
  failed: "sources could not be found",
  screening: "waiting for the self-hosted model to judge it",
  personal: "judged a private payee: never shown to the deal bots",
};

export default function CompaniesPage() {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("all");
  const [offset, setOffset] = useState(0);
  const query = `/admin/companies?limit=${PAGE}&offset=${offset}&q=${encodeURIComponent(q)}${status === "all" ? "" : `&status=${status}`}`;
  const { data } = useSWR<Companies>(query, fetcher, { keepPreviousData: true });

  if (!data) return <Spinner />;
  const overall = Object.values(data.by_status).reduce((a, b) => a + b, 0);
  const ago = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString() : "never");
  return (
    <div className="space-y-5">
      <PageHeader title="Companies" subtitle="The merchant directory the deal bots work from. New ones come from users' spending, after screening." />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Companies" value={overall} />
        <Stat label="Ready to crawl" value={data.by_status.ready ?? 0} hint={STATUS_HINT.ready} />
        <Stat label="Waiting for sources" value={(data.by_status.pending ?? 0) + (data.by_status.discovering ?? 0)} hint={STATUS_HINT.pending} />
        <Stat label="Held back" value={(data.by_status.screening ?? 0) + (data.by_status.personal ?? 0)} hint="screening or private payees" />
      </div>
      <Card className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <SearchBox value={q} onChange={(v) => { setQ(v); setOffset(0); }} placeholder="Search name or type of business" label="Search companies" />
        </div>
        <Chips label="Status" value={status} onChange={(s) => { setStatus(s); setOffset(0); }}
          options={[{ id: "all", label: "All", count: overall }, ...Object.entries(data.by_status).map(([id, n]) => ({ id, label: id, count: n }))]} />
        <TableWrap min={860}>
          <thead><tr>
            <th className={th}>Company</th><th className={th}>Category</th><th className={th}>Status</th>
            <th className={th}>Seen in spending</th><th className={th}>Live deals</th><th className={th}>Sources</th><th className={th}>Last crawled</th>
          </tr></thead>
          <tbody className="divide-y divide-line">
            {data.companies.map((c) => (
              <tr key={c.id}>
                <td className={td}>
                  <p className="font-semibold">{c.website ? <a href={c.website} target="_blank" rel="noopener noreferrer" className="hover:underline">{c.name}</a> : c.name}</p>
                  {c.subcategory && <p className="text-xs text-muted">{c.subcategory}</p>}
                </td>
                <td className={td}>{c.category}</td>
                <td className={td}><Badge tone={STATUS_TONE[c.status] ?? "neutral"}>{c.status}</Badge></td>
                <td className={`${td} tabular`}>{c.seen_in_transactions}</td>
                <td className={`${td} tabular`}>{c.live_deals}</td>
                <td className={`${td} text-xs text-muted`}>{c.sources.length ? c.sources.join(", ") : "—"}</td>
                <td className={`${td} text-xs text-muted`}>{ago(c.last_crawled_at)}</td>
              </tr>
            ))}
          </tbody>
        </TableWrap>
        {data.companies.length === 0 && <p className="text-sm text-muted">No companies match.</p>}
        <div className="flex items-center justify-between text-xs text-muted">
          <span>{data.total === 0 ? "0" : `${offset + 1}–${Math.min(offset + PAGE, data.total)}`} of {data.total}</span>
          <span className="space-x-2">
            <Button size="sm" variant="outline" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>Previous</Button>
            <Button size="sm" variant="outline" disabled={offset + PAGE >= data.total} onClick={() => setOffset(offset + PAGE)}>Next</Button>
          </span>
        </div>
      </Card>
    </div>
  );
}
