"use client";

import clsx from "clsx";
import { Bell, Fingerprint, FlaskConical, LogOut, Monitor, Moon, Shield, Sun, X } from "lucide-react";
import Link from "next/link";
import { Suspense, useCallback, useEffect, useState } from "react";
import useSWR from "swr";
import { api, errorText, fetcher } from "@/lib/api";
import { passkeySupported, registerPasskey } from "@/lib/passkey";
import { currentSubscription, disablePush, enablePush, pushSupported } from "@/lib/push";
import { useSession } from "@/lib/session";
import { applyTheme, getTheme, type ThemeChoice } from "@/lib/theme";
import { ChatWidget } from "./ChatWidget";
import { EmailSettings } from "./EmailSettings";
import { BottomNav, Sidebar } from "./SectionNav";
import { Button, Logo, Spinner } from "./ui";

/** Open the settings sheet from anywhere, optionally scrolled to a section. */
export function openSettings(section?: "email") {
  window.dispatchEvent(new CustomEvent("bachat:open-settings", { detail: section }));
}

type EmailResult = { connected?: boolean; error?: string };

export function AppShell({ children, onChatActivity }: { children: React.ReactNode; onChatActivity?: () => void }) {
  const { status, user } = useSession();
  const [sheet, setSheet] = useState<"" | "settings">("");
  const [settingsClosing, setSettingsClosing] = useState(false);
  const settingsShown = sheet === "settings" && !settingsClosing;
  const [emailResult, setEmailResult] = useState<EmailResult | undefined>();

  // The Gmail sign-in returns to /dashboard?settings=email&connected=1 (or &error=...).
  useEffect(() => {
    const q = new URLSearchParams(window.location.search);
    if (q.get("settings") === "email") {
      setEmailResult({ connected: q.has("connected"), error: q.get("error") ?? undefined });
      setSheet("settings");
      window.history.replaceState(null, "", window.location.pathname);
    }
    const open = () => {
      window.dispatchEvent(new Event("bachat:close-chat"));
      setSheet("settings");
    };
    window.addEventListener("bachat:open-settings", open);
    return () => window.removeEventListener("bachat:open-settings", open);
  }, []);
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
        text: msg.startsWith("connect_gmail_first") ? "Connect a Gmail inbox in Settings first."
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
  const first = (user.full_name || user.email).split(/[\s@]/)[0];
  const month = new Date().toLocaleDateString("en-GB", { month: "long", year: "numeric" });
  const toggleSettings = () => {
    if (settingsShown) return window.dispatchEvent(new Event("bachat:close-sheet"));
    window.dispatchEvent(new Event("bachat:close-chat")); // only one panel open at a time
    setSheet("settings");
  };
  const datePill = (
    <span className="inline-flex h-11 items-center rounded-full bg-surface px-5 text-[15px] text-ink">{month}</span>
  );
  return (
    <div className="mx-auto flex min-h-dvh max-w-[100rem] gap-6 p-4 sm:p-5 lg:gap-8">
      <Sidebar />
      <div className="min-w-0 flex-1 pb-[calc(var(--bottom-nav)+5.5rem)] lg:pb-28">
        <header className="flex items-center gap-3 pt-1 pb-5 sm:pb-6 lg:pt-0">
          {/* The logo lives in the sidebar on laptops; phones and tablets show it next to the greeting. */}
          <Link href="/dashboard" aria-label="Saving home" className="lg:hidden">
            <span className="sm:hidden"><Logo size={44} withName={false} /></span>
            <span className="hidden sm:inline"><Logo size={52} withName={false} tone="forest" /></span>
          </Link>
          <div className="min-w-0 flex-1">
            <p className="text-sm text-muted sm:text-base">Assalam o Alaikum,</p>
            {/* The signed-in user's own first name. */}
            <p className="truncate text-2xl leading-tight font-bold tracking-tight text-ink sm:text-[1.75rem] lg:text-4xl">{first}</p>
          </div>
          {me?.test_tools && (
            <button onClick={sendTestAlert} disabled={sending} aria-label="Send a test bank email" title="Send a test bank email"
              className="inline-flex h-11 items-center gap-2 rounded-full px-3 text-sm font-semibold text-ink-2 hover:bg-hover disabled:opacity-50">
              <FlaskConical className={clsx("size-5", sending && "animate-pulse")} aria-hidden />
              <span className="hidden xl:inline">Test bank email</span>
            </button>
          )}
          <span className="hidden lg:inline-flex">{datePill}</span>
          <button onClick={toggleSettings}
            aria-label={settingsShown ? "Close settings" : "Account and settings"} aria-expanded={settingsShown}
            title={user.full_name || user.email}
            className="relative grid size-12 shrink-0 place-items-center rounded-full bg-forest text-[15px] font-bold tracking-wide text-forest-ink transition hover:brightness-110 lg:size-14 lg:text-lg">
            <span aria-hidden className={clsx("transition-all duration-300", settingsShown && "scale-50 -rotate-90 opacity-0")}>
              {initials(user.full_name || user.email)}
            </span>
            <X aria-hidden className={clsx("absolute size-5 transition-all duration-300",
              settingsShown ? "scale-100 rotate-0 opacity-100" : "scale-50 rotate-90 opacity-0")} />
          </button>
        </header>
        <div className="-mt-1 mb-5 sm:hidden">{datePill}</div>

        <main>{children}</main>
      </div>

      <BottomNav />

      <Suspense>
        <ChatWidget onActivity={onChatActivity} />
      </Suspense>

      {toast && (
        <div role="status" className={clsx(
          "fixed inset-x-4 top-4 z-50 mx-auto max-w-md rounded-2xl px-4 py-3 text-sm shadow-lg",
          toast.error ? "bg-danger text-white" : "bg-forest text-forest-ink")}>
          {toast.text}
        </div>
      )}

      {sheet && (
        <Sheet title="Settings" onClose={() => { setSheet(""); setSettingsClosing(false); }}
          onClosing={() => setSettingsClosing(true)}>
          <SettingsPanel emailResult={emailResult} />
        </Sheet>
      )}
    </div>
  );
}

