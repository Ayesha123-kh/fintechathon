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

/**
 * Bottom navigation for phones (hidden from md up). The active tab sits in a lime circle that floats in a
 * curved notch cut into the bar; switching tabs slides the notch over while the circle dips and pops back up.
 */
export function MobileTabBar({ tab, onChange }: { tab: Tab; onChange: (t: Tab) => void }) {
  // Lifts the chat button above this bar while it is on screen.
  useEffect(() => {
    document.documentElement.classList.add("has-bottom-nav");
    return () => document.documentElement.classList.remove("has-bottom-nav");
  }, []);
  const index = TABS.findIndex((t) => t.id === tab);
  const ActiveIcon = TABS[index].icon;
  return (
    <nav aria-label="Dashboard sections" style={{ "--i": index } as React.CSSProperties}
      className="tabbar fixed inset-x-0 bottom-0 z-30 md:hidden">
      <div className="relative h-16">
        {/* The bar is three pieces so the notch is a real hole that slides: left fill, notch, right fill. */}
        <div className="tabbar-fill-left" aria-hidden />
        <svg className="tabbar-notch-shape" viewBox="0 0 120 64" preserveAspectRatio="none" aria-hidden>
          <path d="M0 0H14C22 0 25 3 28 8A32 32 0 0 0 92 8C95 3 98 0 106 0H120V64H0Z" />
        </svg>
        <div className="tabbar-fill-right" aria-hidden />
        <span key={tab} className="tabbar-bubble" aria-hidden>
          <ActiveIcon className="size-6" />
        </span>
        <ul className="relative mx-auto grid h-full grid-cols-5">
          {TABS.map(({ id, label, icon: Icon }) => {
            const active = tab === id;
            return (
              <li key={id} className="flex">
                <button onClick={() => onChange(id)} aria-label={label} aria-current={active ? "page" : undefined}
                  className="group flex flex-1 items-center justify-center">
                  <Icon aria-hidden className={clsx("size-6 transition-all duration-300",
                    active ? "-translate-y-6 scale-75 opacity-0" : "text-forest-ink/75 group-active:scale-90")} />
                </button>
              </li>
            );
          })}
        </ul>
      </div>
      <div className="h-[env(safe-area-inset-bottom)] bg-forest" />
    </nav>
  );
}
