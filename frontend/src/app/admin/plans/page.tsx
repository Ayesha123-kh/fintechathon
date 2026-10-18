"use client";

import useSWR from "swr";
import { Card, Spinner } from "@/components/ui";
import { fetcher, rs } from "@/lib/api";
import { PageHeader } from "@/components/admin";

type Plan = { id: string; code: string; name: string; price_monthly: string; currency: string; features: object; is_active: boolean; subscribers: number };

function PlansTab() {
  const { data } = useSWR<Plan[]>("/admin/plans", fetcher);
  if (!data) return <Spinner />;
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {data.map((p) => (
        <Card key={p.id}>
          <div className="flex items-baseline justify-between">
            <h2 className="text-lg font-bold">{p.name}</h2>
            <p className="tabular font-semibold">{Number(p.price_monthly) ? `${rs(p.price_monthly)}/mo` : "Free"}</p>
          </div>
          <p className="mt-1 text-sm text-muted">{p.subscribers} active subscribers · code {p.code}</p>
          <pre className="mt-3 overflow-auto rounded-2xl bg-surface-2 p-3 text-xs">{JSON.stringify(p.features, null, 2)}</pre>
        </Card>
      ))}
      <Card className="md:col-span-2">
        <p className="text-sm text-muted">
          Payments aren&apos;t live yet. Subscriptions and payments tables already store provider, customer and subscription ids,
          so a gateway (e.g. a Pakistani PSP or Stripe) can be connected later without schema changes.
        </p>
      </Card>
    </div>
  );
}

export default function Page() {
  return (
    <div className="space-y-5">
      <PageHeader title="Plans" subtitle="Subscription plans and their subscribers." />
      <PlansTab />
    </div>
  );
}
