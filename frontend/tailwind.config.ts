import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f4f5f7",
          100: "#e7e9ed",
          200: "#c5cad3",
          300: "#a1a8b6",
          400: "#6c7587",
          500: "#3f4757",
          600: "#2c3344",
          700: "#1f2533",
          800: "#161b26",
          900: "#0e121a",
        },
        accent: { DEFAULT: "#0ea5e9", dark: "#0284c7" },
        warn: { DEFAULT: "#f59e0b" },
        critical: { DEFAULT: "#ef4444" },
        success: { DEFAULT: "#10b981" },
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas"],
      },
    },
  },
  plugins: [],
};

export default config;
