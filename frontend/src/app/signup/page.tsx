"use client";

import { MailCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AuthShell } from "@/components/AuthShell";
import { Button, ErrorText, Input } from "@/components/ui";
import { api, errorText } from "@/lib/api";
import { type User, useSession } from "@/lib/session";

type Pending = { email: string; resend_in: number };

export default function SignUp() {
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [pending, setPending] = useState<Pending | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.password.length < 8) return setError("Use at least 8 characters for your password.");
    setBusy(true);
    setError("");
    try {
      setPending(await api<Pending>("/auth/signup", { method: "POST", json: form }));
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });

  if (pending) return <VerifyCode pending={pending} onBack={() => setPending(null)} />;

  return (
    <AuthShell title="Start saving smarter" subtitle="Create an account. Your assistant will set everything up with you in a quick chat.">
      <form onSubmit={submit} className="space-y-4">
        <Input label="Full name" name="full_name" autoComplete="name" value={form.full_name} onChange={set("full_name")} required />
        <Input label="Email" type="email" name="email" autoComplete="email" value={form.email} onChange={set("email")} required />
        <Input label="Password" type="password" name="password" autoComplete="new-password" minLength={8}
          value={form.password} onChange={set("password")} required />
        <ErrorText>{error}</ErrorText>
        <Button type="submit" size="lg" className="w-full" loading={busy}>Continue</Button>
        <p className="text-xs text-muted">
          We never ask for card numbers, PINs or bank passwords. Bank emails are read only with your permission.
        </p>
      </form>
      <p className="mt-6 text-center text-sm text-muted">
        Already have an account?{" "}
        <Link href="/signin" className="font-semibold text-forest underline-offset-4 hover:underline dark:text-primary">Sign in</Link>
      </p>
    </AuthShell>
  );
}

function VerifyCode({ pending, onBack }: { pending: Pending; onBack: () => void }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);
  const [wait, setWait] = useState(pending.resend_in);
  const { setUser, reload } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (wait <= 0) return;
    const t = setTimeout(() => setWait((w) => w - 1), 1000);
    return () => clearTimeout(t);
  }, [wait]);

  const verify = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const res = await api<{ user: User }>("/auth/signup/verify", { method: "POST", json: { email: pending.email, code } });
      setUser(res.user);
      await reload();
      router.replace("/dashboard?chat=1");
    } catch (err) {
      setError(errorText(err));
      setBusy(false);
    }
  };

  const resend = async () => {
    setError("");
    setInfo("");
    try {
      const r = await api<Pending>("/auth/signup/resend", { method: "POST", json: { email: pending.email } });
      setWait(r.resend_in);
      setCode("");
      setInfo("A new code is on its way.");
    } catch (err) {
      setError(errorText(err));
    }
  };

  return (
    <AuthShell title="Check your email" subtitle={`We sent a 6-digit code to ${pending.email}.`}>
      <form onSubmit={verify} className="space-y-4">
        <div className="flex justify-center py-1"><MailCheck className="size-10 text-forest dark:text-primary" aria-hidden /></div>
        <Input label="Verification code" name="code" inputMode="numeric" autoComplete="one-time-code" maxLength={6}
          pattern="\d{6}" placeholder="123456" autoFocus value={code} className="text-center text-2xl tracking-[0.5em]"
          onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))} required />
        <ErrorText>{error}</ErrorText>
        {info && <p role="status" className="text-sm text-forest dark:text-primary">{info}</p>}
        <Button type="submit" size="lg" className="w-full" loading={busy} disabled={code.length !== 6}>Verify and create account</Button>
      </form>
      <div className="mt-5 flex items-center justify-between text-sm">
        <button type="button" onClick={onBack} className="font-semibold text-muted hover:text-ink">Use a different email</button>
        <button type="button" onClick={resend} disabled={wait > 0}
          className="font-semibold text-forest disabled:text-muted dark:text-primary">
          {wait > 0 ? `Resend in ${wait}s` : "Resend code"}
        </button>
      </div>
      <p className="mt-3 text-xs text-muted">The code works for 10 minutes. Check spam if you don&apos;t see it.</p>
    </AuthShell>
  );
}
