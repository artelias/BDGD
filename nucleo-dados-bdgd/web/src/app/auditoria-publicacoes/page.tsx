import type { Metadata } from "next";
import { PublicacoesAuditadas } from "@/components/pages/PublicacoesAuditadas";

export const metadata: Metadata = { title: "Auditoria de publicações BDGD" };

export default function Page() {
  return (
    <main>
      <PublicacoesAuditadas />
    </main>
  );
}
