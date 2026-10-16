"use client";

import clsx from "clsx";
import { ArrowLeftRight, Home, PieChart, Tag, Target } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

export type Tab = "goals" | "spending" | "home" | "deals" | "activity";
const TABS: { id: Tab; label: string; icon: typeof Home }[] = [
  { id: "goals", label: "Goals", icon: Target },
  { id: "spending", label: "Spending", icon: PieChart },
  { id: "home", label: "Home", icon: Home },
  { id: "deals", label: "Deals", icon: Tag },
  { id: "activity", label: "Activity", icon: ArrowLeftRight },
];
const isTab = (v: string | null): v is Tab => TABS.some((t) => t.id === v);

/** Active phone tab, kept in the URL (?tab=) so back/forward and returning from a goal page work like pages. */
export function useMobileTab(): [Tab, (t: Tab) => void] {
  const [tab, setTabState] = useState<Tab>("home");
  useEffect(() => {
    const read = () => {
      const t = new URLSearchParams(window.location.search).get("tab");
      setTabState(isTab(t) ? t : "home");
    };
    read();
    window.addEventListener("popstate", read);
    return () => window.removeEventListener("popstate", read);
  }, []);
  const setTab = useCallback((t: Tab) => {
    const url = new URL(window.location.href);
    if (t === "home") url.searchParams.delete("tab");
    else url.searchParams.set("tab", t);
    window.history.pushState(null, "", url);
    setTabState(t);
    window.scrollTo({ top: 0 });
  }, []);
  return [tab, setTab];
}

/** Bottom navigation for phones (hidden from md up, where the whole dashboard fits on one screen). */
export function MobileTabBar({ tab, onChange }: { tab: Tab; onChange: (t: Tab) => void }) {
  // Lifts the chat button above this bar while it is on screen.
  useEffect(() => {
    document.documentElement.classList.add("has-bottom-nav");
    return () => document.documentElement.classList.remove("has-bottom-nav");
  }, []);
  return (
    <nav aria-label="Dashboard sections"
      className="fixed inset-x-0 bottom-0 z-30 border-t-2 border-primary bg-surface/95 px-2 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden dark:border-forest">
      <ul className="mx-auto flex max-w-md items-end justify-between">
        {TABS.map(({ id, label, icon: Icon }) => {
          const active = tab === id;
          if (id === "home") {
            return (
              <li key={id} className="-mt-5 flex flex-1 justify-center">
                <button onClick={() => onChange(id)} aria-current={active ? "page" : undefined} aria-label={label}
                  className={clsx("grid size-14 place-items-center rounded-full border-4 border-bg shadow-lg transition",
                    active ? "bg-forest text-forest-ink" : "bg-primary text-primary-ink")}>
                  <Icon className="size-6" aria-hidden />
                </button>
              </li>
            );
          }
          return (
            <li key={id} className="flex-1">
              <button onClick={() => onChange(id)} aria-current={active ? "page" : undefined}
                className={clsx("flex w-full flex-col items-center gap-0.5 py-2 text-[11px] font-semibold",
                  active ? "text-forest dark:text-primary" : "text-muted")}>
                <span className={clsx("grid h-7 w-11 place-items-center rounded-full", active && "bg-primary/50 dark:bg-forest")}>
                  <Icon className="size-5" aria-hidden />
                </span>
                {label}
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
