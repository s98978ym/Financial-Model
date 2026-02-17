import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Warm design system
        cream: {
          50: '#FDFBF7',
          100: '#FAF6EF',
          200: '#F5F0EA',
          300: '#EDE6D9',
          400: '#DDD3C0',
        },
        sand: {
          100: '#F0E8DA',
          200: '#E0D3BE',
          300: '#C9B89A',
          400: '#B8A488',
          500: '#A08E70',
          600: '#8A7A5E',
        },
        dark: {
          800: '#24243A',
          900: '#1C1C2E',
          950: '#16162A',
        },
        gold: {
          300: '#F0D78C',
          400: '#E5C46B',
          500: '#D4A853',
          600: '#C09440',
        },
        // Confidence colors (unchanged for financial data)
        'conf-high': '#22c55e',
        'conf-mid': '#eab308',
        'conf-low': '#ef4444',
        // Source badge colors
        'src-doc': '#3b82f6',
        'src-infer': '#f59e0b',
        'src-default': '#9ca3af',
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.25rem',
        '4xl': '1.5rem',
      },
      boxShadow: {
        'warm-sm': '0 1px 3px rgba(140, 120, 80, 0.06)',
        'warm': '0 2px 8px rgba(140, 120, 80, 0.08)',
        'warm-md': '0 4px 16px rgba(140, 120, 80, 0.10)',
        'warm-lg': '0 8px 32px rgba(140, 120, 80, 0.12)',
      },
    },
  },
  plugins: [],
}
export default config
