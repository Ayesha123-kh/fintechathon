"use client";

import { useCallback } from "react";
import { AppShell } from "@/components/AppShell";
import { Spinner } from "@/components/ui";
import { type Dashboard, useDashboard } from "./sections";

/** A page showing one dashboard section on its own (the phone bottom nav opens these). */
export function SectionPage({ children }: { children: (d: Dashboard) => React.ReactNode }) {
  const { data, mutate } = useDashboard();
  const refresh = useCallback(() => {
    mutate();
  }, [mutate]);
  return (
    <AppShell onChatActivity={refresh}>
      {data ? <div className="space-y-5">{children(data)}</div> : <div className="grid h-64 place-items-center"><Spinner /></div>}
    </AppShell>
  );
}
