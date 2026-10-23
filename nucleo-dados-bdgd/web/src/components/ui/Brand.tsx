import s from "./ui.module.css";

/** Marca do Núcleo: órbitas concêntricas em torno de um ponto — o dado no centro da rede. */
export function BrandMark({ size = 22 }: { size?: number }) {
  return (
    <svg className={s.brandMark} width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="10.25" stroke="currentColor" strokeWidth="1.5" opacity="0.32" />
      <path d="M12 1.75a10.25 10.25 0 0 1 10.25 10.25" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="12" cy="12" r="5.5" stroke="currentColor" strokeWidth="1.5" opacity="0.6" />
      <circle cx="12" cy="12" r="2.1" fill="currentColor" />
    </svg>
  );
}

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <span className={s.brand}>
      <BrandMark />
      {!compact && (
        <span className={s.brandText}>
          <span className={s.brandName}>Núcleo de Dados da BDGD</span>
          <span className={s.brandSub}>BDGD · agregados públicos 2025</span>
        </span>
      )}
    </span>
  );
}
