"use client";

import clsx from "clsx";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Logo } from "./ui";

export type Section = "home" | "goals" | "spending" | "banks" | "deals" | "activity";
type Item = { id: Section; label: string; href?: string };

/** Laptops (sidebar) and tablets (bottom bar): the dashboard's sections, which they scroll to. */
const SECTIONS: Item[] = [
  { id: "home", label: "Home" },
  { id: "goals", label: "Goals" },
  { id: "spending", label: "Spending" },
  { id: "banks", label: "Banks" },
  { id: "deals", label: "Deals" },
];

/**
 * Phones: one page per item, Home in the middle. Home holds the balance and the banks; goals, spending, deals and
 * recent activity each have their own page.
 */
const PHONE: Required<Item>[] = [
  { id: "goals", label: "Goals", href: "/goals" },
  { id: "spending", label: "Spending", href: "/spending" },
  { id: "home", label: "Home", href: "/dashboard" },
  { id: "deals", label: "Deals", href: "/deals" },
  { id: "activity", label: "Activity", href: "/activity" },
];

/*
  Phone page transitions (about 1 s in all). Tapping an item slides the peach highlight over to it while the
  current page dims slightly (html.page-leaving); then it navigates and the next page's AppShell, seeing
  navTransitionPending(), fades the new page in.
*/
const LEAVE_MS = 350; // highlight slide + dim before the next page opens
let tappedAt = -Infinity;
/**
 * True for the page that a bottom-nav tap opened (read by AppShell and the nav when they mount). It is a time
 * window rather than a one-shot flag so mounting twice (React's development double-mount) still sees it.
 */
export function navTransitionPending(): boolean {
  return performance.now() - tappedAt < 2000;
}

/** Phones: narrower than the `sm` breakpoint (640px). */
export function usePhone(): boolean {
  const [phone, setPhone] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 639px)");
    const update = () => setPhone(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);
  return phone;
}

/**
 * Which section to highlight. On a section's own page (/goals etc.) that section; on the dashboard, phones
 * highlight Home and wider screens the section on screen. The dashboard is one scrolling page: each section is
 * an element with id="goals" etc., and the last one whose top has passed a third of the viewport is the active one.
 */
function useActiveSection(): Section | null {
  const pathname = usePathname();
  const phone = usePhone();
  // Phones show sections on their own pages, so on the dashboard they always highlight Home.
  const onDashboard = pathname === "/dashboard" && !phone;
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
  const page = PHONE.find(({ id, href }) => id !== "home" && pathname.startsWith(href));
  return page ? page.id : pathname === "/dashboard" ? "home" : null;
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
      <Link href="/dashboard" aria-label="Paisave home" className="mb-8 px-2 pt-2">
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
 * On phones each item opens that section's own page; on tablets it scrolls the dashboard.
 * It reserves its height through --bottom-nav so page content and the chat button stay clear of it.
 */
export function BottomNav() {
  const active = useActiveSection();
  const phone = usePhone();
  const router = useRouter();
  // The highlight moves to the tapped item at once, before its page has opened.
  const [popped, setPopped] = useState<Section | null>(null);
  const selected = popped ?? active;
  const items: Item[] = phone ? PHONE : SECTIONS;
  const selectedIndex = items.findIndex(({ id }) => id === selected);
  const go = (e: React.MouseEvent, id: Section, href: string) => {
    if (active === id || e.metaKey || e.ctrlKey || e.shiftKey || e.button !== 0) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return; // plain navigation
    e.preventDefault();
    setPopped(id);
    document.documentElement.classList.add("page-leaving");
    tappedAt = performance.now();
    setTimeout(() => router.push(href), LEAVE_MS);
    // Safety net: never leave the page dimmed if the navigation doesn't happen.
    setTimeout(() => document.documentElement.classList.remove("page-leaving"), 2500);
  };
  useEffect(() => {
    document.documentElement.classList.add("has-bottom-nav");
    return () => document.documentElement.classList.remove("has-bottom-nav");
  }, []);
  return (
    <>
      {/* Phones: a frosted strip behind the floating bar, so content scrolling underneath is blurred rather than readable. */}
      <div aria-hidden
        className="pointer-events-none fixed inset-x-0 bottom-0 z-30 h-[calc(var(--bottom-nav)+1.75rem)] bg-bg/70 backdrop-blur-lg [mask-image:linear-gradient(to_top,black_70%,transparent)] sm:hidden" />
      <nav aria-label="Dashboard sections"
        className="fixed inset-x-3 bottom-[max(0.75rem,env(safe-area-inset-bottom))] z-40 sm:inset-x-auto sm:left-1/2 sm:-translate-x-1/2 lg:hidden">
        <ul className="relative flex h-16 items-center gap-1 rounded-full bg-side p-2 shadow-lg shadow-black/10">
          {/* Phones: one peach highlight that slides to the selected item (the five items share the width equally). */}
          {phone && selectedIndex >= 0 && (
            <li aria-hidden className="nav-slider absolute top-2 bottom-2 left-2 rounded-full bg-primary"
              style={{ "--i": selectedIndex } as React.CSSProperties} />
          )}
          {items.map(({ id, label, href = "/dashboard" }) => (
            <li key={id} className="min-w-0 flex-1 basis-0 sm:flex-none sm:basis-auto">
              {phone ? (
                <Link href={href} aria-current={active === id ? "page" : undefined} onClick={(e) => go(e, id, href)}
                  className={clsx("relative flex h-12 items-center justify-center rounded-full px-1 text-[13px] whitespace-nowrap transition-colors duration-300",
                  selected === id ? "font-semibold text-primary-ink" : "text-side-ink hover:text-forest-ink")}>
                  {label}
                </Link>
              ) : (
                <SectionLink id={id} className={navItem(active === id)}>
                  <span aria-current={active === id ? "page" : undefined}>{label}</span>
                </SectionLink>
              )}
            </li>
          ))}
        </ul>
      </nav>
    </>
  );
}

const navItem = (on: boolean) =>
  clsx("flex h-12 items-center justify-center rounded-full px-2 text-[13px] whitespace-nowrap transition sm:px-6 sm:text-base",
    on ? "bg-primary font-semibold text-primary-ink" : "text-side-ink hover:text-forest-ink");
