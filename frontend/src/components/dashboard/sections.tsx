"use client";

import clsx from "clsx";
import { PiggyBank, Target } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import useSWR from "swr";
import { BankModal } from "@/components/BankModal";
import { CategoryStack, ProgressRing } from "@/components/charts";
import { Card, Empty } from "@/components/ui";
import { fetcher, rs } from "@/lib/api";

/*
  The dashboard's cards, shared by /dashboard (all of them) and the phone pages /goals, /spending, /banks and
  /deals (one each). Every page reads the same /dashboard response, so moving between them needs no new request.
*/

export type Dashboard = {
  total_balance: string; total_savings: string; expendable: string; saved_this_week: string;
  deal_savings_total: string; income_this_month: string; spent_this_month: string;
  banks: { account_id: string; bank: string; bank_short: string; nickname: string; account_type: string;
    balance: string; savings: string; expendable: string }[];
  goals: { id: string; name: string; icon: string; status: string; target: string; saved: string; deadline: string | null;
    progress: number; monthly_needed: string }[];
  spending_by_category: { category: string; name: string; color: string; amount: string }[];
  recent_transactions: { id: string; occurred_at: string; amount: string; direction: string; merchant: string; category: string }[];
  deals_for_you: { id: string; merchant: string; title: string; discount_type: string; discount_value: number | null;
    your_eligible_cards: string[]; valid_until: string | null; source_url: string | null; requires_card: boolean }[];
  email_connected: boolean;
};

/** The dashboard data, refreshed every minute; the same cache backs every page that shows a section. */
export function useDashboard() {
  return useSWR<Dashboard>("/dashboard", fetcher, { refreshInterval: 60_000 });
}

/** "Rs. 420k", "Rs. 1.2M": the short amounts used on goal tiles. */
export const short = (v: number | string) => {
  const n = Number(v);
  const fmt = (x: number) => x.toFixed(1).replace(/\.0$/, "");
  if (Math.abs(n) >= 1_000_000) return `${fmt(n / 1_000_000)}M`;
  if (Math.abs(n) >= 1_000) return `${fmt(n / 1_000)}k`;
  return `${Math.round(n)}`;
};
export const day = (d: string) => new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
export const monthYear = (d: string) => new Date(d).toLocaleDateString("en-GB", { month: "short", year: "numeric" });
export const title = "text-xl font-bold tracking-tight text-ink sm:text-2xl";

type SectionProps = { id?: string; className?: string };

export function SpendingCard({ d, id, className }: { d: Dashboard } & SectionProps) {
  return (
    <Card id={id} data-section={id ? "" : undefined} className={clsx("wide:col-span-5", className)}>
      <h2 className={title}>Spending this month</h2>
      <p className="tabular mt-1 text-[15px] text-muted sm:text-base">
        {Number(d.income_this_month) > 0 ? `${rs(d.spent_this_month)} of ${rs(d.income_this_month)}` : `${rs(d.spent_this_month)} spent so far`}
      </p>
      <div className="mt-6">
        {d.spending_by_category.length === 0
          ? <p className="text-sm text-muted">No spending recorded yet this month.</p>
          : <CategoryStack rows={d.spending_by_category} />}
      </div>
    </Card>
  );
}

