import type { Metadata } from "next";
import { Suspense } from "react";
import { Explorar } from "@/components/pages/Explorar";

export const metadata: Metadata = { title: "Explorar ativos" };
export default function Page() { return <Suspense><Explorar /></Suspense>; }
