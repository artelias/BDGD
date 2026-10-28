import type { Metadata } from "next";
import Link from "next/link";
import { PublicacoesAuditadas } from "@/components/pages/PublicacoesAuditadas";

export const metadata: Metadata = { title: "Auditoria das publicações BDGD" };

export default function Page() {
  return (
    <>
      <p className="caption"><Link href="/evolucao/">Voltar à evolução histórica</Link> · documentação técnica</p>
      <PublicacoesAuditadas />
    </>
  );
}
