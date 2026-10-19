"use client";

import clsx from "clsx";
import { Bell, Loader2, Mail, MessageCircle, Mic, Send, ShieldCheck, Square, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Fragment, useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import useSWR from "swr";
import { DropTail } from "./DropTail";
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

  // On phones the chat button lives in the top bar (AppShell): it opens the chat and shows the unread count.
  useEffect(() => {
    const toggle = () => (openRef.current ? closeRef.current() : setOpen(true));
    window.addEventListener("bachat:toggle-chat", toggle);
    return () => window.removeEventListener("bachat:toggle-chat", toggle);
  }, []);
  // Only one drop-down at a time: opening the chat closes settings, and settings opening closes the chat.
  useEffect(() => {
    if (open) window.dispatchEvent(new Event("bachat:close-sheet"));
  }, [open]);
  useEffect(() => {
    const onClose = () => openRef.current && closeRef.current();
    window.addEventListener("bachat:close-chat", onClose);
    return () => window.removeEventListener("bachat:close-chat", onClose);
  }, []);
  // The top-bar chat icon morphs into a cross while the chat is open.
  useEffect(() => {
    window.dispatchEvent(new CustomEvent("bachat:chat-state", { detail: open && !closing }));
  }, [open, closing]);
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && closeRef.current();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);
  useEffect(() => {
    window.dispatchEvent(new CustomEvent("bachat:chat-unread", { detail: unread }));
  }, [unread]);
  // Last time the chat was read when this panel was opened: messages after it get a "New messages" divider.
  const [readAt, setReadAt] = useState<string | null>(null);
  const readAtRef = useRef<string | null>(null);
  const dividerRef = useRef<HTMLDivElement>(null);
  const recorder = useRef<WavRecorder | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const openRef = useRef(open);
  openRef.current = open;

  // On phones the chat covers the screen: freeze the page underneath so only the messages scroll.
  // (position: fixed is what stops iOS Safari from scrolling the body behind an overlay.)
  useEffect(() => {
    if (!open || !window.matchMedia("(max-width: 767px)").matches) return;
    const y = window.scrollY;
    const body = document.body.style;
    const prev = { position: body.position, top: body.top, left: body.left, right: body.right, overflow: body.overflow };
    Object.assign(body, { position: "fixed", top: `-${y}px`, left: "0", right: "0", overflow: "hidden" });
    return () => {
      Object.assign(body, prev);
      window.scrollTo(0, y);
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

  // Grow the message box with its text (up to max-h-32), so a transcript can be read and edited in place.
  useLayoutEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight + el.offsetHeight - el.clientHeight}px`;
  }, [text, open]);

  const suggestions = user?.onboarding_completed ? SUGGESTIONS : SUGGESTIONS_NEW;

  return (
    <>
      {!open && preview && (
        <div role="status" aria-live="polite"
          className="bubble-pop fixed right-4 bottom-[calc(var(--bottom-nav)+6.25rem+env(safe-area-inset-bottom))] z-40 w-[min(20rem,calc(100vw-2rem))] max-md:top-[calc(4.5rem+env(safe-area-inset-top))] max-md:bottom-auto">
          <button onClick={() => setOpen(true)}
            className="relative block w-full rounded-3xl rounded-br-lg border-2 max-md:rounded-br-3xl max-md:rounded-tr-lg border-primary bg-surface px-4 py-3 text-left shadow-xl transition hover:brightness-[0.98] dark:border-forest">
            <span className="mb-0.5 flex items-center gap-1 pr-6 text-[11px] font-semibold text-muted">
              {preview.kind === "notification" ? <Bell className="size-3" aria-hidden /> : <MessageCircle className="size-3" aria-hidden />}
              {preview.sender || "Your assistant"}
            </span>
            <span className="line-clamp-3 text-sm text-ink">{plain(preview.text)}</span>
          </button>
          <button onClick={() => setPreview(null)} aria-label="Dismiss"
            className="absolute top-2 right-2 grid size-7 place-items-center rounded-full text-muted hover:bg-hover">
            <X className="size-4" />
          </button>
        </div>
      )}

      {!open && (
        <button
          onClick={() => setOpen(true)}
          aria-label="Open chat with your assistant"
          className="fixed right-4 bottom-[calc(var(--bottom-nav)+1.5rem+env(safe-area-inset-bottom))] z-40 grid size-15 max-md:hidden place-items-center rounded-full bg-forest text-forest-ink shadow-lg shadow-forest/30 transition hover:scale-105"
        >
          <MessageCircle className="size-7" aria-hidden />
          {unread > 0 && (
            <span className="absolute -top-1 -right-1 grid min-w-6 place-items-center rounded-full bg-primary px-1.5 text-xs font-bold text-primary-ink">
              {unread}
            </span>
          )}
        </button>
      )}

      {open && (
        <div role="dialog" aria-label="Chat"
          className="fixed inset-x-0 top-16 bottom-0 z-50 flex items-start justify-center p-3 pt-2.5 pb-[calc(0.75rem+env(safe-area-inset-bottom))] md:inset-auto md:right-6 md:bottom-6 md:p-0">
          {/* Phones: the chat drops from the chat icon in the top bar, which stays visible above this layer. */}
          <div className={clsx("absolute inset-0 touch-none bg-ink/30 md:hidden", closing && "fade-closing")} onClick={close} />
          <div className={clsx("drop-tr relative flex h-full w-full min-w-0 md:h-auto md:w-auto", closing && "is-closing")}>
          <DropTail className="right-[10px]" fill="fill-forest" stroke="stroke-primary dark:stroke-forest" />
          <section className="relative flex h-full w-full min-w-0 flex-col overflow-hidden rounded-[1.75rem] max-md:rounded-tr-xl border-2 border-primary bg-surface shadow-2xl dark:border-forest md:h-[640px] md:max-h-[calc(100dvh-3rem)] md:w-[400px]">
            <header className="flex items-center gap-3 bg-forest px-4 py-3.5 text-forest-ink">
              <div className="grid size-10 place-items-center rounded-full bg-primary text-primary-ink">
                <MessageCircle className="size-5" aria-hidden />
              </div>
              <div className="min-w-0 flex-1">
                <p className="font-semibold">Your money team</p>
                <p className="truncate text-xs opacity-80">
                  {status === "ready" ? "Assistant · Savings Coach · Deals Advisor" : status === "error" ? "Reconnecting…" : "Setting up your assistant…"}
                </p>
              </div>
              <button onClick={close} aria-label="Close chat" className="grid size-9 place-items-center rounded-full hover:bg-white/10 max-md:hidden">
                <X className="size-5" />
              </button>
            </header>

            <div ref={listRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto overscroll-contain bg-bg/60 px-3 py-4">
              {messages.length === 0 && (
                <div className="mx-auto max-w-[85%] rounded-3xl bg-surface p-4 text-center text-sm text-ink-2">
                  Assalam o Alaikum{user?.full_name ? ` ${user.full_name.split(" ")[0]}` : ""}! 👋 I&apos;m your savings
                  assistant. Tell me about your banks, cards and what you&apos;re saving for, and I&apos;ll build a plan
                  with you. English, Urdu or Roman Urdu are all fine.
                </div>
              )}
              {messages.map((m, i) => {
                const firstUnread = readAt !== null && m.role === "bot" && isAfter(m.created_at, readAt) &&
                  !messages.slice(0, i).some((p) => p.role === "bot" && isAfter(p.created_at, readAt));
                return (
                  <Fragment key={m.id}>
                    {firstUnread && (
                      <div ref={dividerRef} className="flex items-center gap-2 px-2 text-[11px] font-semibold text-forest dark:text-primary">
                        <span className="h-px flex-1 bg-current opacity-40" /> New messages <span className="h-px flex-1 bg-current opacity-40" />
                      </div>
                    )}
                    <Bubble m={m} />
                  </Fragment>
                );
              })}
              {waiting && (activity ? activity.state !== "writing" : !(messages.at(-1)?.role === "bot" && !messages.at(-1)?.final)) && (
                <div className="space-y-1.5 px-2 text-sm text-muted" aria-live="polite">
                  <div className="flex items-center gap-2">
                    <Loader2 className="size-4 shrink-0 animate-spin" aria-hidden />
                    <span className="min-w-0 truncate">
                      {activity?.sender && <span className="font-semibold">{activity.sender} · </span>}
                      {activity?.state === "tool" && activity.tool ? `${toolLabel(activity.tool)}…` : "Thinking…"}
                    </span>
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
              )}
            </div>

            {needsEmail ? (
              <div className="space-y-3 border-t border-line px-4 py-4">
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
                  className="flex h-11 w-full items-center justify-center gap-2 rounded-full bg-primary font-semibold text-primary-ink disabled:opacity-60">
                  {connecting ? <Loader2 className="size-5 animate-spin" aria-hidden /> : <Mail className="size-5" aria-hidden />}
                  Connect Gmail
                </button>
              </div>
            ) : (
            <>
            {messages.length < 3 && !waiting && (
              <div className="flex gap-2 overflow-x-auto overscroll-x-contain px-3 pt-2">
                {suggestions.map((s) => (
                  <button key={s} onClick={() => send(s)} className="shrink-0 rounded-full border border-line bg-surface-2 px-3 py-1.5 text-xs font-medium">
                    {s}
                  </button>
                ))}
              </div>
            )}
            {error && <p className="px-4 pt-2 text-xs text-danger" role="alert">{error}</p>}

            <form
              onSubmit={(e) => {
                e.preventDefault();
                send(text);
              }}
              className="flex items-end gap-2 border-t border-line px-3 py-3"
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
                  : waiting ? "Waiting for a reply…" : "Message your assistant"}
                aria-label="Message"
                className="max-h-32 min-h-11 flex-1 resize-none rounded-3xl border border-line bg-surface-2 px-4 py-2.5 text-[15px] outline-none focus:border-forest disabled:opacity-60"
              />
              {text.trim() && !recording && !transcribing ? (
                <button type="submit" aria-label="Send" disabled={waiting} className="grid size-11 shrink-0 place-items-center rounded-full bg-primary text-primary-ink disabled:opacity-60">
                  <Send className="size-5" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={toggleRecording}
                  disabled={(waiting && !recording) || transcribing}
                  aria-label={recording ? "Stop recording" : transcribing ? "Transcribing" : "Record a voice message"}
                  className={clsx(
                    "grid size-11 shrink-0 place-items-center rounded-full disabled:opacity-60",
                    recording ? "animate-pulse bg-danger text-white" : "bg-forest text-forest-ink",
                  )}
                >
                  {recording ? <Square className="size-4" />
                    : transcribing ? <Loader2 className="size-5 animate-spin" /> : <Mic className="size-5" />}
                </button>
              )}
            </form>
            </>
            )}
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

function Bubble({ m }: { m: Msg }) {
  const mine = m.role === "user";
  if (m.kind === "notification") {
    return (
      <div className="flex flex-col items-start">
        <span className="mb-1 inline-flex items-center gap-1 px-2 text-[11px] font-semibold text-muted">
          <Bell className="size-3" aria-hidden /> Bachat
        </span>
        <div className="chat-text max-w-[85%] rounded-3xl rounded-bl-lg border-2 border-primary bg-surface px-4 py-2.5 text-[15px] leading-relaxed text-ink">
          <RichText text={m.text} />
        </div>
      </div>
    );
  }
  if (m.role === "system") {
    return (
      <p role="status" className="mx-auto max-w-[90%] rounded-2xl border border-danger/40 bg-danger/10 px-3 py-2 text-center text-xs text-danger">
        {m.text}
      </p>
    );
  }
  return (
    <div className={clsx("flex flex-col", mine ? "items-end" : "items-start")}>
      {!mine && m.sender && <span className="mb-1 px-2 text-[11px] font-semibold text-muted">{m.sender}</span>}
      <div
        className={clsx(
          "chat-text max-w-[85%] rounded-3xl px-4 py-2.5 text-[15px] leading-relaxed",
          mine ? "rounded-br-lg bg-primary text-primary-ink" : "rounded-bl-lg bg-surface text-ink",
        )}
      >
        <RichText text={m.text} />
      </div>
    </div>
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
