"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { AuthShell } from "@/components/AuthShell";
import { Button, ErrorText, Input } from "@/components/ui";
import { api, errorText } from "@/lib/api";
import { type User, useSession } from "@/lib/session";

export default function SignUp() {
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { setUser, reload } = useSession();
  const router = useRouter();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (form.password.length < 8) return setError("Use at least 8 characters for your password.");
    setBusy(true);
    setError("");
    try {
      const res = await api<{ user: User }>("/auth/signup", { method: "POST", json: form });
      setUser(res.user);
      await reload();
      router.replace("/dashboard?chat=1");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });

  return (
    <AuthShell title="Start saving smarter" subtitle="Create an account. Your assistant will set everything up with you in a quick chat.">
      <form onSubmit={submit} className="space-y-4">
        <Input label="Full name" name="full_name" autoComplete="name" value={form.full_name} onChange={set("full_name")} required />
        <Input label="Email" type="email" name="email" autoComplete="email" value={form.email} onChange={set("email")} required />
        <Input label="Password" type="password" name="password" autoComplete="new-password" minLength={8}
          value={form.password} onChange={set("password")} required />
        <ErrorText>{error}</ErrorText>
        <Button type="submit" size="lg" className="w-full" loading={busy}>Create account</Button>
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
