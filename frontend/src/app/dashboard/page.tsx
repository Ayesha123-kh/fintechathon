"use client";

import { ChevronRight, Mail, MessageCircle } from "lucide-react";
import Link from "next/link";
import { useCallback } from "react";
import useSWR from "swr";
import { AppShell, openSettings } from "@/components/AppShell";
import { ProgressRing } from "@/components/charts";
import {
  ActivityCard, BanksCard, type Dashboard, DealsCard, GoalsCard, SpendingCard, useDashboard,
} from "@/components/dashboard/sections";
import { Spinner } from "@/components/ui";
import { fetcher, rs } from "@/lib/api";
import { useSession } from "@/lib/session";

export default function DashboardPage() {
  const { data, mutate } = useDashboard();
  const refresh = useCallback(() => {
    mutate();
  }, [mutate]);
  return <AppShell onChatActivity={refresh}>{data ? <DashboardView d={data} /> : <div className="grid h-64 place-items-center"><Spinner /></div>}</AppShell>;
}

function DashboardView({ d }: { d: Dashboard }) {
  const { user } = useSession();
  // New users connect Gmail first (read-only bank alerts), then set up the rest in chat.
  const { data: email } = useSWR<{ configured: boolean; connections: unknown[] }>(
    user && !user.onboarding_completed ? "/email/connections" : null, fetcher);
  const needsEmail = !!email?.configured && email.connections.length === 0;
  const hasData = d.banks.length > 0 || d.goals.length > 0;
  const total = Number(d.total_balance);
  const savedShare = total > 0 ? Number(d.total_savings) / total : 0;

  return (
    <div className="space-y-5 sm:space-y-6">
      {!user?.onboarding_completed && needsEmail && (
        <button type="button" onClick={() => openSettings("email")}
          className="flex w-full items-center gap-4 rounded-[var(--radius-card)] bg-forest p-5 text-left text-forest-ink sm:px-7">
          <span className="grid size-12 shrink-0 place-items-center rounded-2xl bg-primary text-primary-ink">
            <Mail className="size-6" aria-hidden />
          </span>
          <span className="flex-1">
            <span className="block font-semibold">Step 1: connect your Gmail</span>
            <span className="block text-sm text-forest-muted">We read your bank alerts (read-only) so your plan starts from real spending. Then chat with your assistant.</span>
          </span>
          <ChevronRight className="size-5" aria-hidden />
        </button>
      )}
      {!user?.onboarding_completed && !needsEmail && (
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

      {/* Row 1: balance, then "saved this month" and "saved with deals" this month (beside it from tablets up, below it on phones). */}
      <section id="home" data-section className="grid grid-cols-1 gap-4 sm:gap-5 md:grid-cols-[2fr_1fr] xl:grid-cols-[1.85fr_1fr]">
        <div className="flex flex-col justify-between gap-6 rounded-[2rem] bg-forest p-6 text-forest-ink sm:p-8 lg:p-9">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-[15px] text-forest-muted sm:text-lg">Total balance</p>
              <p className="tabular mt-1 text-[clamp(1.75rem,10vw,2.5rem)] leading-none font-bold tracking-tight whitespace-nowrap sm:mt-2 sm:text-5xl xl:text-7xl">
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
              <dd className="tabular mt-1 text-[clamp(0.95rem,4.6vw,1.125rem)] font-bold whitespace-nowrap sm:text-2xl">{rs(d.total_savings)}</dd>
            </div>
            <div className="rounded-2xl bg-forest-2 px-4 py-3.5 sm:px-5 sm:py-4">
              <dt className="flex items-center gap-2 text-sm text-forest-muted sm:text-base">
                <span className="size-2.5 rounded-full border-[1.5px] border-forest-muted sm:size-3" aria-hidden />Spendable
              </dt>
              <dd className="tabular mt-1 text-[clamp(0.95rem,4.6vw,1.125rem)] font-bold whitespace-nowrap sm:text-2xl">{rs(d.expendable)}</dd>
            </div>
          </dl>
        </div>

        <div className="grid grid-cols-2 gap-4 sm:gap-5 md:grid-cols-1">
          <div className="flex flex-col justify-center rounded-[2rem] bg-primary p-5 text-primary-ink sm:p-7">
            <p className="text-sm font-semibold sm:text-base">Saved this month</p>
            <p className="tabular mt-1 text-[clamp(1.125rem,6vw,1.5rem)] font-bold tracking-tight whitespace-nowrap sm:mt-2 sm:text-3xl xl:text-[2.6rem]">{rs(d.saved_this_month)}</p>
            <p className="mt-1 text-xs sm:mt-2 sm:text-base">
              {Number(d.saved_this_month) > 0 ? <>Great going<span className="max-xl:hidden">, keep it up</span>!</> : "Your next salary starts it off."}
            </p>
          </div>
          <div className="flex flex-col justify-center rounded-[2rem] bg-surface p-5 sm:p-7">
            <p className="text-sm text-muted sm:text-base">Saved with deals</p>
            <p className="tabular mt-1 text-[clamp(1.125rem,6vw,1.5rem)] font-bold tracking-tight whitespace-nowrap text-ink sm:mt-2 sm:text-3xl xl:text-[2.6rem]">{rs(d.deal_savings_this_month)}</p>
            <p className="mt-1 text-xs text-muted sm:mt-2 sm:text-base">From card discounts this month</p>
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
        One grid for the rest, in reading order. Phones: only the banks here; goals, spending, deals and activity each
        have their own page in the bottom bar. Tablets: goals full width, then pairs. Wide laptops (12 columns,
        `wide:` = 1380px+): goals + spending, then banks, deals and activity side by side.
      */}
      <div className="grid grid-cols-1 gap-4 sm:gap-5 md:grid-cols-2 wide:grid-cols-12">
        <GoalsCard id="goals" goals={d.goals} className="max-sm:hidden" />
        <SpendingCard id="spending" d={d} className="max-sm:hidden" />
        <BanksCard id="banks" d={d} />
        <DealsCard id="deals" d={d} className="max-sm:hidden" />
        <ActivityCard d={d} className="max-sm:hidden" />
      </div>
    </div>
  );
}
