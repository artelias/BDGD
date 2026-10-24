/** Exportação estática: o portal serve apenas JSON/GeoJSON agregados versionados (sem servidor, sem banco). */
const nextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  reactStrictMode: true,
  poweredByHeader: false,
  devIndicators: false,
};
export default nextConfig;
