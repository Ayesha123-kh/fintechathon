import { browserSupportsWebAuthn, startAuthentication, startRegistration } from "@simplewebauthn/browser";
import { api } from "./api";

export const passkeySupported = () => typeof window !== "undefined" && browserSupportsWebAuthn();

export async function registerPasskey(deviceName?: string) {
  const options = await api<Parameters<typeof startRegistration>[0]["optionsJSON"]>("/auth/webauthn/register/options", {
    method: "POST",
  });
  const credential = await startRegistration({ optionsJSON: options });
  await api("/auth/webauthn/register/verify", {
    method: "POST",
    json: { credential, device_name: deviceName ?? guessDevice() },
  });
}

/** purpose "login" signs in from scratch; "unlock" re-opens an idle-locked session. */
export async function authenticateWithPasskey<T>(purpose: "login" | "unlock", email?: string): Promise<T> {
  const options = await api<Parameters<typeof startAuthentication>[0]["optionsJSON"]>("/auth/webauthn/options", {
    method: "POST",
    json: { purpose, email: email || null },
  });
  const credential = await startAuthentication({ optionsJSON: options });
  return api<T>("/auth/webauthn/verify", { method: "POST", json: { credential, challenge: options.challenge } });
}

function guessDevice(): string {
  const ua = navigator.userAgent;
  if (/iPhone/.test(ua)) return "iPhone";
  if (/iPad/.test(ua)) return "iPad";
  if (/Android/.test(ua)) return "Android phone";
  if (/Mac/.test(ua)) return "Mac";
  if (/Windows/.test(ua)) return "Windows PC";
  return "This device";
}
