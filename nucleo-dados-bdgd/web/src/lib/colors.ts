/** Paleta de grupos econômicos verificados: matizes distintos com luminância controlada, calibrados por tema.
 *  "nao_confirmado" é neutro (e hachurado no mapa) para nunca sugerir agrupamento inexistente. */
export const GROUP_COLORS: Record<string, { light: string; dark: string }> = {
  energisa: { light: "#d07a22", dark: "#eb9a4d" },
  equatorial: { light: "#16857a", dark: "#3fb7a9" },
  neoenergia: { light: "#4f8f2c", dark: "#7cc25a" },
  cpfl: { light: "#2f62cf", dark: "#6f95f2" },
  enel: { light: "#8450c9", dark: "#ab84ee" },
  edp: { light: "#c63d55", dark: "#ee7187" },
  cemig: { light: "#1d8db8", dark: "#4fbbe3" },
  copel: { light: "#b8901a", dark: "#dcb84a" },
  celesc: { light: "#5e6f99", dark: "#94a3c9" },
  light: { light: "#a85a33", dark: "#d98a5f" },
  oliveira: { light: "#6c7f2e", dark: "#a4b95c" },
};
export const NEUTRAL = { light: "#b9bab4", dark: "#4a4d53" };

export function groupColor(id: string, theme: "light" | "dark") {
  return (GROUP_COLORS[id] ?? NEUTRAL)[theme];
}
