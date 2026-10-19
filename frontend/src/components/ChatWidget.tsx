"use client";

import clsx from "clsx";
import { Bell, Loader2, MessageCircle, MessageCircleMore, Mic, Send, Square, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { api, errorText } from "@/lib/api";
import { useSession } from "@/lib/session";

type Msg = { id: string; role: "user" | "bot" | "system"; sender: string; text: string; kind?: string; final: boolean; created_at: string | null };

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
  const [status, setStatus] = useState<string>("pending");
  const [error, setError] = useState("");
  const [recording, setRecording] = useState(false);
  const [unread, setUnread] = useState(0);
  // Latest message that arrived while the chat was closed, shown as a bubble next to the chat button.
  const [preview, setPreview] = useState<Msg | null>(null);

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
  const recorder = useRef<MediaRecorder | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const openRef = useRef(open);
  openRef.current = open;

  // On phones the chat covers the screen: freeze the page underneath so only the messages scroll.
  // (position: fixed is what stops iOS Safari from scrolling the body behind an overlay.)
  useEffect(() => {
    if (!open || !window.matchMedia("(max-width: 639px)").matches) return;
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
      if (data.type !== "message") return;
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
        setWaiting(false);
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
  }, [messages, waiting, open, readAt]);

  // If no reply (and no error notice) arrives, don't leave the person staring at "Thinking…".
  useEffect(() => {
    if (!waiting) return;
    const t = setTimeout(() => {
      setWaiting(false);
      setError("Your assistant is taking longer than usual. You'll get a notification when it replies.");
    }, 90_000);
    return () => clearTimeout(t);
  }, [waiting]);

  const send = useCallback(async (value: string) => {
    const t = value.trim();
    if (!t) return;
    setText("");
    setError("");
    setWaiting(true);
    try {
      await api("/chat/messages", { method: "POST", json: { text: t } });
    } catch (e) {
      setWaiting(false);
      setError(errorText(e));
      setText(t);
    }
  }, []);

  const toggleRecording = async () => {
    if (recording) {
      recorder.current?.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream);
      const chunks: Blob[] = [];
      rec.ondataavailable = (e) => chunks.push(e.data);
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        const blob = new Blob(chunks, { type: rec.mimeType || "audio/webm" });
        const form = new FormData();
        form.append("audio", blob, `voice.${(rec.mimeType || "audio/webm").includes("mp4") ? "m4a" : "webm"}`);
        setWaiting(true);
        try {
          await api("/chat/voice", { method: "POST", body: form });
        } catch (e) {
          setWaiting(false);
          setError(errorText(e));
        }
      };
      recorder.current = rec;
      rec.start();
      setRecording(true);
    } catch {
      setError("Microphone permission is needed for voice messages.");
    }
  };

  const suggestions = user?.onboarding_completed ? SUGGESTIONS : SUGGESTIONS_NEW;

  return (
    <>
      {/* Latest message that arrived while the chat was closed: beside the button on wider screens, above it on phones. */}
      {!open && preview && (
        <div role="status" aria-live="polite"
          className="bubble-pop fixed right-4 bottom-[calc(var(--bottom-nav)+6.5rem)] z-40 w-[min(22rem,calc(100vw-2rem))] sm:right-[6.75rem] sm:bottom-[calc(var(--bottom-nav)+1.5rem)]">
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

      {/* Fixed to the viewport's bottom-right corner, lifted above the bottom nav on phones and tablets. */}
      {!open && (
        <div className="group fixed right-4 bottom-[calc(var(--bottom-nav)+1rem)] z-40 sm:right-6 sm:bottom-[calc(var(--bottom-nav)+1.5rem)]">
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
        <div role="dialog" aria-label="Chat"
          className="fixed inset-0 z-50 flex items-stretch justify-center p-3 pt-[max(0.75rem,env(safe-area-inset-top))] pb-[max(0.75rem,env(safe-area-inset-bottom))] sm:inset-auto sm:right-6 sm:bottom-6 sm:p-0">
          <div className={clsx("absolute inset-0 touch-none bg-ink/30 sm:hidden", closing && "fade-closing")} onClick={close} />
          <div className={clsx("pop-br relative flex h-full w-full min-w-0 sm:h-auto sm:w-auto", closing && "is-closing")}>
          <section className="relative flex h-full w-full min-w-0 flex-col overflow-hidden rounded-[var(--radius-card)] bg-surface shadow-2xl sm:h-[640px] sm:max-h-[calc(100dvh-3rem)] sm:w-[400px]">
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
              <button onClick={close} aria-label="Close chat" className="grid size-9 place-items-center rounded-full hover:bg-white/10">
                <X className="size-5" />
              </button>
            </header>

            <div ref={listRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto overscroll-contain bg-bg px-3 py-4">
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
              {waiting && (
                <div className="flex items-center gap-2 px-2 text-sm text-muted">
                  <Loader2 className="size-4 animate-spin" aria-hidden /> Thinking…
                </div>
              )}
            </div>

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
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    send(text);
                  }
                }}
                rows={1}
                placeholder={recording ? "Listening… tap stop when done" : "Message your assistant"}
                aria-label="Message"
                className="max-h-32 min-h-11 flex-1 resize-none rounded-3xl border border-line bg-surface-2 px-4 py-2.5 text-[15px] outline-none focus:border-forest"
              />
              {text.trim() ? (
                <button type="submit" aria-label="Send" className="grid size-11 shrink-0 place-items-center rounded-full bg-primary text-primary-ink">
                  <Send className="size-5" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={toggleRecording}
                  aria-label={recording ? "Stop recording" : "Record a voice message"}
                  className={clsx(
                    "grid size-11 shrink-0 place-items-center rounded-full",
                    recording ? "animate-pulse bg-danger text-white" : "bg-forest text-forest-ink",
                  )}
                >
                  {recording ? <Square className="size-4" /> : <Mic className="size-5" />}
                </button>
              )}
            </form>
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
          <Bell className="size-3" aria-hidden /> Saving
        </span>
        <div className="chat-text max-w-[85%] rounded-3xl rounded-bl-lg bg-deal-bg px-4 py-2.5 text-[15px] leading-relaxed text-ink">
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
