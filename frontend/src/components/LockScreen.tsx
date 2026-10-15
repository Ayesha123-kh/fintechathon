"use client";

import { Fingerprint, Lock } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api, errorText } from "@/lib/api";
import { authenticateWithPasskey, passkeySupported } from "@/lib/passkey";
import type { User } from "@/lib/session";
import { Button, ErrorText, Input, Logo } from "./ui";

export function LockScreen({
  user,
  hasPasskey,
  onUnlocked,
  onSignOut,
}: {
  user: User | null;
  hasPasskey: boolean;
  onUnlocked: (u: User) => void;
  onSignOut: () => void;
}) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<"" | "pw" | "bio">("");
  const tried = useRef(false);
  const canBio = hasPasskey && passkeySupported();

  const unlockBio = async () => {
    setBusy("bio");
    setError("");
    try {
      const res = await authenticateWithPasskey<{ user: User }>("unlock");
      onUnlocked(res.user);
    } catch (e) {
      if (!(e instanceof Error && e.name === "NotAllowedError")) setError(errorText(e));
    } finally {
      setBusy("");
    }
  };

  // Offer fingerprint / face straight away, like banking apps.
  useEffect(() => {
    if (canBio && !tried.current) {
      tried.current = true;
      unlockBio();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canBio]);

  const unlockPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy("pw");
    setError("");
    try {
      const res = await api<{ user: User }>("/auth/unlock", { method: "POST", json: { password } });
      onUnlocked(res.user);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy("");
    }
  };

  return (
    <main className="safe-bottom flex min-h-dvh flex-col items-center justify-center gap-6 px-4">
      <Logo size={56} withName={false} />
      <div className="text-center">
        <div className="mx-auto mb-3 grid size-12 place-items-center rounded-full bg-forest text-forest-ink">
          <Lock className="size-5" aria-hidden />
        </div>
        <h1 className="text-2xl font-bold">Locked for your safety</h1>
        <p className="mt-1 text-sm text-muted">
          {user?.full_name ? `${user.full_name.split(" ")[0]}, you` : "You"} were inactive for a while.
        </p>
      </div>
      <div className="w-full max-w-sm space-y-4 rounded-[var(--radius-card)] bg-surface p-5">
        {canBio && (
          <Button size="lg" className="w-full" onClick={unlockBio} loading={busy === "bio"}>
            <Fingerprint className="size-5" aria-hidden /> Unlock with fingerprint or face
          </Button>
        )}
        <form onSubmit={unlockPassword} className="space-y-3">
          <Input
            type="password"
            name="password"
            autoComplete="current-password"
            label={canBio ? "Or use your password" : "Password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <ErrorText>{error}</ErrorText>
          <Button type="submit" variant={canBio ? "outline" : "primary"} className="w-full" loading={busy === "pw"}>
            Unlock
          </Button>
        </form>
      </div>
      <button onClick={onSignOut} className="text-sm font-medium text-muted underline-offset-4 hover:underline">
        Not you? Sign out
      </button>
    </main>
  );
}
