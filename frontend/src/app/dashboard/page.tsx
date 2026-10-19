"use client";

import clsx from "clsx";
import { ChevronRight, Mail, MessageCircle, PiggyBank, Target } from "lucide-react";
import Link from "next/link";
import { useCallback, useState } from "react";
import useSWR from "swr";
import { AppShell, openSettings } from "@/components/AppShell";
import { BankModal } from "@/components/BankModal";
import { CategoryStack, ProgressRing } from "@/components/charts";
import { Card, Empty, Spinner } from "@/components/ui";
import { fetcher, rs } from "@/lib/api";
import { useSession } from "@/lib/session";

type Dashboard = {
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

export default function DashboardPage() {
  const { data, mutate } = useSWR<Dashboard>("/dashboard", fetcher, { refreshInterval: 60_000 });
  const refresh = useCallback(() => {
    mutate();
  }, [mutate]);
  return <AppShell onChatActivity={refresh}>{data ? <DashboardView d={data} /> : <div className="grid h-64 place-items-center"><Spinner /></div>}</AppShell>;
}

/** "Rs. 420k", "Rs. 1.2M": the short amounts used on goal tiles. */
const short = (v: number | string) => {
  const n = Number(v);
  const fmt = (x: number) => x.toFixed(1).replace(/\.0$/, "");
  if (Math.abs(n) >= 1_000_000) return `${fmt(n / 1_000_000)}M`;
  if (Math.abs(n) >= 1_000) return `${fmt(n / 1_000)}k`;
  return `${Math.round(n)}`;
};
const day = (d: string) => new Date(d).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
const monthYear = (d: string) => new Date(d).toLocaleDateString("en-GB", { month: "short", year: "numeric" });
const title = "text-xl font-bold tracking-tight text-ink sm:text-2xl";

function DashboardView({ d }: { d: Dashboard }) {
  const { user } = useSession();
  const [bank, setBank] = useState<string | null>(null);
  const hasData = d.banks.length > 0 || d.goals.length > 0;
  const total = Number(d.total_balance);
  const savedShare = total > 0 ? Number(d.total_savings) / total : 0;

  return (
    <div className="space-y-5 sm:space-y-6">
      {bank && <BankModal accountId={bank} onClose={() => setBank(null)} />}

      {!user?.onboarding_completed && (
        <Link href="?chat=1" className="flex items-center gap-4 rounded-[var(--radius-card)] bg-forest p-5 text-forest-ink sm:px-7">
          <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-primary text-primary-ink">
            <MessageCircle className="size-6" aria-hidden />
          </span>
          <span className="flex-1">
            <span className="block font-semibold">Let&apos;s set up your plan</span>
            <span className="block text-sm text-forest-muted">Chat with your assistant about your banks, cards and goals. It takes 3 minutes.</span>
          </span>
          <ChevronRight className="size-5" aria-hidden />
        </Link>
      )}

      {/* Row 1: balance, then "saved this week" and "saved with deals" (beside it from tablets up, below it on phones). */}
      <section id="home" data-section className="grid gap-4 sm:gap-5 md:grid-cols-[2fr_1fr] xl:grid-cols-[1.85fr_1fr]">
        <div className="flex flex-col justify-between gap-6 rounded-[2rem] bg-forest p-6 text-forest-ink sm:p-8 lg:p-9">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-[15px] text-forest-muted sm:text-lg">Total balance</p>
              <p className="tabular mt-1 text-[2.5rem] leading-none font-bold tracking-tight whitespace-nowrap sm:mt-2 sm:text-5xl xl:text-7xl">
                {rs(d.total_balance)}
              </p>
            </div>
            <span className="xl:hidden">
              <ProgressRing value={savedShare} size={84} thickness={11} label={`${Math.round(savedShare * 100)}% of your balance is saved`}
                trackClassName="stroke-forest-track" barClassName="stroke-primary">
                <span className="tabular text-xl font-bold xl:text-[1.75rem]">{Math.round(savedShare * 100)}%</span>
              </ProgressRing>
            </span>
            <span className="hidden xl:block">
              <ProgressRing value={savedShare} size={128} thickness={15} label={`${Math.round(savedShare * 100)}% of your balance is saved`}
                trackClassName="stroke-forest-track" barClassName="stroke-primary">
                <span className="tabular text-xl font-bold xl:text-[1.75rem]">{Math.round(savedShare * 100)}%</span>
              </ProgressRing>
            </span>
          </div>
          <dl className="grid grid-cols-2 gap-3 sm:gap-4">
            <div className="rounded-2xl bg-forest-2 px-4 py-3.5 sm:px-5 sm:py-4">
              <dt className="flex items-center gap-2 text-sm text-forest-muted sm:text-base">
                <span className="size-2.5 rounded-full bg-primary sm:size-3" aria-hidden />Savings
              </dt>
              <dd className="tabular mt-1 text-lg font-bold whitespace-nowrap sm:text-2xl">{rs(d.total_savings)}</dd>
            </div>
            <div className="rounded-2xl bg-forest-2 px-4 py-3.5 sm:px-5 sm:py-4">
              <dt className="flex items-center gap-2 text-sm text-forest-muted sm:text-base">
                <span className="size-2.5 rounded-full border-[1.5px] border-forest-muted sm:size-3" aria-hidden />Spendable
              </dt>
              <dd className="tabular mt-1 text-lg font-bold whitespace-nowrap sm:text-2xl">{rs(d.expendable)}</dd>
            </div>
          </dl>
        </div>

        <div className="grid grid-cols-2 gap-4 sm:gap-5 md:grid-cols-1">
          <div className="flex flex-col justify-center rounded-[2rem] bg-primary p-5 text-primary-ink sm:p-7">
            <p className="text-sm font-semibold sm:text-base">Saved this week</p>
            <p className="tabular mt-1 text-2xl font-bold tracking-tight whitespace-nowrap sm:mt-2 sm:text-3xl xl:text-[2.6rem]">{rs(d.saved_this_week)}</p>
            <p className="mt-1 text-xs sm:mt-2 sm:text-base">
              {Number(d.saved_this_week) > 0 ? <>Great going<span className="max-xl:hidden">, keep it up</span>!</> : "Your next salary starts it off."}
            </p>
          </div>
          <div className="flex flex-col justify-center rounded-[2rem] bg-surface p-5 sm:p-7">
            <p className="text-sm text-muted sm:text-base">Saved with deals</p>
            <p className="tabular mt-1 text-2xl font-bold tracking-tight whitespace-nowrap text-ink sm:mt-2 sm:text-3xl xl:text-[2.6rem]">{rs(d.deal_savings_total)}</p>
            <p className="mt-1 text-xs text-muted sm:mt-2 sm:text-base">From card discounts</p>
          </div>
        </div>
      </section>

      {!d.email_connected && hasData && (
        <button type="button" onClick={() => openSettings("email")}
          className="flex w-full items-center gap-3 rounded-[var(--radius-card)] bg-surface p-4 text-left sm:px-7">
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-badge text-forest dark:text-primary">
            <Mail className="size-5" aria-hidden />
          </span>
          <span className="flex-1 text-sm sm:text-base"><span className="font-semibold">Connect your email</span> to track bank transactions automatically.</span>
          <ChevronRight className="size-5 text-muted" aria-hidden />
        </button>
      )}

      {/*
        One grid for the rest, in reading order. Phones: one column. Tablets: goals full width, then pairs.
        Wide laptops (12 columns, `wide:` = 1380px+): goals + spending, then banks, deals and activity side by side.
      */}
      <div className="grid gap-4 sm:gap-5 md:grid-cols-2 wide:grid-cols-12">
        <Goals goals={d.goals} />

        <Card id="spending" data-section className="wide:col-span-5">
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

        <Card id="banks" data-section className="wide:col-span-4">
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

        <Card id="deals" data-section className="bg-deal-bg! wide:col-span-4">
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

        <Card className="wide:col-span-4">
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
      </div>
    </div>
  );
}

/** Goal tiles with a progress ring: three across from tablets up, a list with the % inside the ring on phones. */
function Goals({ goals }: { goals: Dashboard["goals"] }) {
  const [all, setAll] = useState(false);
  const shown = all ? goals : goals.slice(0, 3);
  const when = (g: Dashboard["goals"][number]) =>
    g.status === "completed" ? "Completed" : g.deadline ? monthYear(g.deadline) : "Anytime";
  return (
    <Card id="goals" data-section className="md:col-span-2 wide:col-span-7">
      <div className="mb-5 flex items-center justify-between">
        <h2 className={title}>Goals</h2>
        {goals.length > 3 && (
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
