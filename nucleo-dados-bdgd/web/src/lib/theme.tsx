"use client";
import { createContext, useContext, useLayoutEffect, type ReactNode } from "react";
import { useMediaQuery, useStoredValue } from "./hooks";

export type ThemePref = "system" | "light" | "dark";
type Resolved = "light" | "dark";
const KEY = "nucleo-bdgd-tema";

/** Script inline executado antes da pintura: aplica o tema salvo ou o do sistema, sem flash. */
export const THEME_BOOT = `(function(){try{var p=localStorage.getItem('${KEY}')||'system';var d=p==='dark'||(p==='system'&&matchMedia('(prefers-color-scheme: dark)').matches);document.documentElement.dataset.theme=d?'dark':'light';}catch(e){document.documentElement.dataset.theme='light';}})();`;

const Ctx = createContext<{ pref: ThemePref; resolved: Resolved; setPref: (p: ThemePref) => void }>({ pref: "system", resolved: "light", setPref: () => {} });

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [stored, setStored] = useStoredValue(KEY, "system");
  const pref: ThemePref = stored === "light" || stored === "dark" ? stored : "system";
  const systemDark = useMediaQuery("(prefers-color-scheme: dark)");
  const resolved: Resolved = pref === "dark" || (pref === "system" && systemDark) ? "dark" : "light";
  // Sincroniza o DOM (sistema externo) com o estado do React num efeito de LAYOUT: o React roda todos os efeitos de layout
  // antes dos efeitos comuns, e os dos filhos antes dos do pai. Com useEffect, o mapa e os gráficos (filhos) liam as
  // variáveis CSS do tema anterior ao recolorir, e o mapa ficava com o fundo de um tema e as áreas de outro.
  useLayoutEffect(() => { document.documentElement.dataset.theme = resolved; }, [resolved]);
  return <Ctx.Provider value={{ pref, resolved, setPref: setStored }}>{children}</Ctx.Provider>;
}

export const useTheme = () => useContext(Ctx);
export const useReducedMotion = () => useMediaQuery("(prefers-reduced-motion: reduce)");
