import type { NextConfig } from "next";
const config: NextConfig = {
  distDir: process.env.BEANY_PREVIEW === "1" ? ".next-preview" : process.env.BEANY_E2E === "1" ? ".next-e2e" : ".next",
};
export default config;
