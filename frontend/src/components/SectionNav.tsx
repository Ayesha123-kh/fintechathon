"use client";

import clsx from "clsx";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { Logo } from "./ui";

export type Section = "home" | "goals" | "spending" | "banks" | "deals";
const SECTIONS: { id: Section; label: string }[] = [
  { id: "home", label: "Home" },
  { id: "goals", label: "Goals" },
  { id: "spending", label: "Spending" },
  { id: "banks", label: "Banks" },
  { id: "deals", label: "Deals" },
];

/**
 * Which dashboard section is on screen. The dashboard is one scrolling page: each section is an element with
 * id="goals" etc., and the last one whose top has passed a third of the viewport is the active one.
 */
function useActiveSection(): Section | null {
  const pathname = usePathname();
  const onDashboard = pathname === "/dashboard";
  const [active, setActive] = useState<Section>("home");
  useEffect(() => {
    if (!onDashboard) return;
    const update = () => {
      const line = window.innerHeight / 3;
      const atBottom = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4;
      let current: Section = "home";
      for (const { id } of SECTIONS.slice(1)) {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top <= line) current = id;
      }
      // A short last section can never reach the line: count reaching the bottom of the page as arriving there.
      if (atBottom && window.scrollY > 0) {
        const last = [...SECTIONS].reverse().find(({ id }) => document.getElementById(id));
        if (last) current = last.id;
      }
      setActive(current);
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, [onDashboard]);
  if (onDashboard) return active;
  return pathname.startsWith("/goals") ? "goals" : null;
}

/** On the dashboard, scroll smoothly to the section; anywhere else, go to the dashboard at that section. */
function SectionLink({ id, className, children }: { id: Section; className: string; children: React.ReactNode }) {
  const pathname = usePathname();
  const href = id === "home" ? "/dashboard" : `/dashboard#${id}`;
  return (
    <Link href={href} className={className}
      onClick={(e) => {
        if (pathname !== "/dashboard") return;
        e.preventDefault();
        const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        const behavior: ScrollBehavior = reduce ? "auto" : "smooth";
        if (id === "home") window.scrollTo({ top: 0, behavior });
        else document.getElementById(id)?.scrollIntoView({ behavior, block: "start" });
      }}>
      {children}
    </Link>
  );
}

/** Laptops: the dark sidebar with the logo, the sections and the sadqah reminder at the bottom. */
export function Sidebar() {
  const active = useActiveSection();
  const friday = new Date().getDay() === 5;
  return (
    <aside className="sticky top-5 hidden h-[calc(100dvh-2.5rem)] w-60 shrink-0 flex-col rounded-[2rem] bg-side p-5 lg:flex xl:w-64">
      <Link href="/dashboard" aria-label="Saving home" className="mb-8 px-2 pt-2">
        <Logo size={44} nameClassName="text-forest-ink" />
      </Link>
      <nav aria-label="Dashboard sections">
        <ul className="space-y-1.5">
          {SECTIONS.map(({ id, label }) => (
            <li key={id}>
              <SectionLink id={id}
                className={clsx("flex h-12 items-center rounded-2xl px-5 text-[17px] transition",
                  active === id ? "bg-primary font-semibold text-primary-ink" : "text-side-ink hover:bg-side-2 hover:text-forest-ink")}>
                <span aria-current={active === id ? "page" : undefined}>{label}</span>
              </SectionLink>
            </li>
          ))}
        </ul>
      </nav>
      <Link href="?chat=1" className="mt-auto block rounded-2xl bg-side-2 p-4 transition hover:brightness-110">
        <p className="text-sm text-side-ink">Sadqah reminder</p>
        <p className="mt-1 font-semibold leading-snug text-forest-ink">
          {friday ? "It's Friday. A small sadqah today?" : "Friday is near. Plan a small sadqah?"}
        </p>
      </Link>
    </aside>
  );
}

/**
 * Phones and tablets: a dark pill fixed to the bottom of the screen (full width on phones, centred on tablets).
 * It reserves its height through --bottom-nav so page content and the chat button stay clear of it.
 */
export function BottomNav() {
  const active = useActiveSection();
  useEffect(() => {
    document.documentElement.classList.add("has-bottom-nav");
    return () => document.documentElement.classList.remove("has-bottom-nav");
  }, []);
  return (
    <nav aria-label="Dashboard sections"
      className="fixed inset-x-3 bottom-[max(0.75rem,env(safe-area-inset-bottom))] z-30 sm:inset-x-auto sm:left-1/2 sm:-translate-x-1/2 lg:hidden">
      <ul className="flex h-16 items-center gap-1 rounded-full bg-side p-2 shadow-lg shadow-black/10">
        {SECTIONS.map(({ id, label }) => (
          <li key={id} className="flex-1 sm:flex-none">
            <SectionLink id={id}
              className={clsx("flex h-12 items-center justify-center rounded-full px-2 text-[13px] whitespace-nowrap transition sm:px-6 sm:text-base",
                active === id ? "bg-primary font-semibold text-primary-ink" : "text-side-ink hover:text-forest-ink")}>
              <span aria-current={active === id ? "page" : undefined}>{label}</span>
            </SectionLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
