"use client";

import clsx from "clsx";
import { Bell, Fingerprint, FlaskConical, MessageCircle, LogOut, Monitor, Moon, Shield, Sun, X } from "lucide-react";
import Link from "next/link";
import { Suspense, useCallback, useEffect, useState } from "react";
import useSWR from "swr";
import { api, errorText, fetcher } from "@/lib/api";
import { passkeySupported, registerPasskey } from "@/lib/passkey";
import { currentSubscription, disablePush, enablePush, pushSupported } from "@/lib/push";
import { useSession } from "@/lib/session";
import { applyTheme, getTheme, type ThemeChoice } from "@/lib/theme";
import { DropTail } from "./DropTail";
import { ChatWidget } from "./ChatWidget";
import { EmailSettings } from "./EmailSettings";
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
  return (
    <div className="min-h-dvh pb-10">
      <header className="sticky top-0 z-30 border-b border-line/60 bg-bg/85 backdrop-blur">
        {/* Phones: avatar left, logo centred, chat on the right. Laptops: logo left, actions and avatar right. */}
        <div className="relative mx-auto flex h-16 max-w-6xl items-center gap-4 px-4">
          <Link href="/dashboard" aria-label="Home" className="max-md:absolute max-md:left-1/2 max-md:-translate-x-1/2">
            <Logo size={34} />
          </Link>
          <div className="ml-auto flex items-center gap-1">
            {me?.test_tools && (
              <button onClick={sendTestAlert} disabled={sending} aria-label="Send a test bank email" title="Send a test bank email"
                className="inline-flex h-10 items-center gap-2 rounded-full px-3 text-sm font-semibold text-ink-2 hover:bg-hover disabled:opacity-50">
                <FlaskConical className={clsx("size-5", sending && "animate-pulse")} aria-hidden />
                <span className="hidden lg:inline">Test bank email</span>
              </button>
            )}
            <HeaderChatButton />
          </div>
          {/* Phones: the avatar morphs into a cross while settings is open and closes it on tap. */}
          <button
            onClick={() => {
              if (settingsShown) return window.dispatchEvent(new Event("bachat:close-sheet"));
              window.dispatchEvent(new Event("bachat:close-chat")); // only one drop-down open at a time
              setSheet("settings");
            }}
            aria-label={settingsShown ? "Close settings" : "Account and settings"} aria-expanded={settingsShown}
            title={user.full_name || user.email}
            className="relative grid size-10 shrink-0 place-items-center rounded-full bg-forest text-sm font-bold tracking-wide text-forest-ink ring-2 ring-primary transition hover:brightness-110 max-md:order-first md:-ml-3">
            <span aria-hidden className={clsx("transition-all duration-300",
              settingsShown && "max-md:scale-50 max-md:-rotate-90 max-md:opacity-0")}>
              {initials(user.full_name || user.email)}
            </span>
            <X aria-hidden className={clsx("absolute size-5 transition-all duration-300 md:hidden",
              settingsShown ? "scale-100 rotate-0 opacity-100" : "scale-50 rotate-90 opacity-0")} />
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 pt-5">{children}</main>


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
    // Phones: drops down from the avatar, below the top bar. Laptops: a panel under the avatar on the right.
    <div className="fixed inset-x-0 top-16 bottom-0 z-50 flex items-start justify-center px-3 pt-2.5 md:inset-0 md:justify-end md:p-0"
      role="dialog" aria-label={title}>
      <div className={clsx("absolute inset-0 touch-none bg-ink/30", closing && "fade-closing")} onClick={close} />
      <div className={clsx("drop-tl relative w-full md:mt-16 md:mr-4 md:w-96", closing && "is-closing")}>
        <DropTail className="left-[10px]" fill="fill-surface" stroke="stroke-primary dark:stroke-forest" />
        <div className="max-h-[calc(100dvh-6rem)] overflow-y-auto overscroll-contain rounded-[1.75rem] max-md:rounded-tl-xl border-2 border-primary bg-surface p-5 dark:border-forest md:max-h-[85dvh]">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold">{title}</h2>
            <button onClick={close} aria-label="Close" className="grid size-9 place-items-center rounded-full hover:bg-hover max-md:hidden">
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
      <div className="rounded-2xl border-2 border-forest dark:border-primary bg-surface-2 p-4">
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

/** Phones only: toggles the chat (ChatWidget), shows the unread count and morphs into a cross while open. */
function HeaderChatButton() {
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const onUnread = (e: Event) => setUnread(Number((e as CustomEvent).detail) || 0);
    const onState = (e: Event) => setOpen(Boolean((e as CustomEvent).detail));
    window.addEventListener("bachat:chat-unread", onUnread);
    window.addEventListener("bachat:chat-state", onState);
    return () => {
      window.removeEventListener("bachat:chat-unread", onUnread);
      window.removeEventListener("bachat:chat-state", onState);
    };
  }, []);
  return (
    <button onClick={() => window.dispatchEvent(new Event("bachat:toggle-chat"))}
      aria-label={open ? "Close chat" : unread ? `Open chat, ${unread} unread` : "Open chat with your assistant"}
      aria-expanded={open}
      className="relative grid size-10 place-items-center rounded-full bg-forest text-forest-ink transition hover:brightness-110 md:hidden">
      <MessageCircle aria-hidden className={clsx("absolute size-5 transition-all duration-300",
        open ? "scale-50 rotate-90 opacity-0" : "scale-100 rotate-0 opacity-100")} />
      <X aria-hidden className={clsx("absolute size-5 transition-all duration-300",
        open ? "scale-100 rotate-0 opacity-100" : "scale-50 -rotate-90 opacity-0")} />
      {unread > 0 && !open && (
        <span className="absolute -top-1 -right-1 grid min-w-5 place-items-center rounded-full bg-primary px-1 text-[11px] font-bold text-primary-ink ring-2 ring-bg">
          {unread}
        </span>
      )}
    </button>
  );
}
