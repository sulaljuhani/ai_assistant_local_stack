/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Dark theme colors (ChatGPT-inspired)
        bg: {
          primary: '#343541',
          secondary: '#40414f',
          hover: '#444654',
          light: '#f7f7f8',
        },
        text: {
          primary: '#ececf1',
          secondary: '#acacbe',
          light: '#2e2e2e',
        },
        accent: {
          green: '#10a37f',
          'green-hover': '#1a7f64',
          blue: '#19c37d',
        },
        border: '#565869',
        input: {
          bg: '#40414f',
          border: '#565869',
        },
        link: '#19c37d',
        error: '#ef4444',
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          'Helvetica',
          'Arial',
          'sans-serif',
        ],
      },
    },
  },
  plugins: [],
}
