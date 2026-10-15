import { Logo } from "./ui";

export function AuthShell({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return (
    <main className="safe-bottom mx-auto flex min-h-dvh w-full max-w-md flex-col justify-center gap-6 px-4 py-10 md:max-w-lg">
      <Logo />
      <div>
        <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
        <p className="mt-1.5 text-muted">{subtitle}</p>
      </div>
      <div className="rounded-[var(--radius-card)] bg-surface p-5 md:p-7">{children}</div>
    </main>
  );
}
