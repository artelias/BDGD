import Link from "next/link";

export default function NotFound() {
  return (
    <div style={{ display: "grid", placeItems: "center", minHeight: "50vh", textAlign: "center", gap: 10 }}>
      <div>
        <div className="eyebrow">404</div>
        <h1 className="title" style={{ marginTop: 8 }}>Página não encontrada</h1>
        <p className="muted" style={{ marginTop: 8 }}>O endereço não existe neste portal.</p>
        <p style={{ marginTop: 16 }}><Link href="/" style={{ color: "var(--accent)" }}>Voltar ao Panorama</Link></p>
      </div>
    </div>
  );
}
