import { Baby, Car, Gift, GraduationCap, Heart, Home, Laptop, Plane, Smartphone, Target, Umbrella, Gem } from "lucide-react";

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  car: Car, home: Home, plane: Plane, "graduation-cap": GraduationCap, heart: Heart, gift: Gift, phone: Smartphone,
  laptop: Laptop, ring: Gem, baby: Baby, umbrella: Umbrella, target: Target,
};

export function GoalIcon({ name, size = "md" }: { name: string; size?: "md" | "lg" }) {
  const Icon = ICONS[name] ?? Target;
  return (
    <span className={size === "lg" ? "grid size-14 place-items-center rounded-2xl bg-primary text-primary-ink" : "grid size-10 shrink-0 place-items-center rounded-xl bg-primary text-primary-ink"}>
      <Icon className={size === "lg" ? "size-7" : "size-5"} aria-hidden />
    </span>
  );
}
