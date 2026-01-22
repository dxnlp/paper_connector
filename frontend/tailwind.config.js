/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        hf: {
          yellow: '#FFD21E',
          orange: '#FF9D00',
          dark: '#1a1a1a',
          gray: '#374151',
        }
      }
    },
  },
  plugins: [],
}
