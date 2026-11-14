import type { ReactElement } from 'react';

export type Accent = 'red' | 'blue' | 'yellow' | 'green';

export interface TabDef {
  path: string;
  label: string;
  accent: Accent;
  icon: ReactElement;
}

const iconProps = {
  width: 28,
  height: 28,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2.25,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
  focusable: false,
} as const;

/** Bottom-bar order: the thing you need mid-workout comes first, under the thumb. */
export const tabs: readonly TabDef[] = [
  {
    path: '/',
    label: 'Today',
    accent: 'red',
    icon: (
      <svg {...iconProps}>
        <path d="M6.5 6.5v11M17.5 6.5v11M3.5 9v6M20.5 9v6M6.5 12h11" />
      </svg>
    ),
  },
  {
    path: '/calendar',
    label: 'Calendar',
    accent: 'blue',
    icon: (
      <svg {...iconProps}>
        <rect x="3.5" y="5" width="17" height="15.5" rx="1.5" />
        <path d="M3.5 10h17M8 3v4M16 3v4" />
      </svg>
    ),
  },
  {
    path: '/progress',
    label: 'Progress',
    accent: 'yellow',
    icon: (
      <svg {...iconProps}>
        <path d="M5 20v-6M12 20V9M19 20V4" />
      </svg>
    ),
  },
  {
    path: '/coach',
    label: 'Coach',
    accent: 'green',
    icon: (
      <svg {...iconProps}>
        <path d="M4.5 5.5h15v10h-8l-4.5 4v-4h-2.5z" />
      </svg>
    ),
  },
];

export function accentVar(accent: Accent): string {
  return `var(--plate-${accent})`;
}
