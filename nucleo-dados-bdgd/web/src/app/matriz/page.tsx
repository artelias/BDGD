import type { Metadata } from "next";
import { Suspense } from "react";
import { Matriz } from "@/components/pages/Matriz";

export const metadata: Metadata = { title: "Matriz nacional" };
export default function Page() { return <Suspense><Matriz /></Suspense>; }
