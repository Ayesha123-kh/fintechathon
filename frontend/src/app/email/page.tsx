"use client";

import { CheckCircle2, Mail, RefreshCw, ShieldCheck, Trash2 } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import useSWR from "swr";
import { AppShell } from "@/components/AppShell";
import { Button, Card, ErrorText, Spinner } from "@/components/ui";
import { api, errorText, fetcher } from "@/lib/api";

type Conn = { id: string; email: string; status: string; last_error: string | null; last_synced_at: string | null; transactions_found: number };

const ERRORS: Record<string, string> = {
  cancelled: "Connection was cancelled.",
  expired: "That took too long. Please try again.",
  exchange_failed: "Google didn't accept the connection. Please try again.",
  access_denied: "You didn't allow access, so nothing was connected.",
};

function EmailInner() {
  const params = useSearchParams();
  const { data, mutate } = useSWR<{ configured: boolean; connections: Conn[] }>("/email/connections", fetcher);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState(params.get("error") ? ERRORS[params.get("error")!] ?? "Something went wrong." : "");

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
    <div className="mx-auto max-w-2xl space-y-5">
      <div>
        <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Email connection</h1>
        <p className="text-sm text-muted">Track every bank transaction automatically from your alert emails.</p>
      </div>
      {params.get("connected") && (
        <p className="flex items-center gap-2 rounded-2xl bg-primary/40 px-4 py-3 text-sm font-medium">
          <CheckCircle2 className="size-5" aria-hidden /> Gmail connected. We&apos;re reading your recent bank alerts now.
        </p>
      )}
      <ErrorText>{error}</ErrorText>

      <Card className="space-y-4">
        <div className="flex items-start gap-3">
          <ShieldCheck className="mt-0.5 size-6 shrink-0 text-forest dark:text-primary" aria-hidden />
          <ul className="space-y-1.5 text-sm text-ink-2">
            <li><span className="font-semibold text-ink">Read-only.</span> We can never send, delete or change emails.</li>
            <li><span className="font-semibold text-ink">Bank alerts only.</span> We only open emails from the banks you told us about.</li>
            <li><span className="font-semibold text-ink">Disconnect anytime.</span> Access is revoked at Google immediately.</li>
          </ul>
        </div>
        {data && !data.configured ? (
          <p className="rounded-2xl bg-surface-2 p-4 text-sm text-muted">Gmail connection isn&apos;t configured on this server yet.</p>
        ) : (
          <Button size="lg" className="w-full" onClick={connect} loading={busy === "connect"}>
            <Mail className="size-5" aria-hidden /> Connect Gmail
          </Button>
        )}
      </Card>

      <Card>
        <h2 className="mb-3 font-bold">Connected inboxes</h2>
        {!data ? <Spinner /> : data.connections.length === 0 ? (
          <p className="py-2 text-sm text-muted">No inbox connected yet.</p>
        ) : (
          <ul className="space-y-3">
            {data.connections.map((c) => (
              <li key={c.id} className="rounded-2xl border border-primary bg-surface-2 p-4">
                <div className="flex items-center gap-3">
                  <Mail className="size-5 text-muted" aria-hidden />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-semibold">{c.email}</p>
                    <p className="text-xs text-muted">
                      {c.status === "active" ? `${c.transactions_found} transactions found` : "Needs reconnecting"}
                      {c.last_synced_at && ` · checked ${new Date(c.last_synced_at).toLocaleString("en-PK", { hour: "numeric", minute: "2-digit", day: "numeric", month: "short" })}`}
                    </p>
                  </div>
                  <button aria-label="Check now" onClick={() => act(c.id, "sync")} className="grid size-9 place-items-center rounded-full hover:bg-surface">
                    <RefreshCw className={busy === c.id + "sync" ? "size-4 animate-spin" : "size-4"} />
                  </button>
                  <button aria-label="Disconnect" onClick={() => act(c.id, "remove")} className="grid size-9 place-items-center rounded-full text-danger hover:bg-surface">
                    <Trash2 className="size-4" />
                  </button>
                </div>
                {c.last_error && <p className="mt-2 text-xs text-danger">{c.last_error}</p>}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

export default function EmailPage() {
  return (
    <AppShell>
      <Suspense>
        <EmailInner />
      </Suspense>
    </AppShell>
  );
}
