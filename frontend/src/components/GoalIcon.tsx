import { Baby, Car, Gift, GraduationCap, Heart, Home, Laptop, Plane, Smartphone, Target, Umbrella, Gem } from "lucide-react";

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  car: Car, home: Home, plane: Plane, "graduation-cap": GraduationCap, heart: Heart, gift: Gift, phone: Smartphone,
  laptop: Laptop, ring: Gem, baby: Baby, umbrella: Umbrella, target: Target,
};

// Words in a goal's name (English and Roman Urdu) that say which icon fits, for goals saved without a specific one.
const GUESSES: [RegExp, string][] = [
  [/\b(umrah|umra|hajj|haj|trip|travel|tour|vacation|holiday|flight|ticket|visa|abroad|safar)\b/, "plane"],
  [/\b(car|bike|motorcycle|vehicle|gaari|gari|scooty|rickshaw)\b/, "car"],
  [/\b(house|home|plot|flat|apartment|property|ghar|makan|rent|furniture)\b/, "home"],
  [/\b(wedding|marriage|shaadi|shadi|nikah|engagement|ring)\b/, "ring"],
  [/\b(laptop|computer|pc|macbook|tablet)\b/, "laptop"],
  [/\b(phone|mobile|iphone|samsung)\b/, "phone"],
  [/\b(school|fee|fees|degree|course|study|education|university|college|tuition|masters|ms|mba)\b/, "graduation-cap"],
  [/\b(baby|newborn|child|kids)\b/, "baby"],
  [/\b(emergency|rainy|insurance|safety|security|medical|health)\b/, "umbrella"],
  [/\b(gift|eid|birthday|anniversary|present)\b/, "gift"],
  [/\b(sadqah|sadqa|zakat|charity|donation|khairat)\b/, "heart"],
];

/** The icon key to use: the one saved with the goal, or, when that is just the default, one guessed from its name. */
export function goalIconKey(name: string, label = ""): string {
  if (name && name !== "target" && ICONS[name]) return name;
  const text = label.toLowerCase();
  return GUESSES.find(([re]) => re.test(text))?.[1] ?? "target";
}

/** `name` is the saved icon key; `label` is the goal's name, used to guess a better icon when none was chosen. */
export function GoalIcon({ name, label, size = "md" }: { name: string; label?: string; size?: "md" | "lg" }) {
  const Icon = ICONS[goalIconKey(name, label)] ?? Target;
  return (
    <span className={size === "lg" ? "grid size-14 place-items-center rounded-2xl bg-primary text-primary-ink" : "grid size-10 shrink-0 place-items-center rounded-xl bg-primary text-primary-ink"}>
      <Icon className={size === "lg" ? "size-7" : "size-5"} aria-hidden />
    </span>
  );
}

/** Bare icon for use inside a progress ring. */
export function GoalIconGlyph({ name, label, className = "size-5" }: { name: string; label?: string; className?: string }) {
  const Icon = ICONS[goalIconKey(name, label)] ?? Target;
  return <Icon className={`${className} text-forest dark:text-primary`} aria-hidden />;
}
