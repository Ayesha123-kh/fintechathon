"use client";

import clsx from "clsx";
import { Bell, Fingerprint, FlaskConical, LayoutDashboard, LogOut, Mail, Monitor, Moon, Settings2, Shield, Sun, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import useSWR from "swr";
import { api, errorText, fetcher } from "@/lib/api";
import { passkeySupported, registerPasskey } from "@/lib/passkey";
import { currentSubscription, disablePush, enablePush, pushSupported } from "@/lib/push";
import { useSession } from "@/lib/session";
import { applyTheme, getTheme, type ThemeChoice } from "@/lib/theme";
import { ChatWidget } from "./ChatWidget";
import { Button, Logo, Spinner } from "./ui";

const NAV = [
  { href: "/dashboard", label: "Home", icon: LayoutDashboard },
  { href: "/email", label: "Email", icon: Mail },
];

export function AppShell({ children, onChatActivity }: { children: React.ReactNode; onChatActivity?: () => void }) {
  const { status, user } = useSession();
  const pathname = usePathname();
  const [sheet, setSheet] = useState<"" | "settings" | "notifications">("");
  const { data: me } = useSWR<{ test_tools?: boolean }>(status === "active" ? "/me" : null, fetcher);
  const [toast, setToast] = useState<{ text: string; error?: boolean } | null>(null);
  const [sending, setSending] = useState(false);

  const sendTestAlert = async () => {
    setSending(true);
    try {
      const r = await api<{ bank: string; direction: string; amount: number; merchant: string; sent_to: string[] }>(
        "/dev/test-alert", { method: "POST" });
      setToast({ text: `Sent a ${r.bank} ${r.direction} alert of Rs. ${r.amount.toLocaleString("en-PK")} to ${r.sent_to.join(", ")}. It will appear here within a minute.` });
    } catch (e) {
      const msg = errorText(e);
      setToast({
        error: true,
        text: msg.startsWith("connect_gmail_first") ? "Connect a Gmail inbox on the Email screen first."
          : msg.startsWith("smtp_not_configured") ? "Add SMTP_USERNAME and SMTP_PASSWORD to backend/.env to send test emails."
            : msg.startsWith("add_a_bank_first") ? "Add a bank account in chat first." : msg,
      });
    } finally {
      setSending(false);
      setTimeout(() => setToast(null), 7000);
    }
  };

  if (status !== "active" || !user) {
    return (
      <main className="grid min-h-dvh place-items-center">
        <Spinner />
      </main>
    );
  }
  const nav = user.role === "admin" ? [...NAV, { href: "/admin", label: "Admin", icon: Shield }] : NAV;

  return (
    <div className="min-h-dvh pb-24 md:pb-10">
      <header className="sticky top-0 z-30 border-b border-line/60 bg-bg/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4">
          <Link href="/dashboard" aria-label="Home">
            <Logo size={34} />
          </Link>
          <nav className="ml-6 hidden gap-1 md:flex" aria-label="Main">
            {nav.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={clsx(
                  "inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold",
                  pathname.startsWith(href) ? "bg-forest text-forest-ink" : "text-ink-2 hover:bg-hover",
                )}
              >
                <Icon className="size-4" aria-hidden /> {label}
              </Link>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-1">
            {me?.test_tools && (
              <button onClick={sendTestAlert} disabled={sending} aria-label="Send a test bank email" title="Send a test bank email"
                className="inline-flex h-10 items-center gap-2 rounded-full px-3 text-sm font-semibold text-ink-2 hover:bg-hover disabled:opacity-50">
                <FlaskConical className={clsx("size-5", sending && "animate-pulse")} aria-hidden />
                <span className="hidden lg:inline">Test bank email</span>
              </button>
            )}
            <button onClick={() => setSheet("notifications")} aria-label="Notifications"
              className="grid size-10 place-items-center rounded-full hover:bg-hover">
              <Bell className="size-5" />
            </button>
            <button onClick={() => setSheet("settings")} aria-label="Settings"
              className="grid size-10 place-items-center rounded-full hover:bg-hover">
              <Settings2 className="size-5" />
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 pt-5">{children}</main>

      <nav aria-label="Main" className="safe-bottom fixed inset-x-0 bottom-0 z-30 border-t border-line bg-surface/95 px-6 pt-2 backdrop-blur md:hidden">
        <div className="mx-auto flex max-w-md justify-between">
          {nav.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href}
              className={clsx("flex w-16 flex-col items-center gap-1 rounded-2xl py-1.5 text-[11px] font-semibold",
                pathname.startsWith(href) ? "text-forest dark:text-primary" : "text-muted")}>
              <span className={clsx("grid h-8 w-12 place-items-center rounded-full", pathname.startsWith(href) && "bg-primary/40")}>
                <Icon className="size-5" aria-hidden />
              </span>
              {label}
            </Link>
          ))}
        </div>
      </nav>

      <Suspense>
        <ChatWidget onActivity={onChatActivity} />
      </Suspense>

      {toast && (
        <div role="status" className={clsx(
          "fixed inset-x-4 top-20 z-50 mx-auto max-w-md rounded-2xl px-4 py-3 text-sm shadow-lg",
          toast.error ? "bg-danger text-white" : "bg-forest text-forest-ink")}>
          {toast.text}
        </div>
      )}

      {sheet && (
        <Sheet title={sheet === "settings" ? "Settings" : "Notifications"} onClose={() => setSheet("")}>
          {sheet === "settings" ? <SettingsPanel /> : <NotificationsPanel />}
        </Sheet>
      )}
    </div>
  );
}