/** Banks list; tapping one opens its details over the page. */
export function BanksCard({ d, id, className }: { d: Dashboard } & SectionProps) {
  const [bank, setBank] = useState<string | null>(null);
  return (
    <>
      {bank && <BankModal accountId={bank} onClose={() => setBank(null)} />}
      <Card id={id} data-section={id ? "" : undefined} className={clsx("wide:col-span-4", className)}>
        <h2 className={clsx(title, "mb-5")}>Your banks</h2>
        {d.banks.length === 0 ? (
          <Empty icon={<PiggyBank className="size-6" />} title="No banks added" body="Tell your assistant which banks and wallets you use." />
        ) : (
          <ul className="space-y-1">
            {d.banks.map((b) => (
              <li key={b.account_id}>
                <button type="button" onClick={() => setBank(b.account_id)} aria-label={`${b.bank} details`}
                  className="-mx-2 flex w-[calc(100%+1rem)] items-center gap-3 rounded-2xl p-2 text-left transition hover:bg-hover">
                  <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-badge text-xs font-bold text-forest uppercase dark:text-primary sm:size-14 sm:text-sm">
                    {b.bank_short.slice(0, 4)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-semibold text-ink sm:text-lg">{b.bank}</span>
                    <span className="tabular block text-sm text-muted">{rs(b.savings)} saved</span>
                  </span>
                  <span className="tabular font-bold whitespace-nowrap text-ink sm:text-lg">{rs(b.balance)}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}

export function DealsCard({ d, id, className }: { d: Dashboard } & SectionProps) {
  return (
    <Card id={id} data-section={id ? "" : undefined} className={clsx("bg-deal-bg! wide:col-span-4", className)}>
      <h2 className={clsx(title, "mb-5")}>Deals for your cards</h2>
      {d.deals_for_you.length === 0 ? (
        <p className="text-sm text-muted">We&apos;re collecting discounts for your cards. Check back soon.</p>
      ) : (
        <ul className="space-y-3">
          {d.deals_for_you.map((deal) => (
            <li key={deal.id} className="flex items-center gap-3.5 rounded-2xl bg-surface p-3"
              title={deal.your_eligible_cards[0] ? `With your ${deal.your_eligible_cards[0]}` : "Any card or cash"}>
              <span className="tabular grid h-12 min-w-[4.75rem] shrink-0 place-items-center rounded-xl bg-deal px-2 text-[15px] font-bold text-white">
                {deal.discount_type === "percent" && deal.discount_value ? `${deal.discount_value}%`
                  : deal.discount_type === "flat" && deal.discount_value ? rs(deal.discount_value, { compact: true })
                    : deal.discount_type === "bogo" ? "1+1" : "Deal"}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-semibold text-ink sm:text-lg">{deal.merchant}</span>
                <span className="line-clamp-2 text-sm text-muted">
                  {deal.title}{deal.valid_until && ` · till ${day(deal.valid_until)}`}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function ActivityCard({ d, id, className }: { d: Dashboard } & SectionProps) {
  return (
    <Card id={id} data-section={id ? "" : undefined} className={clsx("wide:col-span-4", className)}>
      <h2 className={clsx(title, "mb-4")}>Recent activity</h2>
      {d.recent_transactions.length === 0 ? (
        <p className="text-sm text-muted">Transactions from your bank emails or chat appear here.</p>
      ) : (
        <ul className="divide-y divide-line md:-mr-2 md:max-h-[24rem] md:overflow-y-auto md:overscroll-contain md:pr-2">
          {d.recent_transactions.map((t) => (
            <li key={t.id} className="flex items-start justify-between gap-3 py-3.5 first:pt-0">
              <span className="min-w-0">
                <span className="block truncate font-semibold text-ink sm:text-lg">{t.merchant || (t.direction === "credit" ? "Money in" : "Payment")}</span>
                <span className="block text-sm text-muted capitalize">{t.category} · {day(t.occurred_at)}</span>
              </span>
              <span className="tabular font-bold whitespace-nowrap text-ink sm:text-lg">
                {t.direction === "credit" ? "+" : "−"} {rs(t.amount)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

/** Goal tiles with a progress ring: three across from tablets up, a list with the % inside the ring on phones. */
export function GoalsCard({ goals, id, className, showAll = false }: { goals: Dashboard["goals"]; showAll?: boolean } & SectionProps) {
  const [all, setAll] = useState(showAll);
  const shown = all ? goals : goals.slice(0, 3);
  const when = (g: Dashboard["goals"][number]) =>
    g.status === "completed" ? "Completed" : g.deadline ? monthYear(g.deadline) : "Anytime";
  return (
    <Card id={id} data-section={id ? "" : undefined} className={clsx("md:col-span-2 wide:col-span-7", className)}>
      <div className="mb-5 flex items-center justify-between">
        <h2 className={title}>Goals</h2>
        {goals.length > 3 && !showAll && (
          <button onClick={() => setAll((v) => !v)} className="text-[15px] font-semibold text-forest hover:underline dark:text-primary sm:text-base">
            {all ? "Show less" : "See all"}
          </button>
        )}
      </div>
      {goals.length === 0 ? (
        <Empty icon={<Target className="size-6" />} title="No goals yet"
          body="Tell your assistant what you're saving for, like “a car in 6 months”."
          action={<Link href="?chat=1" className="mt-2 text-sm font-semibold text-forest dark:text-primary">Add a goal in chat</Link>} />
      ) : (
        <ul className="grid gap-3 sm:grid-cols-3 sm:gap-4">
          {shown.map((g) => (
            <li key={g.id}>
              <Link href={`/goals/${g.id}`}
                className="flex h-full items-center gap-4 rounded-[1.25rem] bg-surface-2 p-4 transition hover:brightness-[0.98] sm:flex-col sm:items-start sm:gap-0 sm:p-5">
                <span className="sm:hidden">
                  <ProgressRing value={g.progress} size={56} thickness={6} label={`${g.name} progress`}>
                    <span className="tabular text-sm font-bold text-ink">{Math.round(g.progress * 100)}%</span>
                  </ProgressRing>
                </span>
                <span className="hidden sm:block">
                  <ProgressRing value={g.progress} size={76} thickness={8} label={`${g.name}: ${Math.round(g.progress * 100)}% saved`}>
                    <span />
                  </ProgressRing>
                </span>
                <span className="min-w-0 flex-1 sm:mt-5">
                  <span className="block truncate font-bold text-ink sm:text-xl">{g.name}</span>
                  <span className="tabular mt-0.5 block text-sm text-muted sm:mt-1.5 sm:text-base">Rs. {short(g.saved)} of {short(g.target)}</span>
                  <span className="mt-1 hidden text-sm text-muted sm:block">
                    {g.deadline && g.status !== "completed" ? `by ${monthYear(g.deadline)}` : when(g)}
                  </span>
                </span>
                <span className="text-sm text-muted sm:hidden">{when(g)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
