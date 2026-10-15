"use client";

import { ArrowLeft, CalendarClock, MessageCircle, TrendingUp } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { AppShell } from "@/components/AppShell";
import { GoalIcon } from "@/components/GoalIcon";
import { Card, ProgressBar, Spinner } from "@/components/ui";
import { fetcher, rs } from "@/lib/api";

type Goal = {
  id: string; name: string; icon: string; status: string; priority: number; target: string; saved: string; remaining: string;
  deadline: string | null; progress: number; monthly_needed: string; monthly_rate: string; projected_completion: string | null;
  on_track: boolean; history: { id: string; amount: string; source: string; note: string; created_at: string }[];
};

const SOURCE: Record<string, string> = {
  allocation: "Monthly savings", deal_saving: "Saved with a deal", manual: "Added by you", withdrawal: "Withdrawn",
  sadqah: "Sadqah", goal_completed: "Goal completed",
};

const fmtDate = (d: string) => new Date(d).toLocaleDateString("en-PK", { day: "numeric", month: "short", year: "numeric" });

export default function GoalPage() {
  const { id } = useParams<{ id: string }>();
  const { data: g, error, mutate } = useSWR<Goal>(`/goals/${id}`, fetcher);
  return (
    <AppShell onChatActivity={() => mutate()}>
      <Link href="/dashboard" className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-muted hover:text-ink">
        <ArrowLeft className="size-4" aria-hidden /> Dashboard
      </Link>
      {error ? <p className="text-muted">This goal could not be found.</p> : !g ? <Spinner /> : (
        <div className="grid gap-5 lg:grid-cols-5">
          <div className="space-y-5 lg:col-span-3">
            <Card>
              <div className="flex items-center gap-4">
                <GoalIcon name={g.icon} size="lg" />
                <div>
                  <h1 className="text-2xl font-bold">{g.name}</h1>
                  <p className="text-sm text-muted">
                    {g.status === "completed" ? "Completed 🎉" : g.status === "paused" ? "Paused" : `Priority ${g.priority}`}
                    {g.deadline && ` · Target date ${fmtDate(g.deadline)}`}
                  </p>
                </div>
              </div>
              <div className="mt-6 flex items-end justify-between gap-2">
                <div>
                  <p className="text-sm text-muted">Saved</p>
                  <p className="tabular text-3xl font-bold">{rs(g.saved)}</p>
                </div>
                <p className="tabular pb-1 text-right text-sm text-muted">of {rs(g.target)}<br />
                  <span className="text-lg font-bold text-ink">{Math.round(g.progress * 100)}%</span></p>
              </div>
              <div className="mt-3"><ProgressBar value={g.progress} label="Goal progress" /></div>
            </Card>

            <div className="grid grid-cols-2 gap-3">
              <Card>
                <CalendarClock className="mb-2 size-5 text-muted" aria-hidden />
                <p className="text-sm text-muted">Needed per month</p>
                <p className="tabular text-lg font-bold">{rs(g.monthly_needed)}</p>
              </Card>
              <Card>
                <TrendingUp className="mb-2 size-5 text-muted" aria-hidden />
                <p className="text-sm text-muted">Your recent pace</p>
                <p className="tabular text-lg font-bold">{rs(g.monthly_rate)}<span className="text-sm font-normal text-muted">/mo</span></p>
              </Card>
            </div>

            {g.status === "active" && (
              <Card className={g.on_track ? "bg-primary/35" : "bg-surface"}>
                <p className="font-semibold">{g.on_track ? "You're on track 👏" : "A little behind schedule"}</p>
                <p className="mt-1 text-sm text-ink-2">
                  {g.projected_completion
                    ? `At your current pace you'll reach it around ${fmtDate(g.projected_completion)}.`
                    : "Once savings start flowing in, we'll project your finish date."}
                </p>
                <Link href="?chat=1" className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-forest dark:text-primary">
                  <MessageCircle className="size-4" aria-hidden /> Ask your coach how to speed it up
                </Link>
              </Card>
            )}
          </div>

          <Card className="lg:col-span-2">
            <h2 className="mb-3 text-lg font-bold">History</h2>
            {g.history.length === 0 ? (
              <p className="py-4 text-sm text-muted">No savings added yet. Your next salary will start filling this goal.</p>
            ) : (
              <ul className="divide-y divide-line">
                {g.history.map((h) => (
                  <li key={h.id} className="flex items-center justify-between gap-3 py-3">
                    <div>
                      <p className="text-sm font-medium">{SOURCE[h.source] ?? h.source}</p>
                      <p className="text-xs text-muted">{h.note || fmtDate(h.created_at)}</p>
                    </div>
                    <p className="tabular text-sm font-semibold">{Number(h.amount) >= 0 ? "+" : "−"}{rs(Math.abs(Number(h.amount)))}</p>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      )}
    </AppShell>
  );
}
