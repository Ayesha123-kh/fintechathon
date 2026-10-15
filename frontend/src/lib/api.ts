// Fetch wrapper: same-origin cookies, CSRF header, silent token refresh and idle-lock signalling.

export class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(detail);
  }
}

type Listener = () => void;
const lockListeners = new Set<Listener>();
const logoutListeners = new Set<Listener>();
export function onLocked(fn: Listener): () => void {
  lockListeners.add(fn);
  return () => {
    lockListeners.delete(fn);
  };
}
export function onLoggedOut(fn: Listener): () => void {
  logoutListeners.add(fn);
  return () => {
    logoutListeners.delete(fn);
  };
}

let refreshing: Promise<boolean> | null = null;

async function refresh(): Promise<boolean> {
  refreshing ??= fetch("/api/auth/refresh", {
    method: "POST",
    credentials: "include",
    headers: { "x-requested-with": "bachat" },
  })
    .then((r) => {
      if (r.status === 423) lockListeners.forEach((fn) => fn());
      return r.ok;
    })
    .finally(() => setTimeout(() => (refreshing = null), 0));
  return refreshing;
}

export async function api<T = unknown>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const { json, headers, ...rest } = init;
  const doFetch = () =>
    fetch(`/api${path}`, {
      credentials: "include",
      ...rest,
      headers: {
        "x-requested-with": "bachat",
        ...(json !== undefined ? { "content-type": "application/json" } : {}),
        ...headers,
      },
      body: json !== undefined ? JSON.stringify(json) : rest.body,
    });

  let res = await doFetch();
  if (res.status === 401 && !path.startsWith("/auth/")) {
    if (await refresh()) res = await doFetch();
  }
  if (res.status === 423) {
    lockListeners.forEach((fn) => fn());
  }
  if (res.status === 401 && !path.startsWith("/auth/")) {
    logoutListeners.forEach((fn) => fn());
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {}
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const fetcher = <T,>(path: string) => api<T>(path);

const ERRORS: Record<string, string> = {
  invalid_credentials: "That email and password don't match.",
  email_taken: "An account with this email already exists. Try signing in.",
  too_many_attempts: "Too many attempts. Please wait a few minutes.",
  invalid_or_expired_token: "This reset link has expired. Request a new one.",
  account_disabled: "This account has been disabled. Contact support.",
  unknown_passkey: "This passkey isn't registered. Sign in with your password first.",
  slow_down: "You're sending messages too quickly.",
};

export function errorText(err: unknown): string {
  if (err instanceof ApiError) {
    const key = err.detail.split(":")[0];
    return ERRORS[key] ?? (err.status >= 500 ? "Something went wrong on our side. Please try again." : err.detail);
  }
  return "Network problem. Check your connection.";
}

export const rs = (v: number | string | null | undefined, opts: { compact?: boolean } = {}) => {
  const n = Number(v ?? 0);
  if (opts.compact && Math.abs(n) >= 100000) {
    if (Math.abs(n) >= 10000000) return `Rs. ${(n / 10000000).toFixed(1).replace(/\.0$/, "")} Cr`;
    return `Rs. ${(n / 100000).toFixed(1).replace(/\.0$/, "")} Lac`;
  }
  return `Rs. ${n.toLocaleString("en-PK", { maximumFractionDigits: 0 })}`;
};
