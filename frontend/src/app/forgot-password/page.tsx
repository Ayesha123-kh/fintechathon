"use client";

import { MailCheck } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { AuthShell } from "@/components/AuthShell";
import { Button, ErrorText, Input } from "@/components/ui";
import { api, errorText } from "@/lib/api";

function Request() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/auth/forgot", { method: "POST", json: { email } });
      setSent(true);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };
  if (sent)
    return (
      <AuthShell title="Check your email" subtitle="If an account exists for that address, a reset link is on its way.">
        <div className="flex flex-col items-center gap-3 py-4 text-center">
          <MailCheck className="size-10 text-forest dark:text-primary" aria-hidden />
          <p className="text-sm text-muted">The link works for 30 minutes. Check spam if you don&apos;t see it.</p>
          <Link href="/signin" className="font-semibold text-forest dark:text-primary">Back to sign in</Link>
        </div>
      </AuthShell>
    );
  return (
    <AuthShell title="Forgot password?" subtitle="Enter your email and we'll send you a reset link.">
      <form onSubmit={submit} className="space-y-4">
        <Input label="Email" type="email" name="email" autoComplete="email" maxLength={320} value={email} onChange={(e) => setEmail(e.target.value)} required />
        <ErrorText>{error}</ErrorText>
        <Button type="submit" size="lg" className="w-full" loading={busy}>Send reset link</Button>
      </form>
      <p className="mt-6 text-center text-sm">
        <Link href="/signin" className="font-semibold text-forest dark:text-primary">Back to sign in</Link>
      </p>
    </AuthShell>
  );
}

function Reset({ token }: { token: string }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== confirm) return setError("The passwords don't match.");
    setBusy(true);
    setError("");
    try {
      await api("/auth/reset", { method: "POST", json: { token, password } });
      router.replace("/signin?reset=1");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <AuthShell title="Choose a new password" subtitle="You'll be signed out on every device for safety.">
      <form onSubmit={submit} className="space-y-4">
        <Input label="New password" type="password" autoComplete="new-password" minLength={8} maxLength={128} value={password}
          onChange={(e) => setPassword(e.target.value)} required />
        <Input label="Confirm password" type="password" autoComplete="new-password" minLength={8} maxLength={128} value={confirm}
          onChange={(e) => setConfirm(e.target.value)} required />
        <ErrorText>{error}</ErrorText>
        <Button type="submit" size="lg" className="w-full" loading={busy}>Save password</Button>
      </form>
    </AuthShell>
  );
}

function ForgotInner() {
  const token = useSearchParams().get("token");
  return token ? <Reset token={token} /> : <Request />;
}

export default function ForgotPassword() {
  return (
    <Suspense>
      <ForgotInner />
    </Suspense>
  );
}
