"use client";

import { SectionPage } from "@/components/dashboard/SectionPage";
import { DealsCard } from "@/components/dashboard/sections";

export default function DealsPage() {
  return <SectionPage>{(d) => <DealsCard d={d} />}</SectionPage>;
}
