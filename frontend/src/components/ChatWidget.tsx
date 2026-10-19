"use client";

import clsx from "clsx";
import { AlertCircle, Bell, Loader2, Mail, MessageCircleMore, Mic, Send, ShieldCheck, Sprout, Square, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Fragment, useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import useSWR from "swr";
import { api, errorText, fetcher } from "@/lib/api";
import { useSession } from "@/lib/session";
import { recordWav, type WavRecorder } from "@/lib/wav";

type Msg = { id: string; role: "user" | "bot" | "system"; sender: string; text: string; kind?: string; final: boolean; created_at: string | null };
// Live progress of the assistant's turn: what it is thinking and which tool it is using. Never stored.
type Activity = { state: "thinking" | "tool" | "writing" | "idle"; thinking: string; tool: string | null; sender: string };

/** "fin_user_list_transactions" -> "List transactions" */
function toolLabel(name: string) {
  const words = name.replace(/^(fin_user|fin_market|agents)_/, "").replace(/_/g, " ").trim();
  return words ? words[0].toUpperCase() + words.slice(1) : "Working";
}

const SUGGESTIONS_NEW = ["Let's set up my savings", "I want to save for a car", "Which banks do you support?"];
const SUGGESTIONS = ["How much did I spend this week?", "Any deals for my cards today?", "I got a salary increment", "Am I on track for my goals?"];

export function ChatWidget({ onActivity }: { onActivity?: () => void }) {
  const params = useSearchParams();
  const router = useRouter();
  const { user } = useSession();
  const [open, setOpen] = useState(false);
  const [closing, setClosing] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [waiting, setWaiting] = useState(false);
  const [activity, setActivity] = useState<Activity | null>(null);
  const [showThinking, setShowThinking] = useState(false);
  // Bumped on every sign of life from the assistant; the "taking longer" notice only fires after real silence.
  const [lastSign, setLastSign] = useState(0);
  const [status, setStatus] = useState<string>("pending");
  const [error, setError] = useState("");
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  // Bumped when a voice transcript lands in the message box, to focus it for editing.
  const [heard, setHeard] = useState(0);
  const [unread, setUnread] = useState(0);
  // Latest message that arrived while the chat was closed, shown as a bubble next to the chat button.
  const [preview, setPreview] = useState<Msg | null>(null);
  // Onboarding starts only after an inbox is connected (unless Gmail isn't configured on the server).
  const { data: email, mutate: refreshEmail } = useSWR<{ configured: boolean; connections: unknown[] }>(
    user && user.role !== "admin" && !user.onboarding_completed ? "/email/connections" : null, fetcher);
  const needsEmail = !!email?.configured && email.connections.length === 0;
  const [connecting, setConnecting] = useState(false);
  const connectGmail = async () => {
    setConnecting(true);
    setError("");
    try {
      const { url } = await api<{ url: string }>("/email/google/start", { method: "POST" });
      window.location.href = url;
    } catch (e) {
      setError(errorText(e));
      setConnecting(false);
    }
  };

  // Phones: the chat icon in the top bar (AppShell) toggles the chat and shows the unread count and open state.
  useEffect(() => {
    const toggle = () => (openRef.current ? closeRef.current() : setOpen(true));
    window.addEventListener("bachat:toggle-chat", toggle);
    return () => window.removeEventListener("bachat:toggle-chat", toggle);
  }, []);
  useEffect(() => {
    window.dispatchEvent(new CustomEvent("bachat:chat-state", { detail: open && !closing }));
  }, [open, closing]);
  useEffect(() => {
    window.dispatchEvent(new CustomEvent("bachat:chat-unread", { detail: unread }));
  }, [unread]);
  // Only one drop-down at a time: opening the chat closes settings, and settings opening closes the chat.
  useEffect(() => {
    if (open) window.dispatchEvent(new Event("bachat:close-sheet"));
  }, [open]);
  useEffect(() => {
    const onClose = () => openRef.current && closeRef.current();
    window.addEventListener("bachat:close-chat", onClose);
    return () => window.removeEventListener("bachat:close-chat", onClose);
  }, []);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && closeRef.current();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);
  // Last time the chat was read when this panel was opened: messages after it get a "New messages" divider.
  const [readAt, setReadAt] = useState<string | null>(null);
  const readAtRef = useRef<string | null>(null);
  const dividerRef = useRef<HTMLDivElement>(null);
  const recorder = useRef<WavRecorder | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const openRef = useRef(open);
  openRef.current = open;

  // On phones the chat pops up over the page: stop the page underneath from scrolling so only the messages do.
  // overflow (not position: fixed on the body) keeps the sticky top bar, and its chat icon, where it is; the
  // backdrop's touch-none covers iOS Safari, which ignores overflow for touch scrolling.
  useEffect(() => {
    if (!open || !window.matchMedia("(max-width: 639px)").matches) return;
    const html = document.documentElement.style;
    const prev = { overflow: html.overflow, overscroll: html.overscrollBehavior };
    Object.assign(html, { overflow: "hidden", overscrollBehavior: "none" });
    return () => {
      Object.assign(html, { overflow: prev.overflow, overscrollBehavior: prev.overscroll });
    };
  }, [open]);

  useEffect(() => {
    if (params.get("chat") === "1") setOpen(true);
  }, [params]);

  const close = useCallback(() => {
    setClosing(true); // plays the shrink-back animation, then unmounts
    setTimeout(() => {
      setOpen(false);
      setClosing(false);
    }, 170);
    if (new URLSearchParams(window.location.search).get("chat")) router.replace(window.location.pathname);
  }, [router]);
  const closeRef = useRef(close);
  closeRef.current = close;

  // History + live stream (SSE). The stream also tells the server we're online (no duplicate pushes).
  useEffect(() => {
    let cancelled = false;
    api<Msg[]>("/chat/messages").then((m) => !cancelled && setMessages(m)).catch(() => {});
    const es = new EventSource("/api/chat/stream", { withCredentials: true });
    es.onmessage = (ev) => {
      const data = JSON.parse(ev.data);
      if (data.type === "activity") {
        const a: Activity = data.activity;
        setLastSign(Date.now());
        setActivity(a.state === "idle" ? null : a);
        if (a.state !== "idle") setWaiting(true); // a turn is running: no parallel questions
        return;
      }
      if (data.type !== "message") return;
      setLastSign(Date.now());
      const msg: Msg = data.message;
      setMessages((prev) => {
        const i = prev.findIndex((p) => p.id === msg.id);
        if (i >= 0) {
          const copy = prev.slice();
          copy[i] = msg;
          return copy;
        }
        return [...prev, msg];
      });
      if (msg.role === "bot" || msg.role === "system") {
        // Keep the input locked until the reply is complete, so a second question can't run in parallel.
        if (msg.final || msg.role === "system") {
          setWaiting(false);
          setActivity(null);
        }
        if (!openRef.current && msg.final) {
          setUnread((u) => u + 1);
          setPreview(msg);
        }
        onActivity?.();
      }
    };
    // EventSource can't refresh tokens itself: on errors, a normal API call refreshes the cookie
    // (or surfaces the lock screen) and the stream then reconnects on its own.
    let lastPing = 0;
    es.onerror = () => {
      if (Date.now() - lastPing < 10_000) return;
      lastPing = Date.now();
      api("/me").catch(() => {});
    };
    return () => {
      cancelled = true;
      es.close();
    };
  }, [onActivity]);

  useEffect(() => {
    api<{ count: number; read_at: string | null }>("/chat/unread")
      .then((u) => {
        setUnread(u.count);
        readAtRef.current = u.read_at;
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!preview) return;
    const t = setTimeout(() => setPreview(null), 10_000);
    return () => clearTimeout(t);
  }, [preview]);

  useEffect(() => {
    if (!open) return;
    setPreview(null);
    setReadAt(readAtRef.current ?? "1970-01-01T00:00:00Z");
    setUnread(0);
    api("/chat/read", { method: "POST" }).catch(() => {});
    api<{ status: string }>("/chat/status").then((s) => setStatus(s.status)).catch(() => setStatus("error"));
    return () => {
      // Everything seen in this session is read now.
      readAtRef.current = new Date().toISOString();
    };
  }, [open]);

  const jumped = useRef(false);
  const step = `${activity?.state ?? ""}:${activity?.tool ?? ""}:${showThinking}`; // keep the live step in view
  useEffect(() => {
    if (!open) {
      jumped.current = false;
      return;
    }
    if (!jumped.current && dividerRef.current && listRef.current) {
      jumped.current = true;
      listRef.current.scrollTo({ top: dividerRef.current.offsetTop - 12 });
      return;
    }
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: jumped.current ? "smooth" : "auto" });
    if (messages.length) jumped.current = true;
  }, [messages, waiting, open, readAt, step]);

  // Long agent turns keep sending thinking / tool activity, which keeps this waiting. Only if the assistant goes
  // completely silent do we stop waiting, so the person isn't left staring at "Thinking…".
  useEffect(() => {
    if (!waiting) return;
    const t = setTimeout(() => {
      setWaiting(false);
      setActivity(null);
      setError("Your assistant is taking longer than usual. You'll get a notification when it replies.");
    }, 120_000);
    return () => clearTimeout(t);
  }, [waiting, lastSign]);

  const send = useCallback(async (value: string) => {
    const t = value.trim();
    if (!t || waiting) return;
    setText("");
    setError("");
    setWaiting(true);
    try {
      await api("/chat/messages", { method: "POST", json: { text: t } });
    } catch (e) {
      setWaiting(false);
      if (errorText(e).startsWith("connect_gmail_first")) refreshEmail();
      else setError(errorText(e));
      setText(t);
    }
  }, [waiting, refreshEmail]);

  // Release the microphone if the widget goes away mid-recording.
  useEffect(() => () => recorder.current?.cancel(), []);

  const toggleRecording = async () => {
    if (recording) {
      const rec = recorder.current;
      recorder.current = null;
      setRecording(false);
      if (!rec) return;
      setTranscribing(true);
      setError("");
      try {
        const form = new FormData();
        form.append("audio", await rec.stop(), "voice.wav");
        const res = await api<{ text: string }>("/chat/transcribe", { method: "POST", body: form });
        // Not sent: it goes into the message box (after anything typed meanwhile) to check and edit first.
        setText((t) => (t.trim() ? `${t.trimEnd()} ${res.text}` : res.text));
        setHeard((n) => n + 1);
      } catch (e) {
        setError(errorText(e));
      } finally {
        setTranscribing(false);
      }
      return;
    }
    try {
      recorder.current = await recordWav();
      setRecording(true);
    } catch {
      setError("Microphone permission is needed for voice messages.");
    }
  };

  useEffect(() => {
    const el = inputRef.current;
    if (!heard || !el) return;
    el.focus();
    el.setSelectionRange(el.value.length, el.value.length);
  }, [heard]);

  // Grow the message box with its text (up to max-h-36), so a transcript can be read and edited in place.
  useLayoutEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight + el.offsetHeight - el.clientHeight}px`;
  }, [text, open]);

  const suggestions = user?.onboarding_completed ? SUGGESTIONS : SUGGESTIONS_NEW;

  return (
    <>
      {/* Latest message that arrived while the chat was closed: beside the button on wider screens, under the top bar's chat icon on phones. */}
      {!open && preview && (
        <div role="status" aria-live="polite"
          className="bubble-pop fixed right-4 z-40 w-[min(22rem,calc(100vw-2rem))] max-sm:top-[calc(max(0.75rem,env(safe-area-inset-top))+3.75rem)] sm:right-[6.75rem] sm:bottom-[calc(var(--bottom-nav)+1.5rem)]">
          <button onClick={() => setOpen(true)}
            className="relative block w-full rounded-2xl bg-surface px-5 py-4 text-left shadow-[0_12px_32px_rgb(16_26_20/0.12)] transition hover:brightness-[0.98]">
            <span className="mb-0.5 flex items-center gap-1 pr-6 text-sm font-bold text-forest dark:text-primary">
              {preview.kind === "notification" && <Bell className="size-3.5" aria-hidden />}
              {preview.kind === "notification" ? "Saving" : "Saving assistant"}
            </span>
            <span className="line-clamp-3 text-[15px] leading-snug text-ink-2">{plain(preview.text)}</span>
          </button>
          <button onClick={() => setPreview(null)} aria-label="Dismiss"
            className="absolute top-2 right-2 grid size-7 place-items-center rounded-full text-muted hover:bg-hover">
            <X className="size-4" />
          </button>
        </div>
      )}

      {/* Tablets and laptops: fixed to the viewport's bottom-right corner (above the bottom nav on tablets). Phones use the top bar's chat icon. */}
      {!open && (
        <div className="group fixed right-6 bottom-[calc(var(--bottom-nav)+1.5rem)] z-40 max-sm:hidden">
          <button
            onClick={() => setOpen(true)}
            aria-label={unread ? `Open chat, ${unread} unread` : "Open chat with your assistant"}
            className="relative grid size-16 place-items-center rounded-full bg-forest text-forest-ink shadow-[0_10px_24px_rgb(22_66_60/0.35)] ring-[6px] ring-primary/45 transition hover:scale-105 hover:ring-primary/70 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-forest active:scale-95"
          >
            <MessageCircleMore className="size-7" aria-hidden />
            {unread > 0 && (
              <span className="absolute -top-1 -right-1 grid min-w-6 place-items-center rounded-full bg-alert px-1.5 text-xs font-bold text-white ring-2 ring-white">
                {unread}
              </span>
            )}
          </button>
          {!preview && (
            <span role="tooltip"
              className="pointer-events-none absolute top-1/2 right-[calc(100%+0.75rem)] -translate-y-1/2 rounded-xl bg-side px-3 py-2 text-sm whitespace-nowrap text-forest-ink opacity-0 transition group-hover:opacity-100 max-sm:hidden">
              Chat with your assistant
            </span>
          )}
        </div>
      )}

      {open && (
        // Phones: a popup between the top bar and the bottom nav, which stay visible and usable above its backdrop.
        <div role="dialog" aria-label="Chat"
          className="fixed inset-0 z-[35] sm:inset-auto sm:right-6 sm:bottom-6 sm:z-50">
          <div className={clsx("absolute inset-0 touch-none bg-ink/30 sm:hidden", closing && "fade-closing")} onClick={close} />
          <div className={clsx("pop-chat absolute inset-x-3 top-[calc(max(0.75rem,env(safe-area-inset-top))+3.75rem)] bottom-[calc(var(--bottom-nav)+0.5rem)] flex min-w-0 sm:static sm:inset-auto", closing && "is-closing")}>
          <section className="relative flex h-full w-full min-w-0 flex-col overflow-hidden rounded-[var(--radius-card)] bg-surface shadow-2xl sm:h-[min(780px,calc(100dvh-3rem))] sm:w-[min(500px,calc(100vw-3rem))] lg:w-[540px]">
            <header className="flex items-center gap-3 border-b border-line bg-surface px-4 py-3.5 sm:px-5 sm:py-4">
              <span className="relative">
                <AssistantAvatar size="lg" />
                <span className={clsx("absolute -right-0.5 -bottom-0.5 size-3.5 rounded-full ring-2 ring-surface",
                  status === "ready" ? "bg-[#3fb37f]" : status === "error" ? "bg-alert" : "bg-badge")} aria-hidden />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-lg leading-tight font-bold text-ink">Saving assistant</p>
                <p className="truncate text-sm text-muted">
                  {waiting ? (activity?.state === "tool" ? "working…" : "typing…") : status === "ready" ? "Online · Savings Coach · Deals Advisor" : status === "error" ? "Reconnecting…" : "Setting up your assistant…"}
                </p>
              </div>
              <button onClick={close} aria-label="Close chat" className="grid size-10 place-items-center rounded-full text-ink-2 hover:bg-hover">
                <X className="size-5" />
              </button>
            </header>

            {/* WhatsApp-style thread: the assistant on the left, you on the right, a date pill whenever the day changes. */}
            <div ref={listRef} className="min-h-0 flex-1 overflow-y-auto overscroll-contain bg-bg px-3 py-5 sm:px-5">
              {messages.length === 0 && (
                <Row side="left" avatar>
                  <div className="chat-text rounded-2xl rounded-bl-md bg-surface px-4 py-3 text-[15px] leading-relaxed text-ink shadow-sm">
                    Assalam o Alaikum{user?.full_name ? ` ${user.full_name.split(" ")[0]}` : ""}! 👋 I&apos;m your savings
                    assistant. Tell me about your banks, cards and what you&apos;re saving for, and I&apos;ll build a plan
                    with you. English, Urdu or Roman Urdu are all fine.
                  </div>
                </Row>
              )}
              {messages.map((m, i) => {
                const prev = messages[i - 1];
                const next = messages[i + 1];
                const side = (x?: Msg) => (x ? (x.role === "user" ? "right" : "left") : null);
                const newDay = !prev || dayKey(prev.created_at) !== dayKey(m.created_at);
                const firstUnread = readAt !== null && m.role === "bot" && isAfter(m.created_at, readAt) &&
                  !messages.slice(0, i).some((p) => p.role === "bot" && isAfter(p.created_at, readAt));
                const startsGroup = newDay || firstUnread || side(prev) !== side(m);
                const nextNewDay = !!next && dayKey(next.created_at) !== dayKey(m.created_at);
                const endsGroup = !next || nextNewDay || side(next) !== side(m);
                return (
                  <Fragment key={m.id}>
                    {newDay && m.created_at && (
                      <div className="my-3 flex justify-center first:mt-0">
                        <span className="rounded-full bg-surface px-3 py-1 text-xs font-medium text-muted shadow-sm">{dayLabel(m.created_at)}</span>
                      </div>
                    )}
                    {firstUnread && (
                      <div ref={dividerRef} className="my-3 flex justify-center">
                        <span className="rounded-full bg-primary px-3 py-1 text-xs font-semibold text-primary-ink">New messages</span>
                      </div>
                    )}
                    <div className={startsGroup ? "mt-3 first:mt-0" : "mt-1"}>
                      <Bubble m={m} first={startsGroup} last={endsGroup} />
                    </div>
                  </Fragment>
                );
              })}
              {waiting && (activity ? activity.state !== "writing" : !(messages.at(-1)?.role === "bot" && !messages.at(-1)?.final)) && (
                <div className="mt-3" aria-live="polite">
                  <Row side="left" avatar>
                    <div className="space-y-1.5 rounded-2xl rounded-bl-md bg-surface px-4 py-3 text-sm text-muted shadow-sm">
                      <div className="flex items-center gap-2">
                        {activity ? <Loader2 className="size-4 shrink-0 animate-spin" aria-hidden /> : (
                          <span className="flex items-center gap-1" role="status" aria-label="Assistant is typing">
                            {[0, 1, 2].map((d) => (
                              <span key={d} className="size-2 animate-bounce rounded-full bg-muted" style={{ animationDelay: `${d * 150}ms` }} />
                            ))}
                          </span>
                        )}
                        {activity && (
                          <span className="min-w-0 truncate">
                            {activity.sender && <span className="font-semibold text-ink-2">{activity.sender} · </span>}
                            {activity.state === "tool" && activity.tool ? `${toolLabel(activity.tool)}…` : "Thinking…"}
                          </span>
                        )}
                        {activity?.thinking && (
                          <button onClick={() => setShowThinking((v) => !v)} aria-expanded={showThinking}
                            className="ml-auto shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium hover:bg-hover">
                            {showThinking ? "Hide" : "Show"} thinking
                          </button>
                        )}
                      </div>
                      {activity?.thinking && (
                        <p className={clsx("border-l-2 border-line pl-3 text-xs whitespace-pre-wrap italic",
                          showThinking ? "max-h-48 overflow-y-auto" : "line-clamp-2")}>
                          {showThinking ? activity.thinking : activity.thinking.slice(-240)}
                        </p>
                      )}
                    </div>
                  </Row>
                </div>
              )}
            </div>

            <div className="border-t border-line bg-surface">
              {needsEmail ? (
                <div className="space-y-3 px-4 py-4 sm:px-5">
                  <p className="text-sm text-ink-2">
                    First, connect the Gmail inbox where your bank alerts arrive. Your assistant then plans with your
                    real spending instead of guesses.
                  </p>
                  <div className="flex items-start gap-2 text-xs text-muted">
                    <ShieldCheck className="mt-0.5 size-4 shrink-0 text-forest dark:text-primary" aria-hidden />
                    <p>Read-only. Only alert emails from your banks are read. Disconnect anytime in Settings.</p>
                  </div>
                  {error && <p className="text-xs text-danger" role="alert">{error}</p>}
                  <button onClick={connectGmail} disabled={connecting}
                    className="flex h-12 w-full items-center justify-center gap-2 rounded-full bg-forest font-semibold text-forest-ink transition hover:brightness-110 disabled:opacity-60">
                    {connecting ? <Loader2 className="size-5 animate-spin" aria-hidden /> : <Mail className="size-5" aria-hidden />}
                    Connect Gmail
                  </button>
                </div>
              ) : (
              <>
              {messages.length < 3 && !waiting && (
                <div className="flex gap-2 overflow-x-auto overscroll-x-contain px-3 pt-3 sm:px-5">
                  {suggestions.map((s) => (
                    <button key={s} onClick={() => send(s)}
                      className="shrink-0 rounded-full border border-line bg-bg px-3.5 py-2 text-sm font-medium text-ink-2 transition hover:border-forest hover:text-ink">
                      {s}
                    </button>
                  ))}
                </div>
              )}
              {error && <p className="px-4 pt-2 text-sm text-danger sm:px-5" role="alert">{error}</p>}

              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  send(text);
                }}
                className="flex items-end gap-2 px-3 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:px-5 sm:pb-4"
              >
                <textarea
                  ref={inputRef}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      send(text);
                    }
                  }}
                  rows={1}
                  disabled={waiting}
                  placeholder={recording ? "Listening… tap stop when done" : transcribing ? "Turning your voice into text…"
                    : waiting ? "Waiting for a reply…" : "Type a message"}
                  aria-label="Message"
                  className="max-h-36 min-h-12 flex-1 resize-none rounded-3xl border border-line bg-bg px-5 py-3 text-[15px] text-ink outline-none placeholder:text-muted focus:border-forest disabled:opacity-60"
                />
                {text.trim() && !recording && !transcribing ? (
                  <button type="submit" aria-label="Send" disabled={waiting} className="grid size-12 shrink-0 place-items-center rounded-full bg-forest text-forest-ink transition hover:brightness-110 active:scale-95 disabled:opacity-60">
                    <Send className="size-5" />
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={toggleRecording}
                    disabled={(waiting && !recording) || transcribing}
                    aria-label={recording ? "Stop recording" : transcribing ? "Transcribing" : "Record a voice message"}
                    className={clsx(
                      "grid size-12 shrink-0 place-items-center rounded-full transition active:scale-95 disabled:opacity-60",
                      recording ? "animate-pulse bg-danger text-white" : "bg-forest text-forest-ink hover:brightness-110",
                    )}
                  >
                    {recording ? <Square className="size-4" />
                      : transcribing ? <Loader2 className="size-5 animate-spin" /> : <Mic className="size-5" />}
                  </button>
                )}
              </form>
              </>
              )}
            </div>
          </section>
          </div>
        </div>
      )}
    </>
  );
}

/** Markdown-free one-liner for the preview bubble. */
function plain(text: string): string {
  return text.replace(/\*\*([^*]+)\*\*/g, "$1").replace(/_([^_]+)_/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1").replace(/\s*\n+\s*/g, " · ").trim();
}

function isAfter(when: string | null, ref: string) {
  return !!when && new Date(when).getTime() > new Date(ref).getTime();
}

const dayKey = (d: string | null) => (d ? new Date(d).toDateString() : "");
const time = (d: string | null) => (d ? new Date(d).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }) : "");
function dayLabel(d: string) {
  const date = new Date(d);
  const today = new Date();
  const yesterday = new Date(today.getTime() - 86_400_000);
  if (date.toDateString() === today.toDateString()) return "Today";
  if (date.toDateString() === yesterday.toDateString()) return "Yesterday";
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
}

/** The assistant's round sprout avatar, in the dashboard's peach and green. */
function AssistantAvatar({ size = "sm" }: { size?: "sm" | "lg" }) {
  return (
    <span aria-hidden className={clsx("grid shrink-0 place-items-center rounded-full bg-primary text-forest",
      size === "lg" ? "size-11" : "size-8")}>
      <Sprout className={size === "lg" ? "size-5" : "size-4"} strokeWidth={2.25} />
    </span>
  );
}

/** One side of the thread. The assistant's side keeps a column for its avatar so its bubbles line up. */
function Row({ side, avatar, children }: { side: "left" | "right"; avatar?: boolean; children: React.ReactNode }) {
  if (side === "right") return <div className="flex justify-end pl-12 sm:pl-16">{children}</div>;
  return (
    <div className="flex items-end gap-2 pr-12 sm:pr-16">
      {avatar ? <AssistantAvatar /> : <span className="w-8 shrink-0" aria-hidden />}
      <div className="min-w-0">{children}</div>
    </div>
  );
}

function Bubble({ m, first, last }: { m: Msg; first: boolean; last: boolean }) {
  const mine = m.role === "user";
  const stamp = time(m.created_at);
  if (mine) {
    return (
      <Row side="right">
        <div className={clsx("chat-text rounded-2xl bg-forest px-4 pt-2.5 pb-1.5 text-[15px] leading-relaxed text-forest-ink shadow-sm",
          last && "rounded-br-md")}>
          <RichText text={m.text} />
          {stamp && <p className="mt-0.5 text-right text-[11px] text-forest-muted">{stamp}</p>}
        </div>
      </Row>
    );
  }
  const tone = m.kind === "notification" ? "bg-deal-bg text-ink" : m.role === "system" ? "bg-danger/10 text-danger" : "bg-surface text-ink";
  return (
    <Row side="left" avatar={last}>
      {first && (m.kind === "notification" || m.sender) && (
        <p className="mb-1 flex items-center gap-1 px-1 text-xs font-semibold text-forest dark:text-primary">
          {m.kind === "notification" && <Bell className="size-3" aria-hidden />}
          {m.kind === "notification" ? "Saving" : m.role === "system" ? "Saving assistant" : m.sender}
        </p>
      )}
      <div role={m.role === "system" ? "status" : undefined}
        className={clsx("chat-text rounded-2xl px-4 pt-2.5 pb-1.5 text-[15px] leading-relaxed shadow-sm", tone, last && "rounded-bl-md")}>
        {m.role === "system" && <AlertCircle className="mr-1.5 mb-0.5 inline size-4 align-middle" aria-hidden />}
        <RichText text={m.text} />
        {stamp && <p className="mt-0.5 text-right text-[11px] text-muted">{stamp}</p>}
      </div>
    </Row>
  );
}

/** Tiny, safe markdown: paragraphs, "- " bullets, **bold**, _italic_ and links. No HTML injection. */
function RichText({ text }: { text: string }) {
  const blocks = text.trim().split(/\n{2,}/);
  return (
    <>
      {blocks.map((block, i) => {
        const lines = block.split("\n");
        if (lines.every((l) => /^\s*([-*•]|\d+\.)\s+/.test(l))) {
          return (
            <ul key={i}>
              {lines.map((l, j) => (
                <li key={j}>{inline(l.replace(/^\s*([-*•]|\d+\.)\s+/, ""))}</li>
              ))}
            </ul>
          );
        }
        return (
          <p key={i}>
            {lines.map((l, j) => (
              <Fragment key={j}>
                {j > 0 && <br />}
                {inline(l)}
              </Fragment>
            ))}
          </p>
        );
      })}
    </>
  );
}

function inline(s: string): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|_[^_]+_|\[[^\]]+\]\((https?:\/\/[^)\s]+)\)|https?:\/\/\S+)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = re.exec(s))) {
    if (m.index > last) out.push(s.slice(last, m.index));
    const t = m[0];
    if (t.startsWith("**")) out.push(<strong key={k++}>{t.slice(2, -2)}</strong>);
    else if (t.startsWith("_")) out.push(<em key={k++}>{t.slice(1, -1)}</em>);
    else if (t.startsWith("[")) {
      const label = t.slice(1, t.indexOf("]"));
      out.push(<a key={k++} href={m[2]} target="_blank" rel="noopener noreferrer">{label}</a>);
    } else out.push(<a key={k++} href={t} target="_blank" rel="noopener noreferrer">{t}</a>);
    last = m.index + t.length;
  }
  if (last < s.length) out.push(s.slice(last));
  return out;
}
