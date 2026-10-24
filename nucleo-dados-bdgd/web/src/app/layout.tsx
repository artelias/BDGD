import type { Metadata, Viewport } from "next";
import { Suspense, type ReactNode } from "react";
import { AppShell } from "@/components/shell/AppShell";
import { ToastProvider } from "@/components/ui/Feedback";
import { DataProvider } from "@/lib/data-context";
import { THEME_BOOT, ThemeProvider } from "@/lib/theme";
import "maplibre-gl/dist/maplibre-gl.css";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Núcleo de Dados da BDGD", template: "%s · Núcleo de Dados da BDGD" },
  description: "Agregados públicos da Base de Dados Geográfica da Distribuidora (BDGD/ANEEL), data-base 31/12/2025: áreas de atuação, ativos por entidade, grupos econômicos e comparações. Desenvolvido por Arthur Henrique Elias de Lima.",
  authors: [{ name: "Arthur Henrique Elias de Lima", url: "mailto:Arthur.henrique.elias@gmail.com" }],
  applicationName: "Núcleo de Dados da BDGD",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [{ media: "(prefers-color-scheme: light)", color: "#f4f4f1" }, { media: "(prefers-color-scheme: dark)", color: "#0d0e10" }],
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT }} />
        <link rel="icon" href="/icon.svg" type="image/svg+xml" />
      </head>
      <body>
        <ThemeProvider>
          <DataProvider>
            <ToastProvider>
              <Suspense>
                <AppShell>{children}</AppShell>
              </Suspense>
            </ToastProvider>
          </DataProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
