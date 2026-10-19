"use client";

import { SectionPage } from "@/components/dashboard/SectionPage";
import { SpendingCard } from "@/components/dashboard/sections";

export default function SpendingPage() {
  return <SectionPage>{(d) => <SpendingCard d={d} />}</SectionPage>;
}