function Sheet({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center md:items-start md:justify-end" role="dialog" aria-label={title}>
      <div className="absolute inset-0 bg-ink/30" onClick={onClose} />
      <div className="safe-bottom relative max-h-[85dvh] w-full overflow-y-auto rounded-t-[1.75rem] bg-surface p-5 md:mt-16 md:mr-4 md:w-96 md:rounded-[1.75rem]">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold">{title}</h2>
          <button onClick={onClose} aria-label="Close" className="grid size-9 place-items-center rounded-full hover:bg-hover">
            <X className="size-5" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function SettingsPanel() {
  const { user, signOut, reload, hasPasskey } = useSession();
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState("");
  const [pushOn, setPushOn] = useState<boolean | null>(null);

  useEffect(() => {
    currentSubscription().then((s) => setPushOn(!!s)).catch(() => setPushOn(false));
  }, []);

  const addPasskey = async () => {
    setBusy("passkey");
    setMsg("");
    try {
      await registerPasskey();
      await reload();
      setMsg("Fingerprint / face sign-in is on for this device.");
    } catch (e) {
      setMsg(e instanceof Error && e.name === "NotAllowedError" ? "Cancelled." : errorText(e));
    } finally {
      setBusy("");
    }
  };

  const togglePush = async () => {
    setBusy("push");
    setMsg("");
    try {
      if (pushOn) {
        await disablePush();
        setPushOn(false);
      } else {
        const r = await enablePush();
        if (r === "granted") {
          setPushOn(true);
          await api("/push/test", { method: "POST" });
        } else
          setMsg(
            r === "denied" ? "Notifications are blocked in your browser settings."
              : r === "unconfigured" ? "Push isn't configured on the server yet."
                : "Install the app to your home screen to get notifications on this device.",
          );
      }
    } catch (e) {
      setMsg(errorText(e));
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border-2 border-primary bg-surface-2 p-4">
        <p className="font-semibold">{user?.full_name}</p>
        <p className="text-sm text-muted">{user?.email}</p>
      </div>
      {passkeySupported() && (
        <Button variant="outline" className="w-full justify-start" onClick={addPasskey} loading={busy === "passkey"}>
          <Fingerprint className="size-5" aria-hidden />
          {hasPasskey ? "Add fingerprint / face on this device" : "Turn on fingerprint / face sign-in"}
        </Button>
      )}
      {pushSupported() && (
        <Button variant="outline" className="w-full justify-start" onClick={togglePush} loading={busy === "push"}>
          <Bell className="size-5" aria-hidden />
          {pushOn ? "Turn off notifications on this device" : "Turn on notifications"}
        </Button>
      )}
      <ThemePicker />
      <p className="text-xs text-muted">
        Everything else, like your banks, goals, savings rule, language, sadqah reminders or the investment board,
        is changed by telling your assistant in the chat.
      </p>
      {msg && <p className="rounded-2xl bg-primary/30 px-4 py-3 text-sm">{msg}</p>}
      <Button variant="ghost" className="w-full justify-start text-danger" onClick={signOut}>
        <LogOut className="size-5" aria-hidden /> Sign out
      </Button>
    </div>
  );
}

type Note = { id: string; kind: string; title: string; body: string; url: string; read: boolean; created_at: string };

function NotificationsPanel() {
  const { data, mutate } = useSWR<Note[]>("/notifications", fetcher);
  const markRead = useCallback(async () => {
    await api("/notifications/read", { method: "POST" }).catch(() => {});
    mutate();
  }, [mutate]);
  useEffect(() => {
    const t = setTimeout(markRead, 1500);
    return () => clearTimeout(t);
  }, [markRead]);
  if (!data) return <Spinner />;
  if (!data.length) return <p className="py-6 text-center text-sm text-muted">No notifications yet.</p>;
  return (
    <ul className="space-y-2">
      {data.map((n) => (
        <li key={n.id}>
          <Link href={n.url} className={clsx("block rounded-2xl p-3.5", n.read ? "bg-surface-2/60" : "bg-primary/25")}>
            <p className="text-sm font-semibold">{n.title}</p>
            <p className="mt-0.5 text-sm text-ink-2">{n.body}</p>
            <p className="mt-1 text-[11px] text-muted">{new Date(n.created_at).toLocaleString()}</p>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function ThemePicker() {
  const [theme, setTheme] = useState<ThemeChoice>("system");
  useEffect(() => setTheme(getTheme()), []);
  const options: { id: ThemeChoice; label: string; icon: typeof Sun }[] = [
    { id: "light", label: "Light", icon: Sun },
    { id: "dark", label: "Dark", icon: Moon },
    { id: "system", label: "Device", icon: Monitor },
  ];
  return (
    <div>
      <p className="mb-2 text-sm font-medium text-ink-2">Appearance</p>
      <div role="radiogroup" aria-label="Appearance" className="grid grid-cols-3 gap-1 rounded-full bg-surface-2 p-1">
        {options.map(({ id, label, icon: Icon }) => (
          <button key={id} role="radio" aria-checked={theme === id}
            onClick={() => { applyTheme(id); setTheme(id); }}
            className={clsx("inline-flex h-9 items-center justify-center gap-1.5 rounded-full text-sm font-semibold transition",
              theme === id ? "bg-forest text-forest-ink" : "text-ink-2 hover:bg-hover")}>
            <Icon className="size-4" aria-hidden /> {label}
          </button>
        ))}
      </div>
    </div>
  );
}
