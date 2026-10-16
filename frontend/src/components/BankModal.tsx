"use client";

import { ArrowDownLeft, ArrowUpRight, CreditCard, Landmark, X } from "lucide-react";
import { useEffect, useRef } from "react";
import useSWR from "swr";
import { fetcher, rs } from "@/lib/api";
import { SplitDonut } from "./charts";
import { Spinner } from "./ui";

type CardRow = { id: string; label: string; network: string; tier: string | null; type: string };
type Account = {
  account_id: string; bank: string; bank_short: string; nickname: string; account_type: string;
  balance: string; savings: string; expendable: string; cards: CardRow[];
  transactions: { id: string; occurred_at: string; amount: string; direction: string; merchant: string; category: string }[];
};
type Banks = { accounts: Account[] };

/** Bank details for one account, shown over the dashboard. */
export function BankModal({ accountId, onClose }: { accountId: string; onClose: () => void }) {
  const { data } = useSWR<Banks>("/banks", fetcher);
  const closeRef = useRef<HTMLButtonElement>(null);
  const account = data?.accounts.find((a) => a.account_id === accountId);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    closeRef.current?.focus();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = overflow;
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center md:items-center" role="dialog" aria-modal="true"
      aria-label={account ? `${account.bank} details` : "Bank details"}>
      <div className="absolute inset-0 bg-ink/40" onClick={onClose} />
      <section className="safe-bottom relative flex max-h-[90dvh] w-full flex-col overflow-hidden rounded-t-[1.75rem] border-2 border-forest bg-surface p-5 md:max-w-lg md:rounded-[1.75rem]">
        <button ref={closeRef} onClick={onClose} aria-label="Close"
          className="absolute top-4 right-4 grid size-9 place-items-center rounded-full hover:bg-hover">
          <X className="size-5" />
        </button>
        {!data ? (
          <div className="grid h-40 place-items-center"><Spinner /></div>
        ) : !account ? (
          <p className="py-8 text-center text-sm text-muted">This account no longer exists.</p>
        ) : (
          <>
            <div className="flex items-start gap-3 pr-10">
              <span className="grid size-11 shrink-0 place-items-center rounded-2xl bg-forest text-forest-ink"><Landmark className="size-5" aria-hidden /></span>
              <div className="min-w-0 flex-1">
                <p className="font-semibold">{account.bank}</p>
                <p className="text-xs capitalize text-muted">{account.account_type} account</p>
              </div>
            </div>
            <div className="mt-4 flex items-center justify-between gap-4">
              <dl className="tabular space-y-2 text-sm">
                <div><dt className="text-xs text-muted">Balance</dt><dd className="text-xl font-bold">{rs(account.balance)}</dd></div>
                <div>
                  <dt className="flex items-center gap-1.5 text-xs text-muted"><span className="size-2.5 rounded-full bg-chart-save" />Savings</dt>
                  <dd className="font-semibold">{rs(account.savings)}</dd>
                </div>
                <div>
                  <dt className="flex items-center gap-1.5 text-xs text-muted"><span className="size-2.5 rounded-full bg-chart-spend ring-1 ring-forest/30" />Spendable</dt>
                  <dd className="font-semibold">{rs(account.expendable)}</dd>
                </div>
              </dl>
              <SplitDonut savings={Number(account.savings)} expendable={Number(account.expendable)} label={account.bank} size={120} thickness={14} />
            </div>
            {account.cards.length > 0 && (
              <div className="mt-4 space-y-2">
                {account.cards.map((c) => (
                  <div key={c.id} className="flex items-center gap-3 rounded-2xl border-2 border-primary bg-surface-2 px-3.5 py-2.5">
                    <CreditCard className="size-5 text-forest dark:text-primary" aria-hidden />
                    <p className="flex-1 text-sm font-medium">{c.label}</p>
                  </div>
                ))}
              </div>
            )}
            <h3 className="mt-5 mb-1 text-sm font-semibold text-ink-2">Recent transactions</h3>
            {account.transactions.length === 0 ? <p className="py-2 text-sm text-muted">None yet.</p> : (
              <ul className="-mr-2 min-h-0 flex-1 divide-y divide-line overflow-y-auto overscroll-contain pr-2">
                {account.transactions.map((t) => (
                  <li key={t.id} className="flex items-center gap-3 py-2">
                    {t.direction === "credit" ? <ArrowDownLeft className="size-4 text-forest dark:text-primary" aria-label="Money in" /> : <ArrowUpRight className="size-4 text-muted" aria-label="Money out" />}
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm">{t.merchant || (t.direction === "credit" ? "Money in" : "Payment")}</p>
                      <p className="text-[11px] capitalize text-muted">{t.category} · {new Date(t.occurred_at).toLocaleDateString("en-PK", { day: "numeric", month: "short" })}</p>
                    </div>
                    <p className="tabular text-sm font-semibold whitespace-nowrap">{t.direction === "credit" ? "+" : "−"}{rs(t.amount)}</p>
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-3 text-xs text-muted">To change this account or its cards, tell your assistant in the chat.</p>
          </>
        )}
      </section>
    </div>
  );
}
