"use client";

import { ArrowDownLeft, ArrowUpRight, ChevronRight, Mail, MessageCircle, PiggyBank, Sparkles, Tag, Target } from "lucide-react";
import Link from "next/link";
import { useCallback, useState } from "react";
import useSWR from "swr";
import { AppShell, openSettings } from "@/components/AppShell";
import { MobileTabBar, type Tab, useMobileTab } from "@/components/MobileTabBar";
import { BankModal } from "@/components/BankModal";
import { CategoryBars, Donut, ProgressRing, SplitDonut, SplitLegend } from "@/components/charts";
import { GoalIconGlyph } from "@/components/GoalIcon";
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

function DashboardView({ d }: { d: Dashboard }) {
  const { user } = useSession();
  const [bank, setBank] = useState<string | null>(null);
  const [tab, setTab] = useMobileTab();
  // On phones only the active tab's sections are shown; laptops always show everything.
  const on = (t: Tab) => (tab === t ? "" : "max-md:hidden");
  const first = user?.full_name?.split(" ")[0];
  const hasData = d.banks.length > 0 || d.goals.length > 0;

  return (
    <>
    {/* Outside the spaced container: a fixed bar must not pick up its children's margins. */}
    <MobileTabBar tab={tab} onChange={setTab} />
    <div className="space-y-5 max-md:pb-24">
      {bank && <BankModal accountId={bank} onClose={() => setBank(null)} />}
      <div className={on("home")}>
        <p className="text-sm text-muted">Assalam o Alaikum{first ? `, ${first}` : ""}</p>
        <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Your money at a glance</h1>
      </div>

      {!user?.onboarding_completed && tab === "home" && (
        <Link href="?chat=1" className="flex items-center gap-4 rounded-[var(--radius-card)] bg-forest p-5 text-forest-ink">
          <div className="grid size-12 shrink-0 place-items-center rounded-2xl bg-primary text-primary-ink">
            <MessageCircle className="size-6" aria-hidden />
          </div>
          <div className="flex-1">
            <p className="font-semibold">Let&apos;s set up your plan</p>
            <p className="text-sm opacity-85">Chat with your assistant about your banks, cards and goals. It takes 3 minutes.</p>
          </div>
          <ChevronRight className="size-5" aria-hidden />
        </Link>
      )}

      {/* Phones: amounts | circle on top, pills full width below. sm+: pills under the amounts, circle spans both. */}
      <Card className={`grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-4 md:p-7 ${on("home")}`}>
        <div className="min-w-0 space-y-4">
          <div>
            <p className="text-sm text-muted">Total balance</p>
            <p className="tabular text-2xl font-bold whitespace-nowrap sm:text-3xl md:text-4xl">{rs(d.total_balance)}</p>
          </div>
          <dl className="space-y-3">
            <div>
              <dt className="flex items-center gap-1.5 text-sm text-muted"><span className="size-2.5 rounded-full bg-chart-save" />Savings</dt>
              <dd className="tabular text-lg font-bold whitespace-nowrap sm:text-xl">{rs(d.total_savings)}</dd>
              <dd className="text-xs text-muted">Set aside for your goals</dd>
            </div>
            <div>
              <dt className="flex items-center gap-1.5 text-sm text-muted"><span className="size-2.5 rounded-full bg-chart-spend ring-1 ring-forest/30" />Spendable</dt>
              <dd className="tabular text-lg font-bold whitespace-nowrap sm:text-xl">{rs(d.expendable)}</dd>
              <dd className="text-xs text-muted">Spent {rs(d.spent_this_month, { compact: true })} this month</dd>
            </div>
          </dl>
        </div>
        <div className="sm:hidden"><Donut
          size={136}
          thickness={16}
          label={`Total ${rs(d.total_balance)}: savings ${rs(d.total_savings)}, spendable ${rs(d.expendable)}`}
          segments={[
            { key: "s", label: "Savings", value: Number(d.total_savings), className: "stroke-chart-save" },
            { key: "e", label: "Spendable", value: Number(d.expendable), className: "stroke-chart-spend" },
          ]}
          center={
            <div>
              <p className="text-[11px] text-muted">Total</p>
              <p className="tabular text-lg font-bold">{rs(d.total_balance, { compact: true })}</p>
              <p className="text-[11px] text-muted">
                {Number(d.total_balance) ? Math.round((Number(d.total_savings) / Number(d.total_balance)) * 100) : 0}% saved
              </p>
            </div>
          }
        /></div>
        <div className="hidden sm:col-start-2 sm:row-span-2 sm:row-start-1 sm:block"><Donut
          size={200}
          thickness={22}
          label={`Total ${rs(d.total_balance)}: savings ${rs(d.total_savings)}, spendable ${rs(d.expendable)}`}
          segments={[
            { key: "s", label: "Savings", value: Number(d.total_savings), className: "stroke-chart-save" },
            { key: "e", label: "Spendable", value: Number(d.expendable), className: "stroke-chart-spend" },
          ]}
          center={
            <div>
              <p className="text-[11px] text-muted">Total</p>
              <p className="tabular text-lg font-bold">{rs(d.total_balance, { compact: true })}</p>
              <p className="text-[11px] text-muted">
                {Number(d.total_balance) ? Math.round((Number(d.total_savings) / Number(d.total_balance)) * 100) : 0}% saved
              </p>
            </div>
          }
        /></div>
        <div className="col-span-2 flex flex-wrap gap-2 text-sm sm:col-span-1 sm:col-start-1">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-primary px-3 py-1 font-semibold whitespace-nowrap text-primary-ink">
            <Sparkles className="size-3.5" aria-hidden /> {rs(d.saved_this_week)} saved this week
          </span>
          {Number(d.deal_savings_total) > 0 && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-forest/30 bg-surface-2 px-3 py-1 whitespace-nowrap">
              <Tag className="size-3.5" aria-hidden /> {rs(d.deal_savings_total)} saved with deals
            </span>
          )}
        </div>
      </Card>

      {!d.email_connected && hasData && (
        <button type="button" onClick={() => openSettings("email")} className={`flex w-full items-center gap-3 text-left ${on("home")} rounded-[var(--radius-card)] border border-dashed border-forest/40 bg-surface p-4`}>
          <Mail className="size-5 text-forest dark:text-primary" aria-hidden />
          <p className="flex-1 text-sm"><span className="font-semibold">Connect your email</span> to track bank transactions automatically.</p>
          <ChevronRight className="size-4 text-muted" aria-hidden />
        </button>
      )}

      <div className="grid gap-5 lg:grid-cols-5">
        <div className="space-y-5 lg:col-span-3">
          <Card className={on("goals")}>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-bold">Goals</h2>
              <Target className="size-5 text-muted" aria-hidden />
            </div>
            {d.goals.length === 0 ? (
              <Empty icon={<Target className="size-6" />} title="No goals yet"
                body="Tell your assistant what you're saving for, like “a car in 6 months”."
                action={<Link href="?chat=1" className="mt-2 text-sm font-semibold text-forest dark:text-primary">Add a goal in chat</Link>} />
            ) : (
              <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {d.goals.map((g) => (
                  <li key={g.id}>
                    <Link href={`/goals/${g.id}`}
                      className="flex h-full flex-col items-center gap-2 rounded-2xl border-2 border-forest dark:border-primary bg-surface-2 p-4 text-center transition hover:brightness-[0.98]">
                      <ProgressRing value={g.progress} size={88} thickness={9} label={`${g.name} progress`}>
                        <div className="flex flex-col items-center">
                          <GoalIconGlyph name={g.icon} />
                          <span className="tabular text-sm font-bold">{Math.round(g.progress * 100)}%</span>
                        </div>
                      </ProgressRing>
                      <p className="line-clamp-2 text-sm font-semibold leading-tight">{g.name}</p>
                      <p className="tabular text-xs text-muted">{rs(g.saved, { compact: true })} / {rs(g.target, { compact: true })}</p>
                      {g.status === "completed" ? (
                        <p className="text-xs font-semibold text-forest dark:text-primary">Completed 🎉</p>
                      ) : (
                        <p className="text-[11px] text-muted">
                          {g.deadline ? `by ${new Date(g.deadline).toLocaleDateString("en-PK", { month: "short", year: "numeric" })}` : "No deadline"}
                          {Number(g.monthly_needed) > 0 && ` · ${rs(g.monthly_needed, { compact: true })}/mo`}
                        </p>
                      )}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card className={on("home")}>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-lg font-bold">Where your money is</h2>
              <SplitLegend />
            </div>
            {d.banks.length === 0 ? (
              <Empty icon={<PiggyBank className="size-6" />} title="No banks added" body="Tell your assistant which banks and wallets you use." />
            ) : (
              <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {d.banks.map((b) => (
                  <li key={b.account_id}>
                    <button type="button" onClick={() => setBank(b.account_id)} aria-label={`${b.bank} details`}
                      className="flex h-full w-full flex-col items-center gap-2 rounded-2xl border-2 border-forest dark:border-primary bg-surface-2 p-4 text-center transition hover:brightness-[0.98]">
                      <SplitDonut savings={Number(b.savings)} expendable={Number(b.expendable)} label={b.bank} size={96} thickness={12} />
                      <p className="text-sm font-semibold">{b.bank_short}</p>
                      <dl className="tabular grid w-full grid-cols-2 gap-1 text-[11px]">
                        <div><dt className="text-muted">Savings</dt><dd className="font-semibold whitespace-nowrap">{rs(b.savings, { compact: true })}</dd></div>
                        <div><dt className="text-muted">Spendable</dt><dd className="font-semibold whitespace-nowrap">{rs(b.expendable, { compact: true })}</dd></div>
                      </dl>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card className={on("activity")}>
            <h2 className="mb-3 text-lg font-bold">Recent activity</h2>
            {d.recent_transactions.length === 0 ? (
              <p className="py-4 text-sm text-muted">Transactions from your bank emails or chat appear here.</p>
            ) : (
              <ul className="divide-y divide-line md:-mr-2 md:max-h-[22rem] md:overflow-y-auto md:overscroll-contain md:pr-2">
                {d.recent_transactions.map((t) => (
                  <li key={t.id} className="flex items-center gap-3 py-2.5">
                    <span className="grid size-9 place-items-center rounded-full bg-surface-2">
                      {t.direction === "credit" ? <ArrowDownLeft className="size-4 text-forest dark:text-primary" aria-label="Money in" /> : <ArrowUpRight className="size-4 text-muted" aria-label="Money out" />}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{t.merchant || (t.direction === "credit" ? "Money in" : "Payment")}</p>
                      <p className="text-xs capitalize text-muted">{t.category} · {new Date(t.occurred_at).toLocaleDateString("en-PK", { day: "numeric", month: "short" })}</p>
                    </div>
                    <p className="tabular text-sm font-semibold">{t.direction === "credit" ? "+" : "−"}{rs(t.amount)}</p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>

        <div className="space-y-5 lg:col-span-2">
          <Card className={on("spending")}>
            <h2 className="mb-4 text-lg font-bold">Spending this month</h2>
            {d.spending_by_category.length === 0 ? (
              <p className="py-4 text-sm text-muted">No spending recorded yet this month.</p>
            ) : (
              <CategoryBars rows={d.spending_by_category} />
            )}
          </Card>

          <Card className={on("deals")}>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-bold">Deals for you</h2>
              <Tag className="size-5 text-muted" aria-hidden />
            </div>
            {d.deals_for_you.length === 0 ? (
              <p className="py-4 text-sm text-muted">We&apos;re collecting discounts for your cards. Check back soon.</p>
            ) : (
              <ul className="space-y-2.5">
                {d.deals_for_you.map((deal) => (
                  <li key={deal.id} className="rounded-2xl border-2 border-forest dark:border-primary bg-surface-2 p-3.5">
                    <div className="flex items-start gap-3">
                      <span className="tabular grid min-w-14 place-items-center rounded-xl bg-primary px-2 py-1.5 text-sm font-bold text-primary-ink">
                        {deal.discount_type === "percent" && deal.discount_value ? `${deal.discount_value}%` : deal.discount_type === "flat" && deal.discount_value ? rs(deal.discount_value, { compact: true }) : deal.discount_type === "bogo" ? "1+1" : "Deal"}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-semibold">{deal.merchant}</p>
                        <p className="text-sm text-ink-2">{deal.title}</p>
                        <p className="mt-1 text-xs text-muted">
                          {deal.your_eligible_cards[0] ? `With your ${deal.your_eligible_cards[0]}` : "Any card or cash"}
                          {deal.valid_until && ` · until ${new Date(deal.valid_until).toLocaleDateString("en-PK", { day: "numeric", month: "short" })}`}
                        </p>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
    </>
  );
}
