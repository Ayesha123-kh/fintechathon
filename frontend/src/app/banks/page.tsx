"use client";

import { ArrowDownLeft, ArrowUpRight, CreditCard, Landmark } from "lucide-react";
import Link from "next/link";
import useSWR from "swr";
import { AppShell } from "@/components/AppShell";
import { SplitDonut, SplitLegend } from "@/components/charts";
import { Card, Empty, Spinner } from "@/components/ui";
import { fetcher, rs } from "@/lib/api";

type CardRow = { id: string; label: string; network: string; tier: string | null; type: string; last4: string | null; bank?: string };
type Account = {
  account_id: string; bank: string; bank_short: string; nickname: string; account_type: string; last4: string | null;
  balance: string; savings: string; expendable: string; cards: CardRow[];
  transactions: { id: string; occurred_at: string; amount: string; direction: string; merchant: string; category: string }[];
};
type Banks = { total_balance: string; total_savings: string; expendable: string; accounts: Account[]; other_cards: CardRow[] };

export default function BanksPage() {
  const { data, mutate } = useSWR<Banks>("/banks", fetcher);
  return (
    <AppShell onChatActivity={() => mutate()}>
      <div className="mb-5">
        <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Banks & cards</h1>
        <p className="text-sm text-muted">Add or change accounts and cards by telling your assistant.</p>
      </div>
      {!data ? <Spinner /> : data.accounts.length === 0 ? (
        <Card>
          <Empty icon={<Landmark className="size-6" />} title="No bank accounts yet"
            body="Tell your assistant which banks and wallets you use, e.g. “I have Meezan and Easypaisa”."
            action={<Link href="?chat=1" className="mt-2 text-sm font-semibold text-forest dark:text-primary">Open chat</Link>} />
        </Card>
      ) : (
        <div className="space-y-5">
          <Card className="flex flex-wrap items-center gap-x-8 gap-y-3">
            <div><p className="text-sm text-muted">Total</p><p className="tabular text-2xl font-bold">{rs(data.total_balance)}</p></div>
            <div><p className="text-sm text-muted">Savings</p><p className="tabular text-lg font-semibold">{rs(data.total_savings)}</p></div>
            <div><p className="text-sm text-muted">Spendable</p><p className="tabular text-lg font-semibold">{rs(data.expendable)}</p></div>
            <div className="ml-auto"><SplitLegend /></div>
          </Card>
          <div className="grid gap-5 md:grid-cols-2">
            {data.accounts.map((a) => (
              <Card key={a.account_id} id={a.account_id} className="scroll-mt-24">
                <div className="flex items-start gap-3">
                  <span className="grid size-11 place-items-center rounded-2xl bg-forest text-forest-ink"><Landmark className="size-5" aria-hidden /></span>
                  <div className="flex-1">
                    <p className="font-semibold">{a.bank}</p>
                    <p className="text-xs capitalize text-muted">{a.account_type} account{a.last4 && ` ••${a.last4}`}</p>
                  </div>
                  <p className="tabular text-lg font-bold">{rs(a.balance)}</p>
                </div>
                <div className="mt-4 flex items-center justify-between gap-4">
                  <dl className="tabular space-y-2 text-sm">
                    <div>
                      <dt className="flex items-center gap-1.5 text-xs text-muted"><span className="size-2.5 rounded-full bg-chart-save" />Savings</dt>
                      <dd className="font-semibold">{rs(a.savings)}</dd>
                    </div>
                    <div>
                      <dt className="flex items-center gap-1.5 text-xs text-muted"><span className="size-2.5 rounded-full bg-chart-spend ring-1 ring-forest/30" />Spendable</dt>
                      <dd className="font-semibold">{rs(a.expendable)}</dd>
                    </div>
                  </dl>
                  <SplitDonut savings={Number(a.savings)} expendable={Number(a.expendable)} label={a.bank} size={112} thickness={14} />
                </div>
                {a.cards.length > 0 && (
                  <div className="mt-4 space-y-2">
                    {a.cards.map((c) => <CardChip key={c.id} c={c} />)}
                  </div>
                )}
                <h3 className="mt-5 mb-1 text-sm font-semibold text-ink-2">Recent transactions</h3>
                {a.transactions.length === 0 ? <p className="py-2 text-sm text-muted">None yet.</p> : (
                  <ul className="divide-y divide-line">
                    {a.transactions.map((t) => (
                      <li key={t.id} className="flex items-center gap-3 py-2">
                        {t.direction === "credit" ? <ArrowDownLeft className="size-4 text-forest dark:text-primary" aria-label="Money in" /> : <ArrowUpRight className="size-4 text-muted" aria-label="Money out" />}
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm">{t.merchant || (t.direction === "credit" ? "Money in" : "Payment")}</p>
                          <p className="text-[11px] capitalize text-muted">{t.category} · {new Date(t.occurred_at).toLocaleDateString("en-PK", { day: "numeric", month: "short" })}</p>
                        </div>
                        <p className="tabular text-sm font-semibold">{t.direction === "credit" ? "+" : "−"}{rs(t.amount)}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </Card>
            ))}
          </div>
          {data.other_cards.length > 0 && (
            <Card>
              <h2 className="mb-3 font-bold">Other cards</h2>
              <div className="space-y-2">{data.other_cards.map((c) => <CardChip key={c.id} c={c} />)}</div>
            </Card>
          )}
        </div>
      )}
    </AppShell>
  );
}

function CardChip({ c }: { c: CardRow }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl bg-surface-2 px-3.5 py-2.5">
      <CreditCard className="size-5 text-forest dark:text-primary" aria-hidden />
      <p className="flex-1 text-sm font-medium">{c.label}</p>
      {c.last4 && <span className="tabular text-xs text-muted">••{c.last4}</span>}
    </div>
  );
}
