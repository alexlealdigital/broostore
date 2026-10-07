/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#EFF6FF',
          100: '#DBEAFE',
          200: '#BFDBFE',
          300: '#93C5FD',
          400: '#60A5FA',
          500: '#3B82F6',
          600: '#2563EB',
          700: '#1E40AF',
          800: '#1E3A8A',
          900: '#172554',
        },
        accent: {
          50: '#FFFBEB',
          100: '#FEF3C7',
          400: '#FBBF24',
          500: '#F59E0B',
          600: '#D97706',
          700: '#B45309',
        },
        ink: {
          DEFAULT: '#111827',
          soft: '#374151',
          muted: '#6B7280',
        },
        surface: {
          DEFAULT: '#F9FAFB',
          alt: '#F3F4F6',
          line: '#E5E7EB',
        },
      },
      fontFamily: {
        sans: ['Inter Variable', 'Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(17,24,39,.05), 0 1px 3px rgba(17,24,39,.06)',
        'card-hover': '0 10px 25px -5px rgba(30,64,175,.15), 0 4px 10px -4px rgba(17,24,39,.08)',
        pop: '0 20px 40px -12px rgba(17,24,39,.25)',
      },
      keyframes: {
        shimmer: { '100%': { transform: 'translateX(100%)' } },
        'fade-in': { from: { opacity: '0', transform: 'translateY(4px)' }, to: { opacity: '1', transform: 'none' } },
      },
      animation: {
        'fade-in': 'fade-in .25s ease-out both',
      },
    },
  },
  plugins: [],
};
