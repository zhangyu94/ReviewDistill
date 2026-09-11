import { defineConfig, presetWind4 } from 'unocss'

const themePreflight = String.raw`
:root {
  --ch-color-background: #ffffff;
  --ch-color-background-soft: #fafafa;
  --ch-color-background-muted: #f5f5f5;
  --ch-color-foreground: #171717;
  --ch-color-body: #4d4d4d;
  --ch-color-card: #ffffff;
  --ch-color-card-foreground: #171717;
  --ch-color-primary: #171717;
  --ch-color-primary-foreground: #ffffff;
  --ch-color-secondary: #f5f5f5;
  --ch-color-secondary-foreground: #171717;
  --ch-color-muted: #f5f5f5;
  --ch-color-muted-foreground: #888888;
  --ch-color-accent: #f5f5f5;
  --ch-color-accent-foreground: #171717;
  --ch-color-destructive: #ee0000;
  --ch-color-destructive-foreground: #ffffff;
  --ch-color-destructive-soft: #f7d4d6;
  --ch-color-border: #ebebeb;
  --ch-color-border-strong: #a1a1a1;
  --ch-color-input: #ebebeb;
  --ch-color-ring: #171717;
  --ch-color-link: #0070f3;
  --ch-color-link-deep: #0761d1;
  --ch-color-warning: #f5a623;
  --ch-color-warning-soft: #ffefcf;
  --ch-color-code-bg: #171717;
  --ch-color-code-fg: #f2f2f2;
  --ch-radius: 6px;
  --ch-radius-md: 8px;
  --ch-font-sans: "Geist", "Geist Sans", ui-sans-serif, system-ui, sans-serif;
  --ch-font-mono: "Geist Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, monospace;
  font-family: var(--ch-font-sans);
  line-height: 1.5;
  letter-spacing: -0.011em;
  color: var(--ch-color-foreground);
  background: var(--ch-color-background-soft);
  -webkit-font-smoothing: antialiased;
}

::selection {
  background: var(--ch-color-foreground);
  color: var(--ch-color-code-fg);
}

* { box-sizing: border-box; }
body { margin: 0; min-width: 320px; min-height: 100vh; }
#root { min-height: 100vh; }
button, input, textarea, select { font: inherit; color: inherit; }
button:not(:disabled) { cursor: pointer; }
button:disabled { cursor: not-allowed; }
a { color: var(--ch-color-link); }
a:hover { color: var(--ch-color-link-deep); }
code, kbd, pre { font-family: var(--ch-font-mono); }
`

const ringFocus
  = 'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ch-color-ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--ch-color-background)]'
const buttonBase
  = `inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-[4px] text-xs font-medium transition-colors disabled:pointer-events-none disabled:opacity-50 ${ringFocus}`

export default defineConfig({
  preflights: [{ getCSS: () => themePreflight }],
  // Two sizes: text-xs (12px) for UI chrome; ch-prose / text-sm (14px) for reading.
  shortcuts: [
    ['ch-muted-text', 'text-[var(--ch-color-muted-foreground)]'],
    ['ch-btn', `${buttonBase} h-6 px-2`],
    ['ch-btn-default', 'bg-[var(--ch-color-primary)] text-[var(--ch-color-primary-foreground)] hover:bg-black'],
    ['ch-btn-outline', 'border border-[var(--ch-color-border)] bg-[var(--ch-color-background)] text-[var(--ch-color-foreground)] hover:bg-[var(--ch-color-background-muted)]'],
    [
      'ch-chip',
      'inline-flex h-6 shrink-0 items-center rounded-[4px] border px-2 text-xs font-medium no-underline leading-none text-[var(--ch-color-body)] hover:text-[var(--ch-color-foreground)] hover:no-underline focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-[var(--ch-color-ring)]',
    ],
    [
      'ch-chip-idle',
      'border-[var(--ch-color-border)] bg-[var(--ch-color-background)] hover:bg-[var(--ch-color-background-muted)]',
    ],
    [
      'ch-chip-active',
      'border-[var(--ch-color-border-strong)] bg-[var(--ch-color-background-muted)] text-[var(--ch-color-foreground)]',
    ],
    [
      'ch-input',
      `flex h-6 w-full rounded-[4px] border border-[var(--ch-color-input)] bg-[var(--ch-color-background)] px-2 py-0.5 text-xs shadow-none placeholder:text-[var(--ch-color-muted-foreground)] ${ringFocus}`,
    ],
    [
      'ch-select',
      `flex h-6 w-full items-center rounded-[4px] border border-[var(--ch-color-input)] bg-[var(--ch-color-background)] px-2 py-0.5 text-xs ${ringFocus}`,
    ],
    ['ch-error-text', 'text-[var(--ch-color-destructive)] whitespace-pre-wrap text-xs'],
    ['ch-nav-link', 'rounded-[4px] px-1.5 py-0.5 text-xs no-underline text-[var(--ch-color-body)] hover:text-[var(--ch-color-foreground)]'],
    ['ch-nav-link-active', 'text-[var(--ch-color-foreground)] font-medium'],
    ['ch-link', 'text-[var(--ch-color-link)] no-underline hover:text-[var(--ch-color-link-deep)]'],
    ['ch-code-block', 'max-h-[320px] overflow-auto rounded-[var(--ch-radius)] border border-[var(--ch-color-border)] bg-[var(--ch-color-code-bg)] p-2 font-[var(--ch-font-mono)] text-xs leading-4 text-[var(--ch-color-code-fg)]'],
    ['ch-panel', 'rounded-[4px] border border-[var(--ch-color-border)] bg-[var(--ch-color-card)] p-3'],
    ['ch-panel-muted', 'rounded-[4px] border border-[var(--ch-color-border)] bg-[var(--ch-color-background-muted)] p-3'],
    ['ch-kicker', 'mb-1.5 text-xs font-medium uppercase tracking-[0.06em] text-[var(--ch-color-muted-foreground)]'],
    ['ch-field-label', 'mb-0.5 block text-xs text-[var(--ch-color-muted-foreground)]'],
    ['ch-prose', 'text-sm leading-5'],
  ],
  presets: [presetWind4()],
})
