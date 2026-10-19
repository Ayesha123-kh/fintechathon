"use client";

import { SectionPage } from "@/components/dashboard/SectionPage";
import { BanksCard } from "@/components/dashboard/sections";

export default function BanksPage() {
  return <SectionPage>{(d) => <BanksCard d={d} />}</SectionPage>;
}
