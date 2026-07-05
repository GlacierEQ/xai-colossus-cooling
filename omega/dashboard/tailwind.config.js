/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{js,ts,jsx,tsx}', './components/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        apex: {
          blue:  '#00d4ff',
          cyan:  '#00ffff',
          dark:  '#0a0e1a',
          panel: '#0d1526',
          border:'#1e3a5f',
        }
      },
      fontFamily: { mono: ['JetBrains Mono', 'monospace'] }
    }
  },
  plugins: []
}
