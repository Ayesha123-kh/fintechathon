"use client";

import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { LockScreen } from "@/components/LockScreen";
import { api, onLocked, onLoggedOut } from "./api";

export type User = {
  id: string;
  email: string;
  full_name: string;
  role: "user" | "admin";
  onboarding_completed: boolean;
};

type SessionState = {
  status: "loading" | "none" | "active" | "locked";
  user: User | null;
  hasPasskey: boolean;
  idleMinutes: number;
};

type Ctx = SessionState & {
  reload: () => Promise<void>;
  setUser: (u: User) => void;
  lock: () => void;
  signOut: () => Promise<void>;
};

const SessionContext = createContext<Ctx | null>(null);
const PUBLIC = ["/signin", "/signup", "/forgot-password"];

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<SessionState>({ status: "loading", user: null, hasPasskey: false, idleMinutes: 5 });
  const router = useRouter();
  const pathname = usePathname();
  const lastActivity = useRef(Date.now());

  const reload = useCallback(async () => {
    try {
      const s = await api<{ state: string; user?: User; has_passkey?: boolean; idle_lock_minutes?: number }>(
        "/auth/session",
      );
      setState({
        status: (s.state as SessionState["status"]) ?? "none",
        user: s.user ?? null,
        hasPasskey: !!s.has_passkey,
        idleMinutes: s.idle_lock_minutes ?? 5,
      });
    } catch {
      setState((p) => ({ ...p, status: "none", user: null }));
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const lock = useCallback(() => setState((p) => (p.status === "active" ? { ...p, status: "locked" } : p)), []);

  // Server says locked / logged out.
  useEffect(() => onLocked(lock), [lock]);
  useEffect(
    () =>
      onLoggedOut(() => {
        setState((p) => ({ ...p, status: "none", user: null }));
      }),
    [],
  );

  // Banking-app style idle lock: after N minutes without interaction, lock the UI immediately
  // (the server independently refuses requests after the same idle period).
  useEffect(() => {
    if (state.status !== "active") return;
    const bump = () => (lastActivity.current = Date.now());
    const events = ["pointerdown", "keydown", "scroll", "touchstart"] as const;
    events.forEach((e) => window.addEventListener(e, bump, { passive: true }));
    const onVisible = () => {
      if (document.visibilityState === "visible" && Date.now() - lastActivity.current > state.idleMinutes * 60_000) lock();
    };
    document.addEventListener("visibilitychange", onVisible);
    const timer = setInterval(() => {
      if (Date.now() - lastActivity.current > state.idleMinutes * 60_000) lock();
    }, 10_000);
    return () => {
      events.forEach((e) => window.removeEventListener(e, bump));
      document.removeEventListener("visibilitychange", onVisible);
      clearInterval(timer);
    };
  }, [state.status, state.idleMinutes, lock]);

  // Route guard.
  useEffect(() => {
    if (state.status === "loading") return;
    const isPublic = PUBLIC.some((p) => pathname.startsWith(p));
    if (state.status === "none" && !isPublic) router.replace("/signin");
    // Admins only have the admin dashboard; everyone else only has the user app.
    const home = state.user?.role === "admin" ? "/admin" : "/dashboard";
    if ((state.status === "active" || state.status === "locked") && isPublic) router.replace(home);
    if (state.status === "active" && state.user) {
      const inAdmin = pathname.startsWith("/admin");
      if (state.user.role === "admin" && !inAdmin) router.replace("/admin");
      if (state.user.role !== "admin" && inAdmin) router.replace("/dashboard");
    }
  }, [state.status, state.user, pathname, router]);

  const signOut = useCallback(async () => {
    await api("/auth/signout", { method: "POST" }).catch(() => {});
    setState((p) => ({ ...p, status: "none", user: null }));
    router.replace("/signin");
  }, [router]);

  const setUser = useCallback((u: User) => {
    lastActivity.current = Date.now();
    setState((p) => ({ ...p, status: "active", user: u }));
  }, []);

  return (
    <SessionContext.Provider value={{ ...state, reload, setUser, lock, signOut }}>
      {state.status === "locked" ? (
        <LockScreen
          user={state.user}
          hasPasskey={state.hasPasskey}
          onUnlocked={(u) => setUser(u)}
          onSignOut={signOut}
        />
      ) : (
        children
      )}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession outside SessionProvider");
  return ctx;
}
