import type { Metadata } from "next";
import { Suspense } from "react";
import { Comparar } from "@/components/pages/Comparar";

export const metadata: Metadata = { title: "Comparador" };
export default function Page() { return <Suspense><Comparar /></Suspense>; }
