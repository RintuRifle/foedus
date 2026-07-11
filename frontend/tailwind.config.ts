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
        ink: "#08090C",
        surface: { DEFAULT: "#0E1015", 2: "#141720", 3: "#1B1F2B" },
        line: "rgba(212,168,83,0.14)",
        brass: { DEFAULT: "#D4A853", bright: "#F0C674", dim: "#8A6F35" },
        cream: "#EDE6D6",
        muted: "#8B867A",
        emerald: "#3DD68C",
        crimson: "#F0526A",
        azure: "#5CA8FF",
        amberwarn: "#E8A33D",
      },
      fontFamily: {
        display: ["var(--font-fraunces)", "Georgia", "serif"],
        sans: ["var(--font-plex)", "system-ui", "sans-serif"],
        mono: ["var(--font-plex-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        dossier: "0 24px 60px -18px rgba(0,0,0,0.75), 0 0 0 1px rgba(212,168,83,0.10)",
        glowbrass: "0 0 40px -8px rgba(212,168,83,0.35)",
      },
      keyframes: {
        rise: {
          from: { opacity: "0", transform: "translateY(18px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        scanline: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(400%)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.45" },
        },
      },
      animation: {
        rise: "rise 0.6s cubic-bezier(0.22,1,0.36,1) both",
        scanline: "scanline 2.4s linear infinite",
        pulseSoft: "pulseSoft 1.8s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
