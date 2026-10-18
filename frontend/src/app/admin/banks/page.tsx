"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import { Badge, Chips, PageHeader, SearchBox, Stat, TableWrap, td, th } from "@/components/admin";
import { Card, Spinner } from "@/components/ui";
import { fetcher } from "@/lib/api";

type Bank = {
  id: string; name: string; short_name: string; kind: string; website: string | null; email_domains: string[];
  aliases: string[]; debit_products: number; credit_products: number; user_accounts: number; user_cards: number;
  active_deals: number;
};

const KINDS = { bank: "Bank", islamic_bank: "Islamic bank", wallet: "Wallet" } as Record<string, string>;

export default function BanksPage() {
  const { data } = useSWR<Bank[]>("/admin/banks", fetcher);
  const [q, setQ] = useState("");
  const [kind, setKind] = useState("all");

  const shown = useMemo(() => (data ?? []).filter((b) =>
    (kind === "all" || b.kind === kind) &&
    (!q || [b.name, b.short_name, ...b.aliases].some((x) => x.toLowerCase().includes(q.toLowerCase())))), [data, q, kind]);

  if (!data) return <Spinner />;
  const count = (k: string) => data.filter((b) => b.kind === k).length;
  return (
    <div className="space-y-5">
      <PageHeader title="Banks" subtitle="Every bank and wallet the app supports. Loaded from the reference data at startup." />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Institutions" value={data.length} hint={`${count("bank")} banks · ${count("islamic_bank")} Islamic · ${count("wallet")} wallets`} />
        <Stat label="Card products" value={data.reduce((n, b) => n + b.debit_products + b.credit_products, 0)} />
        <Stat label="User accounts" value={data.reduce((n, b) => n + b.user_accounts, 0)} />
        <Stat label="Active deals tied to a bank" value={data.reduce((n, b) => n + b.active_deals, 0)} />
      </div>
      <Card className="space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <SearchBox value={q} onChange={setQ} placeholder="Search by name or alias" label="Search banks" />
          <Chips label="Kind" value={kind} onChange={setKind}
            options={[{ id: "all", label: "All", count: data.length }, ...Object.entries(KINDS).map(([id, label]) => ({ id, label, count: count(id) }))]} />
        </div>
        <TableWrap min={760}>
          <thead><tr>
            <th className={th}>Bank</th><th className={th}>Kind</th><th className={th}>Debit</th><th className={th}>Credit</th>
            <th className={th}>User accounts</th><th className={th}>User cards</th><th className={th}>Active deals</th>
            <th className={th}>Alert email domains</th>
          </tr></thead>
          <tbody className="divide-y divide-line">
            {shown.map((b) => (
              <tr key={b.id}>
                <td className={td}>
                  <p className="font-semibold">{b.website ? <a href={b.website} target="_blank" rel="noopener noreferrer" className="hover:underline">{b.name}</a> : b.name}</p>
                  <p className="text-xs text-muted">{b.short_name}</p>
                </td>
                <td className={td}><Badge tone={b.kind === "wallet" ? "soft" : "neutral"}>{KINDS[b.kind] ?? b.kind}</Badge></td>
                <td className={`${td} tabular`}>{b.debit_products}</td>
                <td className={`${td} tabular`}>{b.credit_products}</td>
                <td className={`${td} tabular`}>{b.user_accounts}</td>
                <td className={`${td} tabular`}>{b.user_cards}</td>
                <td className={`${td} tabular`}>{b.active_deals}</td>
                <td className={`${td} text-xs text-muted`}>{b.email_domains.join(", ") || "—"}</td>
              </tr>
            ))}
          </tbody>
        </TableWrap>
        {shown.length === 0 && <p className="text-sm text-muted">No bank matches.</p>}
      </Card>
    </div>
  );
}
