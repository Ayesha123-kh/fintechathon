"use client";

import clsx from "clsx";
import { Bell, Fingerprint, FlaskConical, LogOut, MessageCircleMore, Moon, Sun, X } from "lucide-react";
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
import type { Dashboard } from "./dashboard/sections";
import { EmailSettings } from "./EmailSettings";
import { BottomNav, navTransitionPending, Sidebar } from "./SectionNav";
import { Button, Logo, Spinner } from "./ui";

/** Open the settings sheet from anywhere, optionally scrolled to a section. */
export function openSettings(section?: "email") {
  window.dispatchEvent(new CustomEvent("bachat:open-settings", { detail: section }));
}

type EmailResult = { connected?: boolean; error?: string };

/** `sidebar` (admin only) replaces the section sidebar on laptops; admin pages handle phones themselves. */
export function AppShell({ children, onChatActivity, sidebar }: {
  children: React.ReactNode; onChatActivity?: () => void; sidebar?: React.ReactNode;
}) {
  const { status, user } = useSession();
  const pathname = usePathname();
  // Phones: a page opened from the bottom nav brightens in (see SectionNav).
  const [enter, setEnter] = useState(false);
  useEffect(() => {
    document.documentElement.classList.remove("page-leaving");
    setEnter(navTransitionPending());
  }, []);
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
  const isAdmin = user?.role === "admin"; // admins only have the admin dashboard: no chat, email, push or finances
  const { data: me } = useSWR<{ test_tools?: boolean }>(status === "active" && !isAdmin ? "/me" : null, fetcher);
  // Colours the month pill. Same key as the dashboard pages' data, so it adds no request there.
  const { data: dash } = useSWR<Pick<Dashboard, "salary_credited_this_month">>(
    status === "active" && !isAdmin ? "/dashboard" : null, fetcher);
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
          : msg.startsWith("smtp_not_configured") ? "Add SMTP_USERNAME and SMTP_PASSWORD to the root .env to send test emails."
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
  const avatar = (size: string) => (
    <button onClick={toggleSettings}
      aria-label={settingsShown ? "Close settings" : "Account and settings"} aria-expanded={settingsShown}
      title={user.full_name || user.email}
      className={clsx("relative grid shrink-0 place-items-center rounded-full bg-forest font-bold tracking-wide text-forest-ink transition hover:brightness-110", size)}>
      <span aria-hidden className={clsx("transition-all duration-300", settingsShown && "scale-50 -rotate-90 opacity-0")}>
        {initials(user.full_name || user.email)}
      </span>
      <X aria-hidden className={clsx("absolute size-5 transition-all duration-300",
        settingsShown ? "scale-100 rotate-0 opacity-100" : "scale-50 rotate-90 opacity-0")} />
    </button>
  );
  const testAlert = me?.test_tools && (
    <button onClick={sendTestAlert} disabled={sending} aria-label="Send a test bank email" title="Send a test bank email"
      className="inline-flex h-11 items-center gap-2 rounded-full px-3 text-sm font-semibold text-ink-2 hover:bg-hover disabled:opacity-50">
      <FlaskConical className={clsx("size-5", sending && "animate-pulse")} aria-hidden />
      <span className="hidden xl:inline">Test bank email</span>
    </button>
  );
  // Deep green once this month's salary has been credited, peach while it hasn't (cream until that's known).
  const salary = dash?.salary_credited_this_month;
  const datePill = (
    <span title={salary === undefined ? undefined : salary ? "Salary credited this month" : "Salary not credited yet this month"}
      className={clsx("inline-flex h-11 items-center rounded-full px-5 text-[15px] transition-colors",
        salary === undefined ? "bg-surface text-ink" : salary ? "bg-forest text-forest-ink" : "bg-primary text-primary-ink")}>
      {month}
      {salary !== undefined && <span className="sr-only">{salary ? ", salary credited" : ", salary not credited yet"}</span>}
    </span>
  );
  return (
    <div className="flex min-h-dvh w-full gap-6 p-4 sm:p-5 lg:gap-8">
      {sidebar ? (
        <aside className="sticky top-5 hidden h-[calc(100dvh-2.5rem)] w-60 shrink-0 overflow-y-auto rounded-[2rem] bg-surface p-4 md:block">
          {sidebar}
        </aside>
      ) : !isAdmin && <Sidebar />}
      <div className="min-w-0 flex-1 pb-[calc(var(--bottom-nav)+5.5rem)] lg:pb-28">
        {/* Phones: a top bar that stays put, with the avatar left, the logo centred and the chat icon right. */}
        <header className="sticky top-0 z-40 -mx-4 -mt-4 mb-4 grid grid-cols-[1fr_auto_1fr] items-center bg-bg/95 px-4 pt-[max(0.75rem,env(safe-area-inset-top))] pb-3 backdrop-blur sm:hidden">
          <div>{avatar("size-11 text-sm")}</div>
          <Link href={isAdmin ? "/admin" : "/dashboard"} aria-label="Saving home"><Logo size={34} nameClassName="text-xl text-ink" /></Link>
          <div className="flex items-center justify-end gap-0.5">
            {testAlert}
            {!isAdmin && <PhoneChatButton />}
          </div>
        </header>
        {pathname === "/dashboard" && (
          <div className="mb-5 sm:hidden">
            <p className="text-sm text-muted">Assalam o Alaikum, {first}</p>
            <h1 className="text-2xl leading-tight font-bold tracking-tight text-ink">Your money at a glance</h1>
          </div>
        )}

        {/* Tablets and laptops. */}
        <header className="flex items-center gap-3 pt-1 pb-5 max-sm:hidden sm:pb-6 lg:pt-0">
          {/* The logo lives in the sidebar on laptops; tablets show it next to the greeting. */}
          <Link href={isAdmin ? "/admin" : "/dashboard"} aria-label="Saving home" className="lg:hidden">
            <Logo size={52} withName={false} tone="forest" />
          </Link>
          <div className="min-w-0 flex-1">
            <p className="text-sm text-muted sm:text-base">Assalam o Alaikum,</p>
            {/* The signed-in user's own first name. */}
            <p className="truncate text-2xl leading-tight font-bold tracking-tight text-ink sm:text-[1.75rem] lg:text-4xl">{first}</p>
          </div>
          {testAlert}
          <span className="hidden lg:inline-flex">{datePill}</span>
          {avatar("size-12 text-[15px] lg:size-14 lg:text-lg")}
        </header>

        <main className={enter ? "page-enter" : undefined} onAnimationEnd={() => setEnter(false)}>{children}</main>
      </div>

      {!isAdmin && (
        <>
          <BottomNav />
          <Suspense>
            <ChatWidget onActivity={onChatActivity} />
          </Suspense>
        </>
      )}

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
    // A panel that opens from the avatar (top-left on phones, top-right on wider screens).
    <div className="fixed inset-0 z-50" role="dialog" aria-label={title}>
      <div className={clsx("absolute inset-0 touch-none bg-ink/30", closing && "fade-closing")} onClick={close} />
      <div className={clsx("pop-tr pop-sheet absolute top-[4.75rem] right-3 left-3 sm:left-auto sm:w-96 lg:top-[5.5rem] lg:right-5", closing && "is-closing")}>
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
  const isAdmin = user?.role === "admin";
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
      {!isAdmin && <EmailSettings result={emailResult} />}
      {passkeySupported() && (
        <Button variant="outline" className="w-full justify-start" onClick={addPasskey} loading={busy === "passkey"}>
          <Fingerprint className="size-5" aria-hidden />
          {hasPasskey ? "Add fingerprint / face on this device" : "Turn on fingerprint / face sign-in"}
        </Button>
      )}
      {!isAdmin && pushSupported() && (
        <Button variant="outline" className="w-full justify-start" onClick={togglePush} loading={busy === "push"}>
          <Bell className="size-5" aria-hidden />
          {pushOn ? "Turn off notifications on this device" : "Turn on notifications"}
        </Button>
      )}
      <ThemePicker />
      {!isAdmin && (
        <p className="text-xs text-muted">
          Everything else, like your banks, goals, savings rule, language, sadqah reminders or the investment board,
          is changed by telling your assistant in the chat.
        </p>
      )}
      {msg && <p className="rounded-2xl bg-primary/30 px-4 py-3 text-sm">{msg}</p>}
      <Button variant="ghost" className="w-full justify-start text-danger" onClick={signOut}>
        <LogOut className="size-5" aria-hidden /> Sign out
      </Button>
    </div>
  );
}

