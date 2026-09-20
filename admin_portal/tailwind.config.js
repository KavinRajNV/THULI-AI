/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        kisan: {
          50: '#f0fdf0',
          100: '#dcfce7',
          200: '#bbf7d0',
          300: '#86efac',
          400: '#4ade80',
          500: '#22c55e',
          600: '#16a34a',
          700: '#15803d',
          800: '#166534',
          900: '#14532d',
        },
        earth: {
          50: '#fdf8f0',
          100: '#f5e6d0',
          200: '#e8cba0',
          300: '#d4a96e',
          400: '#c08a45',
          500: '#a67332',
          600: '#8a5d28',
          700: '#6d4820',
          800: '#533618',
          900: '#3a2610',
        },
      },
      fontFamily: {
        tamil: ['"Noto Sans Tamil"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
