"use client";

import { SectionPage } from "@/components/dashboard/SectionPage";
import { GoalsCard } from "@/components/dashboard/sections";

export default function GoalsPage() {
  return <SectionPage>{(d) => <GoalsCard goals={d.goals} showAll />}</SectionPage>;
}
