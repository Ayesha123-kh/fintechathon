"use client";

import clsx from "clsx";
import {
  Bot, Building2, CreditCard, Landmark, LayoutDashboard, ListChecks, Tag, TrendingUp, Users, Wallet,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

type Item = { href: string; label: string; icon: typeof Users };

/** The admin dashboard's pages, grouped for the sidebar. Each is its own route under /admin. */
export const ADMIN_NAV: { title: string; items: Item[] }[] = [
  { title: "Dashboard", items: [{ href: "/admin", label: "Overview", icon: LayoutDashboard }] },
  {
    title: "People and agents",
    items: [
      { href: "/admin/users", label: "Users", icon: Users },
      { href: "/admin/agents", label: "Agents", icon: Bot },
      { href: "/admin/plans", label: "Plans", icon: Wallet },
    ],
  },
  {
    title: "Deals",
    items: [
      { href: "/admin/deals", label: "Deals", icon: Tag },
      { href: "/admin/companies", label: "Companies", icon: Building2 },
    ],
  },
  {
    title: "Banking",
    items: [
      { href: "/admin/banks", label: "Banks", icon: Landmark },
      { href: "/admin/cards", label: "Cards", icon: CreditCard },
    ],
  },
  {
    title: "Markets",
    items: [
      { href: "/admin/assets", label: "Tracked assets", icon: TrendingUp },
      { href: "/admin/watchlists", label: "Watchlists", icon: ListChecks },
    ],
  },
];

function useActive() {
  const pathname = usePathname();
  return (href: string) => (href === "/admin" ? pathname === "/admin" : pathname === href || pathname.startsWith(href + "/"));
}

/** Laptops: the left sidebar. */
export function AdminSidebar() {
  const isActive = useActive();
  return (
    <nav aria-label="Admin" className="space-y-5 pb-6">
      {ADMIN_NAV.map((group) => (
        <div key={group.title}>
          <p className="mb-1.5 px-3 text-xs font-semibold tracking-wide text-muted uppercase">{group.title}</p>
          <ul className="space-y-0.5">
            {group.items.map(({ href, label, icon: Icon }) => (
              <li key={href}>
                <Link href={href} aria-current={isActive(href) ? "page" : undefined}
                  className={clsx("flex items-center gap-3 rounded-full px-3 py-2 text-sm font-semibold transition",
                    isActive(href) ? "bg-forest text-forest-ink" : "text-ink-2 hover:bg-hover")}>
                  <Icon className="size-[18px] shrink-0" aria-hidden /> {label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}

/** Phones: a sidebar would eat the screen, so the same pages become a scrolling strip above the content. */
export function AdminTabs() {
  const isActive = useActive();
  return (
    <nav aria-label="Admin" className="-mx-4 mb-5 flex gap-2 overflow-x-auto px-4 pb-1 md:hidden">
      {ADMIN_NAV.flatMap((g) => g.items).map(({ href, label, icon: Icon }) => (
        <Link key={href} href={href} aria-current={isActive(href) ? "page" : undefined}
          className={clsx("inline-flex shrink-0 items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold",
            isActive(href) ? "bg-forest text-forest-ink" : "bg-surface text-ink-2")}>
          <Icon className="size-4" aria-hidden /> {label}
        </Link>
      ))}
    </nav>
  );
}
