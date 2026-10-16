"use client";

import { Fingerprint } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AuthShell } from "@/components/AuthShell";
import { Button, ErrorText, Input } from "@/components/ui";
import { api, errorText } from "@/lib/api";
import { authenticateWithPasskey, passkeySupported } from "@/lib/passkey";
import { type User, useSession } from "@/lib/session";

export default function SignIn() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<"" | "pw" | "bio">("");
  const { setUser, reload } = useSession();
  const [canPasskey, setCanPasskey] = useState(false);
  useEffect(() => setCanPasskey(passkeySupported()), []);
  const router = useRouter();

  const done = async (u: User) => {
    setUser(u);
    await reload();
    router.replace("/dashboard");
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy("pw");
    setError("");
    try {
      const res = await api<{ user: User }>("/auth/signin", { method: "POST", json: { email, password } });
      await done(res.user);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy("");
    }
  };

  const bio = async () => {
    setBusy("bio");
    setError("");
    try {
      const res = await authenticateWithPasskey<{ user: User }>("login", email);
      await done(res.user);
    } catch (err) {
      if (!(err instanceof Error && err.name === "NotAllowedError")) setError(errorText(err));
    } finally {
      setBusy("");
    }
  };

  return (
    <AuthShell title="Welcome back" subtitle="Sign in to see your savings and goals.">
      <form onSubmit={submit} className="space-y-4">
        <Input label="Email" type="email" name="email" autoComplete="username webauthn" value={email}
          onChange={(e) => setEmail(e.target.value)} required />
        <Input label="Password" type="password" name="password" autoComplete="current-password" value={password}
          onChange={(e) => setPassword(e.target.value)} required />
        <div className="flex justify-end">
          <Link href="/forgot-password" className="text-sm font-medium text-forest underline-offset-4 hover:underline dark:text-primary">
            Forgot password?
          </Link>
        </div>
        <ErrorText>{error}</ErrorText>
        <Button type="submit" size="lg" className="w-full" loading={busy === "pw"}>Sign in</Button>
      </form>
      {canPasskey && (
        <>
          <div className="my-5 flex items-center gap-3 text-xs text-muted">
            <span className="h-px flex-1 bg-line" /> or <span className="h-px flex-1 bg-line" />
          </div>
          <Button variant="outline" size="lg" className="w-full" onClick={bio} loading={busy === "bio"}>
            <Fingerprint className="size-5" aria-hidden /> Fingerprint or face
          </Button>
        </>
      )}
      <p className="mt-6 text-center text-sm text-muted">
        New here?{" "}
        <Link href="/signup" className="font-semibold text-forest underline-offset-4 hover:underline dark:text-primary">
          Create an account
        </Link>
      </p>
    </AuthShell>
  );
}
