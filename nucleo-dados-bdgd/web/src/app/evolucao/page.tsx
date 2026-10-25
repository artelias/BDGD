import type { Metadata } from "next";
import { Evolucao } from "@/components/pages/Evolucao";

export const metadata: Metadata = { title: "Evolução histórica" };

export default function Page() {
  return <Evolucao />;
}
