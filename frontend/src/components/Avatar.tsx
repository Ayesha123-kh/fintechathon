"use client";

import clsx from "clsx";
import { ImagePlus, Loader2 } from "lucide-react";
import Image from "next/image";
import { useRef, useState } from "react";
import useSWR from "swr";
import { ApiError, api, errorText, fetcher } from "@/lib/api";
import { squarePhoto } from "@/lib/avatar";
import { AVATAR_MAX_BYTES, AVATAR_MAX_INPUT_BYTES } from "@/lib/limits";
import { useSession } from "@/lib/session";

/** The signed-in person's optional profile photo URL, or null (none set, or an admin account). */
export function useMyAvatar() {
  const { status, user } = useSession();
  const { data, mutate } = useSWR<{ avatar_version?: number | null }>(
    status === "active" && user?.role !== "admin" ? "/me" : null, fetcher);
  return { url: data?.avatar_version ? `/api/me/avatar?v=${data.avatar_version}` : null, refresh: mutate };
}

export function UserPhoto({ src, size = 32, className }: { src: string; size?: number; className?: string }) {
  return (
    <Image src={src} alt="" width={size} height={size} unoptimized
      className={clsx("shrink-0 rounded-full object-cover", className)} style={{ width: size, height: size }} />
  );
}

/** Settings: name and email, with a dotted circle to upload an optional profile photo (regular users only). */
export function ProfileCard() {
  const { user } = useSession();
  const canPhoto = user?.role !== "admin"; // the photo is shown in the assistant chat, which admins don't have
  const { url, refresh } = useMyAvatar();
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const upload = async (file?: File) => {
    if (!file) return;
    setError("");
    // The same rules the server applies, checked first so nothing is uploaded only to be refused.
    if (!/^image\/(jpeg|png|webp|heic|heif|gif|avif|bmp)$/.test(file.type)) {
      setError("Choose a photo (JPEG, PNG or WebP).");
      if (input.current) input.current.value = "";
      return;
    }
    if (file.size > AVATAR_MAX_INPUT_BYTES) {
      setError(`That photo is over ${AVATAR_MAX_INPUT_BYTES / 1024 / 1024} MB. Choose a smaller one.`);
      if (input.current) input.current.value = "";
      return;
    }
    setBusy(true);
    try {
      const photo = await squarePhoto(file);
      if (photo.size > AVATAR_MAX_BYTES) throw new ApiError(413, "avatar_too_large");
      const form = new FormData();
      form.append("image", photo, "avatar");
      await api("/me/avatar", { method: "POST", body: form });
      await refresh();
    } catch (e) {
      setError(e instanceof ApiError ? errorText(e) : "Couldn't read that photo. Try a JPEG or PNG.");
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  };

  const remove = async () => {
    setBusy(true);
    setError("");
    try {
      await api("/me/avatar", { method: "DELETE" });
      await refresh();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex items-center gap-4 rounded-2xl bg-surface-2 p-4">
      {canPhoto && (
        <>
          <button type="button" onClick={() => input.current?.click()} disabled={busy}
            aria-label={url ? "Change profile photo" : "Upload a profile photo (optional)"}
            title={url ? "Change profile photo" : "Upload a profile photo (optional)"}
            className={clsx("relative grid size-14 shrink-0 place-items-center overflow-hidden rounded-full transition",
              url ? "hover:brightness-90"
                : "border-2 border-dotted border-muted text-muted hover:border-forest hover:text-forest dark:hover:border-primary dark:hover:text-primary")}>
            {url ? <UserPhoto src={url} size={56} /> : <ImagePlus className="size-6" aria-hidden />}
            {busy && (
              <span className="absolute inset-0 grid place-items-center bg-surface-2/70">
                <Loader2 className="size-5 animate-spin text-ink" aria-label="Saving photo" />
              </span>
            )}
          </button>
          <input ref={input} type="file" accept="image/jpeg,image/png,image/webp,image/heic,image/heif" className="hidden"
            onChange={(e) => upload(e.target.files?.[0])} />
        </>
      )}
      <div className="min-w-0 flex-1">
        <p className="truncate font-semibold">{user?.full_name}</p>
        <p className="truncate text-sm text-muted">{user?.email}</p>
        {canPhoto && url && !busy && (
          <button type="button" onClick={remove} className="mt-1 text-xs font-semibold text-muted hover:text-danger">
            Remove photo
          </button>
        )}
        {error && <p className="mt-1 text-xs text-danger" role="alert">{error}</p>}
      </div>
    </div>
  );
}
