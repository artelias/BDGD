/** Exportação estática: o portal serve apenas JSON/GeoJSON agregados versionados (sem servidor, sem banco). */
// Portão do Motor V2 (scripts/motor-v2-gate.mjs): só build de homologação ou preview da Vercel expõe o produto experimental.
const motorV2 = process.env.NEXT_PUBLIC_MOTOR_V2 === "homologacao" || process.env.VERCEL_ENV === "preview" ? "homologacao" : "";
const nextConfig = {
  output: "export",
  env: { NEXT_PUBLIC_MOTOR_V2: motorV2 },
  trailingSlash: true,
  images: { unoptimized: true },
  reactStrictMode: true,
  poweredByHeader: false,
  devIndicators: false,
};
export default nextConfig;
