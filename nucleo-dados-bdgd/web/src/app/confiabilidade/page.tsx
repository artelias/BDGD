import type { Metadata } from "next";
import { Suspense } from "react";
import { Confiabilidade } from "@/components/confiabilidade/Confiabilidade";

export const metadata: Metadata = { title: "Confiabilidade | DEC/FEC × infraestrutura" };
export default function Page() { return <Suspense><Confiabilidade /></Suspense>; }
