/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        apex: {
          black:  '#0a0a0a',
          dark:   '#111111',
          card:   '#1a1a1a',
          border: '#2a2a2a',
          cyan:   '#00d4ff',
          green:  '#00ff88',
          yellow: '#ffcc00',
          red:    '#ff3333',
          purple: '#9d4edd',
          ghost:  '#334155',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          from: { boxShadow: '0 0 5px #00d4ff33' },
          to:   { boxShadow: '0 0 20px #00d4ff88, 0 0 40px #00d4ff22' },
        }
      }
    },
  },
  plugins: [],
};
