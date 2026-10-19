"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Logo, Spinner } from "@/components/ui";
import { useSession } from "@/lib/session";

export default function Home() {
  const { status, user } = useSession();
  const router = useRouter();
  useEffect(() => {
    if (status === "active") router.replace(user?.role === "admin" ? "/admin" : "/dashboard");
    if (status === "none") router.replace("/signin");
  }, [status, user, router]);
  return (
    <main className="grid min-h-dvh place-items-center">
      <div className="flex flex-col items-center gap-4">
        <Logo size={56} />
        <Spinner />
      </div>
    </main>
  );
}
