/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#030712', // slate-950
        card: '#0f172a',       // slate-900
        border: '#1e293b',     // slate-800
        primary: {
          DEFAULT: '#06b6d4',  // cyan-500
          foreground: '#ffffff',
        },
        attribution: {
          confirmed: '#10b981', // emerald-500
          likely: '#06b6d4',    // cyan-500
          possible: '#f59e0b',  // amber-500
          inconclusive: '#8b5cf6', // purple-500
          different: '#f43f5e', // rose-500
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [],
}
