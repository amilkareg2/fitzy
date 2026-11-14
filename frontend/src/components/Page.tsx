import type { CSSProperties, ReactNode } from 'react';

import styles from './Page.module.css';
import { accentVar, type Accent } from './tabs';

interface PageProps {
  accent: Accent;
  /** Visible page heading. Defaults to `title`; pass a node for a custom hero. */
  heading?: ReactNode;
  title: string;
  children?: ReactNode;
}

export function Page({ accent, heading, title, children }: PageProps) {
  return (
    <section
      className={styles.page}
      aria-labelledby="page-title"
      style={{ '--page-accent': accentVar(accent) } as CSSProperties}
    >
      <header className={styles.header}>
        <h1 id="page-title" className={styles.title}>
          {heading ?? title}
        </h1>
      </header>
      <div className={styles.body}>{children}</div>
    </section>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <p className={styles.empty}>{children}</p>;
}
