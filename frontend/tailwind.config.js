/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          900: '#0a0a0f',
          800: '#111118',
          700: '#1a1a24',
          600: '#252532',
          500: '#32324a',
        },
        neon: {
          purple: '#7c3aed',
          blue:   '#2563eb',
          cyan:   '#06b6d4',
          glow:   '#a78bfa',
        }
      },
      boxShadow: {
        'neon-sm': '0 0 8px rgba(124, 58, 237, 0.4)',
        'neon-md': '0 0 20px rgba(124, 58, 237, 0.5)',
        'neon-lg': '0 0 40px rgba(124, 58, 237, 0.3)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}