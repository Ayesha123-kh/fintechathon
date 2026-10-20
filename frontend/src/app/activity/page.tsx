"use client";

import { SectionPage } from "@/components/dashboard/SectionPage";
import { ActivityCard } from "@/components/dashboard/sections";

export default function ActivityPage() {
  return <SectionPage>{(d) => <ActivityCard d={d} />}</SectionPage>;
}
