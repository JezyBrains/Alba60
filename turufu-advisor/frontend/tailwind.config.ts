import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        game: {
          bg: "#080A0F",
          surface: "#121620",
          glass: "rgba(18, 22, 32, 0.65)",
          glassHover: "rgba(28, 34, 48, 0.85)",
          border: "rgba(255, 255, 255, 0.08)",
        },
        felt: {
          DEFAULT: "#154D30",
          dark: "#0B301D",
          edge: "#051A0E",
        },
        suit: {
          red: "#FF2A55",
          redDim: "rgba(255, 42, 85, 0.15)",
          black: "#2A2D34",
          blackDim: "rgba(42, 45, 52, 0.4)",
        },
        oracle: {
          glow: "#00FF9D",
          glowDim: "rgba(0, 255, 157, 0.2)",
          danger: "#FF2A55",
          mrithi: "#FFB800",
        },
        ink: {
          DEFAULT: "#FFFFFF",
          muted: "#A1A1AA",
          dim: "#52525B",
        },
      },
      fontFamily: {
        sans: ['"Inter"', "system-ui", "-apple-system", "sans-serif"],
      },
      borderRadius: {
        card: "0.75rem",
      },
      boxShadow: {
        glass: "0 8px 32px 0 rgba(0, 0, 0, 0.5)",
        glassInner: "inset 0 1px 0 0 rgba(255, 255, 255, 0.1)",
        neon: "0 0 15px rgba(0, 255, 157, 0.5)",
        neonDanger: "0 0 15px rgba(255, 42, 85, 0.5)",
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'glass-gradient': 'linear-gradient(135deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.01) 100%)',
      },
      keyframes: {
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        }
      }
    },
  },
  plugins: [],
};

export default config;
