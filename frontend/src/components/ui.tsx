"use client";

import clsx from "clsx";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import Image from "next/image";
import { forwardRef, useState } from "react";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={clsx("rounded-[var(--radius-card)] border-2 border-forest bg-surface p-5", className)} {...props} />;
}

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "forest" | "ghost" | "outline" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading, className, children, disabled, ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-full font-semibold transition active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forest",
        {
          "bg-primary text-primary-ink hover:brightness-95": variant === "primary",
          "bg-forest text-forest-ink hover:brightness-110": variant === "forest",
          "bg-transparent text-ink hover:bg-surface-2": variant === "ghost",
          "border border-line bg-surface text-ink hover:bg-surface-2": variant === "outline",
          "bg-danger text-white hover:brightness-110": variant === "danger",
          "h-9 px-4 text-sm": size === "sm",
          "h-11 px-5 text-[15px]": size === "md",
          "h-13 px-6 text-base": size === "lg",
        },
        className,
      )}
      {...props}
    >
      {loading && <Loader2 className="size-4 animate-spin" aria-hidden />}
      {children}
    </button>
  );
});

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement> & { label?: string }>(
  function Input({ label, className, id, type, ...props }, ref) {
    const inputId = id ?? props.name;
    const isPassword = type === "password";
    const [visible, setVisible] = useState(false);
    return (
      <label htmlFor={inputId} className="block">
        {label && <span className="mb-1.5 block text-sm font-medium text-ink-2">{label}</span>}
        <span className="relative block">
          <input
            ref={ref}
            id={inputId}
            type={isPassword && visible ? "text" : type}
            className={clsx(
              "h-12 w-full rounded-2xl border border-line bg-surface-2 px-4 text-[15px] text-ink outline-none transition placeholder:text-muted focus:border-forest focus:bg-surface",
              isPassword && "pr-12",
              className,
            )}
            {...props}
          />
          {isPassword && (
            <button
              type="button"
              onClick={() => setVisible((v) => !v)}
              aria-label={visible ? "Hide password" : "Show password"}
              aria-pressed={visible}
              className="absolute top-1/2 right-2 grid size-9 -translate-y-1/2 place-items-center rounded-full text-muted hover:bg-surface hover:text-ink"
            >
              {visible ? <EyeOff className="size-5" aria-hidden /> : <Eye className="size-5" aria-hidden />}
            </button>
          )}
        </span>
      </label>
    );
  },
);

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={clsx("size-5 animate-spin text-muted", className)} aria-label="Loading" />;
}

export function Logo({ size = 40, withName = true }: { size?: number; withName?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <Image src="/icons/icon-192.png" alt="" width={size} height={size} className="rounded-xl" priority />
      {withName && <span className="text-xl font-bold tracking-tight text-forest dark:text-primary">Bachat</span>}
    </span>
  );
}

export function ErrorText({ children }: { children: React.ReactNode }) {
  if (!children) return null;
  return (
    <p role="alert" className="rounded-2xl bg-danger/10 px-4 py-3 text-sm text-danger">
      {children}
    </p>
  );
}

export function Empty({ icon, title, body, action }: { icon: React.ReactNode; title: string; body: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 py-8 text-center">
      <div className="grid size-12 place-items-center rounded-2xl bg-surface-2 text-forest dark:text-primary">{icon}</div>
      <p className="font-semibold">{title}</p>
      <p className="max-w-xs text-sm text-muted">{body}</p>
      {action}
    </div>
  );
}
