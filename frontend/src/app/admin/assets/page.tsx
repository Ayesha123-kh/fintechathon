"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import useSWR from "swr";
import { Badge, Chips, PageHeader, SearchBox, Stat, TableWrap, td, th } from "@/components/admin";
import { Card, Spinner } from "@/components/ui";
import { fetcher } from "@/lib/api";

type Asset = {
  symbol: string; asset_class: string; cluster: string; cluster_slug: string; active: boolean; followers: number;
  signals_7d: number; last_signal: string | null; last_signal_at: string | null; last_price: number | null;
};
type Assets = { total: number; by_asset_class: Record<string, number>; assets: Asset[] };

const CLASS_LABEL: Record<string, string> = {
  psx: "PSX", crypto: "Crypto", gold_silver: "Gold & silver", foreign_stocks: "Global stocks", pk_real_estate: "Real estate",
};
const SIGNAL_TONE: Record<string, "good" | "soft" | "bad" | "neutral"> = { buy: "good", alert: "bad", sell: "bad", watch: "soft", hold: "neutral" };

export default function AssetsPage() {
  const { data } = useSWR<Assets>("/admin/assets", fetcher, { refreshInterval: 60_000 });
  const [q, setQ] = useState("");
  const [cls, setCls] = useState("all");

  const shown = useMemo(() => (data?.assets ?? []).filter((a) =>
    (cls === "all" || a.asset_class === cls) &&
    (!q || `${a.symbol} ${a.cluster}`.toLowerCase().includes(q.toLowerCase()))), [data, q, cls]);

  if (!data) return <Spinner />;
  const followed = data.assets.filter((a) => a.followers > 0).length;
  return (
    <div className="space-y-5">
      <PageHeader title="Tracked assets" subtitle="Every symbol the watcher agents follow, with who follows it and its latest signal." />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Tracked assets" value={data.total} hint={`${Object.keys(data.by_asset_class).length} asset classes`} />
        <Stat label="Followed by users" value={followed} />
        <Stat label="Signals in 7 days" value={data.assets.reduce((n, a) => n + a.signals_7d, 0)} />
        <Stat label="Paused clusters" value={new Set(data.assets.filter((a) => !a.active).map((a) => a.cluster_slug)).size} />
      </div>
      <Card className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <SearchBox value={q} onChange={setQ} placeholder="Search symbol or cluster" label="Search assets" />
        </div>
        <Chips label="Asset class" value={cls} onChange={setCls}
          options={[{ id: "all", label: "All", count: data.total }, ...Object.entries(data.by_asset_class).map(([id, n]) => ({ id, label: CLASS_LABEL[id] ?? id, count: n }))]} />
        <TableWrap min={820}>
          <thead><tr>
            <th className={th}>Symbol</th><th className={th}>Asset class</th><th className={th}>Cluster</th><th className={th}>Followers</th>
            <th className={th}>Signals (7d)</th><th className={th}>Latest signal</th><th className={th}>Last price</th>
          </tr></thead>
          <tbody className="divide-y divide-line">
            {shown.map((a) => (
              <tr key={`${a.cluster_slug}:${a.symbol}`} className={a.active ? "" : "opacity-50"}>
                <td className={`${td} font-semibold`}>{a.symbol}</td>
                <td className={td}>{CLASS_LABEL[a.asset_class] ?? a.asset_class}</td>
                <td className={td}>{a.cluster}{!a.active && <span className="ml-2 text-xs text-muted">paused</span>}</td>
                <td className={`${td} tabular`}>{a.followers}</td>
                <td className={`${td} tabular`}>{a.signals_7d}</td>
                <td className={td}>
                  {a.last_signal ? (
                    <>
                      <Badge tone={SIGNAL_TONE[a.last_signal] ?? "neutral"}>{a.last_signal}</Badge>
                      {a.last_signal_at && <span className="ml-2 text-xs text-muted">{new Date(a.last_signal_at).toLocaleDateString()}</span>}
                    </>
                  ) : <span className="text-muted">none yet</span>}
                </td>
                <td className={`${td} tabular`}>{a.last_price !== null ? a.last_price.toLocaleString("en-PK", { maximumFractionDigits: 2 }) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </TableWrap>
        <p className="text-xs text-muted">
          Showing {shown.length} of {data.total}. Edit the symbols in each cluster, or add one, on the{" "}
          <Link href="/admin/watchlists" className="underline">Watchlists</Link> page.
        </p>
      </Card>
    </div>
  );
}
