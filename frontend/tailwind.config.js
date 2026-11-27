/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'Inter',
          '-apple-system',
          'BlinkMacSystemFont',
          '"SF Pro Text"',
          '"Segoe UI"',
          'Roboto',
          'system-ui',
          'sans-serif',
        ],
        mono: [
          '"SF Mono"',
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'Monaco',
          'Consolas',
          'monospace',
        ],
      },
      colors: {
        apple: {
          bg: 'var(--bg-primary)',
          sidebar: 'var(--bg-sidebar)',
          surface: 'var(--bg-surface)',
          elevated: 'var(--bg-elevated)',
          hover: 'var(--bg-hover)',
          ink: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          tertiary: 'var(--text-tertiary)',
          blue: 'var(--accent-blue)',
          blueHover: 'var(--accent-blue-hover)',
          border: 'var(--border-subtle)',
          borderStrong: 'var(--border-strong)',
        },
      },
      borderRadius: {
        apple: '10px',
        'apple-lg': '12px',
        'apple-sm': '8px',
      },
      boxShadow: {
        'apple-sm': '0 1px 2px rgba(0, 0, 0, 0.06)',
        'apple-md': '0 6px 24px rgba(0, 0, 0, 0.14)',
        'apple-lg': '0 16px 48px rgba(0, 0, 0, 0.28)',
      },
    },
  },
  plugins: [],
};
