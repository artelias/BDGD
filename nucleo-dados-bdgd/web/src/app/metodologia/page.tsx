import type { Metadata } from "next";
import { Suspense } from "react";
import { Metodologia } from "@/components/pages/Metodologia";

export const metadata: Metadata = { title: "Metodologia e qualidade" };
export default function Page() { return <Suspense><Metodologia /></Suspense>; }
