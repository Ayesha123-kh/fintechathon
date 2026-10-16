"use client";

import clsx from "clsx";
import { Loader2, MessageCircle, Mic, Send, Square, X } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { api, errorText } from "@/lib/api";
import { useSession } from "@/lib/session";

type Msg = { id: string; role: "user" | "bot" | "system"; sender: string; text: string; final: boolean; created_at: string | null };

const SUGGESTIONS_NEW = ["Let's set up my savings", "I want to save for a car", "Which banks do you support?"];
const SUGGESTIONS = ["How much did I spend this week?", "Any deals for my cards today?", "I got a salary increment", "Am I on track for my goals?"];

export function ChatWidget({ onActivity }: { onActivity?: () => void }) {
  const params = useSearchParams();
  const router = useRouter();
  const { user } = useSession();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [waiting, setWaiting] = useState(false);
  const [status, setStatus] = useState<string>("pending");
  const [error, setError] = useState("");
  const [recording, setRecording] = useState(false);
  const [unread, setUnread] = useState(0);
  const recorder = useRef<MediaRecorder | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const openRef = useRef(open);
  openRef.current = open;

  useEffect(() => {
    if (params.get("chat") === "1") setOpen(true);
  }, [params]);

  const close = () => {
    setOpen(false);
    if (params.get("chat")) router.replace(window.location.pathname);
  };

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
      if (msg.role === "bot") {
        setWaiting(false);
        if (!openRef.current && msg.final) setUnread((u) => u + 1);
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
    if (!open) return;
    setUnread(0);
    api<{ status: string }>("/chat/status").then((s) => setStatus(s.status)).catch(() => setStatus("error"));
  }, [open]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, waiting, open]);

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
      {!open && (
        <button
          onClick={() => setOpen(true)}
          aria-label="Open chat with your assistant"
          className="fixed right-4 bottom-[calc(1.5rem+env(safe-area-inset-bottom))] z-40 grid size-15 place-items-center rounded-full bg-forest text-forest-ink shadow-lg shadow-forest/30 transition hover:scale-105"
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
        <div className="fixed inset-0 z-50 flex items-end justify-end md:inset-auto md:right-6" role="dialog" aria-label="Chat">
          <div className="absolute inset-0 bg-ink/30 md:hidden" onClick={close} />
          <section className="relative flex h-[92dvh] w-full flex-col overflow-hidden rounded-t-[1.75rem] bg-surface shadow-2xl md:h-[640px] md:w-[400px] md:rounded-[1.75rem]">
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

            <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto bg-bg/60 px-3 py-4">
              {messages.length === 0 && (
                <div className="mx-auto max-w-[85%] rounded-3xl bg-surface p-4 text-center text-sm text-ink-2">
                  Assalam o Alaikum{user?.full_name ? ` ${user.full_name.split(" ")[0]}` : ""}! 👋 I&apos;m your savings
                  assistant. Tell me about your banks, cards and what you&apos;re saving for, and I&apos;ll build a plan
                  with you. English, Urdu or Roman Urdu are all fine.
                </div>
              )}
              {messages.map((m) => (
                <Bubble key={m.id} m={m} />
              ))}
              {waiting && (
                <div className="flex items-center gap-2 px-2 text-sm text-muted">
                  <Loader2 className="size-4 animate-spin" aria-hidden /> Thinking…
                </div>
              )}
            </div>

            {messages.length < 3 && !waiting && (
              <div className="flex gap-2 overflow-x-auto px-3 pt-2">
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
              className="safe-bottom flex items-end gap-2 border-t border-line px-3 pt-3"
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
      )}
    </>
  );
}

function Bubble({ m }: { m: Msg }) {
  const mine = m.role === "user";
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
