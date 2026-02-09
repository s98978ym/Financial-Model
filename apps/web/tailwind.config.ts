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
        // Confidence colors
        'conf-high': '#22c55e',    // green-500
        'conf-mid': '#eab308',     // yellow-500
        'conf-low': '#ef4444',     // red-500
        // Source badge colors
        'src-doc': '#3b82f6',      // blue-500
        'src-infer': '#f59e0b',    // amber-500
        'src-default': '#9ca3af',  // gray-400
      },
    },
  },
  plugins: [],
}
export default config
