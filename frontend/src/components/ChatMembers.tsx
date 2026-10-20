import clsx from "clsx";
import { BadgePercent, type LucideIcon, PiggyBank, Sprout, TrendingUp, Wallet } from "lucide-react";

/*
  Who can post in a person's chat, each with their own avatar and name colour, like a WhatsApp group: their four
  advisors and the app itself (notifications). The desks that crawl deals and watch markets never post here.
  Name colours keep at least 4.5:1 contrast on the thread's background in light and dark mode.
*/
export const MEMBERS = {
  assistant: { name: "Finance Assistant", icon: Wallet, avatar: "bg-forest text-primary", nameColor: "text-forest dark:text-primary" },
  savings: { name: "Savings Coach", icon: PiggyBank, avatar: "bg-cat-2 text-white", nameColor: "text-[#2f6b5c] dark:text-cat-3" },
  deals: { name: "Deals Advisor", icon: BadgePercent, avatar: "bg-deal text-white", nameColor: "text-[#a8432c] dark:text-alert" },
  investment: { name: "Investment Advisor", icon: TrendingUp, avatar: "bg-[#5b5f97] text-white", nameColor: "text-[#4b4f86] dark:text-[#b4b7e6]" },
  app: { name: "Saving", icon: Sprout, avatar: "bg-primary text-forest", nameColor: "text-forest dark:text-primary" },
} satisfies Record<string, { name: string; icon: LucideIcon; avatar: string; nameColor: string }>;

export type MemberKey = keyof typeof MEMBERS;
const ADVISORS = (Object.keys(MEMBERS) as MemberKey[]).filter((k) => k !== "app");

/** Who sent a message: notifications and app messages are "app", otherwise the advisor named in `sender`. */
export function memberOf(m: { sender?: string | null; kind?: string; role?: string }): MemberKey {
  if (m.kind === "notification" || m.role === "system") return "app";
  const name = (m.sender ?? "").toLowerCase();
  return ADVISORS.find((k) => name.startsWith(MEMBERS[k].name.toLowerCase())) ?? "assistant";
}

const SIZES = { xs: ["size-6", "size-3"], sm: ["size-8", "size-4"], lg: ["size-11", "size-5"] } as const;

export function MemberAvatar({ who, size = "sm", className }: { who: MemberKey; size?: keyof typeof SIZES; className?: string }) {
  const { icon: Icon, avatar } = MEMBERS[who];
  return (
    <span aria-hidden className={clsx("grid shrink-0 place-items-center rounded-full", avatar, SIZES[size][0], className)}>
      <Icon className={SIZES[size][1]} strokeWidth={2.25} />
    </span>
  );
}

/** A group's picture: the members' avatars overlapping, like a WhatsApp group with several people. */
export function GroupAvatar({ members }: { members: MemberKey[] }) {
  return (
    <span aria-hidden className="flex -space-x-3">
      {members.slice(0, 3).map((m) => <MemberAvatar key={m} who={m} className="ring-2 ring-surface" />)}
    </span>
  );
}
