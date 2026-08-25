/** Tailwind config for the blog theme.
 *  Rebuild the stylesheet after changing classes in _layouts/_includes:
 *    ./script/build-css.sh
 */
module.exports = {
  content: [
    './_layouts/**/*.html',
    './_includes/**/*.html',
    './assets/js/**/*.js',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        serif: ['"Instrument Serif"', 'ui-serif', 'Georgia', 'serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      colors: {
        ink: '#0a0a0a',
        paper: '#f6f5f2',
      },
    },
  },
  safelist: [
    // Applied at runtime by assets/js/theme.js (TOC scroll-spy, back-to-top).
    'font-medium', 'text-ink', 'text-ink/55', 'pl-4', 'hidden', 'flex',
  ],
}