function Sheet({ title, onClose, onClosing, children }: {
  title: string; onClose: () => void; onClosing?: () => void; children: React.ReactNode;
}) {
  const [closing, setClosing] = useState(false);
  const close = useCallback(() => {
    setClosing(true);
    onClosing?.();
    setTimeout(onClose, 170);
  }, [onClose, onClosing]);
  useEffect(() => {
    window.addEventListener("bachat:close-sheet", close);
    return () => window.removeEventListener("bachat:close-sheet", close);
  }, [close]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [close]);
  return (
    // A panel that opens from the avatar in the top-right corner.
    <div className="fixed inset-0 z-50" role="dialog" aria-label={title}>
      <div className={clsx("absolute inset-0 touch-none bg-ink/30", closing && "fade-closing")} onClick={close} />
      <div className={clsx("pop-tr absolute top-[4.75rem] right-3 left-3 sm:left-auto sm:w-96 lg:top-[5.5rem] lg:right-5", closing && "is-closing")}>
        <div className="max-h-[calc(100dvh-6rem)] overflow-y-auto overscroll-contain rounded-[var(--radius-card)] bg-surface p-5 shadow-2xl">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold">{title}</h2>
            <button onClick={close} aria-label="Close" className="grid size-9 place-items-center rounded-full hover:bg-hover">
              <X className="size-5" />
            </button>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}

function SettingsPanel({ emailResult }: { emailResult?: EmailResult }) {
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
      <div className="rounded-2xl bg-surface-2 p-4">
        <p className="font-semibold">{user?.full_name}</p>
        <p className="text-sm text-muted">{user?.email}</p>
      </div>
      <EmailSettings result={emailResult} />
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
      {user?.role === "admin" && (
        <Link href="/admin" className="flex w-full items-center gap-2 rounded-full border border-line px-5 py-2.5 text-[15px] font-semibold hover:bg-hover">
          <Shield className="size-5" aria-hidden /> Admin dashboard
        </Link>
      )}
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

function initials(name: string): string {
  const parts = name.replace(/@.*/, "").split(/[\s._-]+/).filter(Boolean);
  const letters = parts.length > 1 ? parts[0][0] + parts[parts.length - 1][0] : (parts[0] ?? "?").slice(0, 2);
  return letters.toUpperCase();
}