function ThemePicker() {
  const [theme, setTheme] = useState<ThemeChoice>("light");
  useEffect(() => setTheme(getTheme()), []);
  const options: { id: ThemeChoice; label: string; icon: typeof Sun }[] = [
    { id: "light", label: "Light", icon: Sun },
    { id: "dark", label: "Dark", icon: Moon },
  ];
  return (
    <div>
      <p className="mb-2 text-sm font-medium text-ink-2">Appearance</p>
      <div role="radiogroup" aria-label="Appearance" className="grid grid-cols-2 gap-1 rounded-full bg-surface-2 p-1">
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

/** Phones: opens and closes the chat popup (ChatWidget), shows the unread count and turns into a cross while open. */
function PhoneChatButton() {
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
      className="relative grid size-11 place-items-center rounded-full bg-forest text-forest-ink transition hover:brightness-110 active:scale-95">
      <MessageCircleMore aria-hidden className={clsx("absolute size-5 transition-all duration-300",
        open ? "scale-50 rotate-90 opacity-0" : "scale-100 rotate-0 opacity-100")} />
      <X aria-hidden className={clsx("absolute size-5 transition-all duration-300",
        open ? "scale-100 rotate-0 opacity-100" : "scale-50 -rotate-90 opacity-0")} />
      {unread > 0 && !open && (
        <span className="absolute -top-1 -right-1 grid min-w-5 place-items-center rounded-full bg-alert px-1 text-[11px] font-bold text-white ring-2 ring-bg">
          {unread}
        </span>
      )}
    </button>
  );
}
