"use client";

import { ArrowRight, LayoutDashboard } from "lucide-react";
import Link from "next/link";
import { UserAvatar } from "@/components/Avatar";
import { buttonClass } from "@/components/ui";
import { useSession } from "@/lib/session";

/**
 * The landing page's buttons, which depend on the session: sign in / sign up when signed out, the person's avatar
 * and their dashboard when signed in. `place` picks the size and colours for the header, the hero or the closing
 * band (which sits on deep green).
 */
export function AuthActions({ place }: { place: "header" | "hero" | "band" }) {
  const { status, user } = useSession();
  const header = place === "header";

  if (status === "loading") {
    // Same footprint as the buttons, so the page doesn't shift once the session is known.
    return <span aria-hidden className={header ? "block h-11 w-36 sm:w-44" : "block h-13 w-72"} />;
  }

  // A locked session is still signed in: its dashboard opens on the lock screen.
  if ((status === "active" || status === "locked") && user) {
    const admin = user.role === "admin";
    const home = admin ? "/admin" : "/dashboard";
    const name = user.full_name || user.email;
    if (header) {
      return (
        <div className="flex items-center gap-2 sm:gap-3">
          <Link href={home} className={buttonClass("forest", "md", "max-sm:h-10 max-sm:px-4 max-sm:text-sm")}>
            <LayoutDashboard className="size-4" aria-hidden /> {admin ? "Admin" : "Dashboard"}
          </Link>
          <Link href={home} title={name} aria-label={`${name}, open your dashboard`}
            className="rounded-full ring-2 ring-primary transition hover:brightness-110 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forest">
            <UserAvatar size={44} />
          </Link>
        </div>
      );
    }
    return (
      <div className="flex flex-wrap items-center gap-x-4 gap-y-3">
        <Link href={home} className={buttonClass(place === "band" ? "primary" : "forest", "lg")}>
          {admin ? "Open the admin dashboard" : "Open your dashboard"} <ArrowRight className="size-5" aria-hidden />
        </Link>
        <span className={place === "band" ? "flex items-center gap-2 text-sm text-forest-muted" : "flex items-center gap-2 text-sm text-muted"}>
          <UserAvatar size={28} /> Signed in as {name.split(/[\s@]/)[0]}
        </span>
      </div>
    );
  }

  if (header) {
    return (
      <div className="flex items-center gap-1 sm:gap-2">
        <Link href="/signin" className={buttonClass("ghost", "md", "max-sm:h-10 max-sm:px-3 max-sm:text-sm")}>Sign in</Link>
        <Link href="/signup" className={buttonClass("forest", "md", "max-sm:h-10 max-sm:px-4 max-sm:text-sm")}>Sign up</Link>
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Link href="/signup" className={buttonClass(place === "band" ? "primary" : "forest", "lg")}>
        Create your account <ArrowRight className="size-5" aria-hidden />
      </Link>
      <Link href="/signin" className={buttonClass(place === "band" ? "onDark" : "outline", "lg")}>Sign in</Link>
    </div>
  );
}
