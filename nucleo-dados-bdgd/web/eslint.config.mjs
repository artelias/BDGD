import next from "eslint-config-next";

const config = [
  ...next,
  { ignores: ["out/**", ".next/**", "public/**", "playwright-report/**", "test-results/**"] },
];
export default config;
