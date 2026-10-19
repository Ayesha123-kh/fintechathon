export type ThemeChoice = "light" | "dark";
const KEY = "bachat-theme";

/** Light unless someone picked Dark in Settings (the device's dark mode is not followed). */
export function getTheme(): ThemeChoice {
  try {
    return localStorage.getItem(KEY) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

export function applyTheme(choice: ThemeChoice) {
  const root = document.documentElement;
  if (choice === "dark") root.dataset.theme = "dark";
  else delete root.dataset.theme;
  try {
    if (choice === "dark") localStorage.setItem(KEY, "dark");
    else localStorage.removeItem(KEY);
  } catch {}
}

/** Runs before first paint (inlined in <head>) so a saved Dark choice never flashes the light theme. */
export const THEME_BOOT_SCRIPT = `try{if(localStorage.getItem("${KEY}")==="dark")document.documentElement.dataset.theme="dark"}catch(e){}`;
