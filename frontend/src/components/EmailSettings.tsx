"use client";

import { CheckCircle2, Mail, RefreshCw, ShieldCheck, Trash2 } from "lucide-react";
import { useState } from "react";
import useSWR from "swr";
import { api, errorText, fetcher } from "@/lib/api";
import { Button, ErrorText, Spinner } from "./ui";

type Conn = { id: string; email: string; status: string; last_error: string | null; last_synced_at: string | null; transactions_found: number };

const ERRORS: Record<string, string> = {
  cancelled: "Connection was cancelled.",
  expired: "That took too long. Please try again.",
  exchange_failed: "Google didn't accept the connection. Please try again.",
  access_denied: "You didn't allow access, so nothing was connected.",
};

/** Gmail connection, shown inside the Settings sheet. `result` comes back from the Google sign-in redirect. */
export function EmailSettings({ result }: { result?: { connected?: boolean; error?: string } }) {
  const { data, mutate } = useSWR<{ configured: boolean; connections: Conn[] }>("/email/connections", fetcher);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState(result?.error ? ERRORS[result.error] ?? "Something went wrong." : "");

  const connect = async () => {
    setBusy("connect");
    setError("");
    try {
      const { url } = await api<{ url: string }>("/email/google/start", { method: "POST" });
      window.location.href = url;
    } catch (e) {
      setError(errorText(e));
      setBusy("");
    }
  };

  const act = async (id: string, kind: "sync" | "remove") => {
    setBusy(id + kind);
    try {
      if (kind === "sync") await api(`/email/connections/${id}/sync`, { method: "POST" });
      else await api(`/email/connections/${id}`, { method: "DELETE" });
      mutate();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-ink-2">Email connection</p>
      {result?.connected && (
        <p className="flex items-center gap-2 rounded-2xl bg-primary/40 px-3 py-2.5 text-sm font-medium">
          <CheckCircle2 className="size-4 shrink-0" aria-hidden /> Gmail connected. Reading your recent bank alerts now.
        </p>
      )}
      <ErrorText>{error}</ErrorText>
      <div className="flex items-start gap-2 text-xs text-ink-2">
        <ShieldCheck className="mt-0.5 size-4 shrink-0 text-forest dark:text-primary" aria-hidden />
        <p>Read-only. Only alert emails from the banks you told us about are read. Disconnect anytime.</p>
      </div>
      {!data ? <Spinner /> : (
        <>
          {data.connections.map((c) => (
            <div key={c.id} className="rounded-2xl border-2 border-forest bg-surface-2 p-3 dark:border-primary">
              <div className="flex items-center gap-2">
                <Mail className="size-4 shrink-0 text-muted" aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold">{c.email}</p>
                  <p className="text-[11px] text-muted">
                    {c.status === "active" ? `${c.transactions_found} transactions found` : "Needs reconnecting"}
                    {c.last_synced_at && ` · checked ${new Date(c.last_synced_at).toLocaleString("en-PK", { hour: "numeric", minute: "2-digit", day: "numeric", month: "short" })}`}
                  </p>
                </div>
                <button aria-label="Check now" onClick={() => act(c.id, "sync")} className="grid size-8 place-items-center rounded-full hover:bg-hover">
                  <RefreshCw className={busy === c.id + "sync" ? "size-4 animate-spin" : "size-4"} />
                </button>
                <button aria-label={`Disconnect ${c.email}`} onClick={() => act(c.id, "remove")} className="grid size-8 place-items-center rounded-full text-danger hover:bg-hover">
                  <Trash2 className="size-4" />
                </button>
              </div>
              {c.last_error && <p className="mt-1.5 text-xs text-danger">{c.last_error}</p>}
            </div>
          ))}
          {data.configured ? (
            <Button variant="outline" className="w-full justify-start" onClick={connect} loading={busy === "connect"}>
              <Mail className="size-5" aria-hidden /> {data.connections.length ? "Connect another Gmail" : "Connect Gmail"}
            </Button>
          ) : (
            <p className="rounded-2xl bg-surface-2 p-3 text-xs text-muted">Gmail connection isn&apos;t configured on this server yet.</p>
          )}
        </>
      )}
    </div>
  );
}
