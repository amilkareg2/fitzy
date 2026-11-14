import type { CSSProperties } from 'react';
import { NavLink } from 'react-router-dom';

import styles from './TabBar.module.css';
import { accentVar, tabs } from './tabs';

export function TabBar() {
  return (
    <nav className={styles.bar} aria-label="Main">
      <ul className={styles.list}>
        {tabs.map((tab) => (
          <li key={tab.path} className={styles.item}>
            <NavLink
              to={tab.path}
              end={tab.path === '/'}
              className={({ isActive }) =>
                isActive ? `${styles.tab} ${styles.active}` : styles.tab
              }
              style={{ '--tab-accent': accentVar(tab.accent) } as CSSProperties}
            >
              {tab.icon}
              <span className={styles.label}>{tab.label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
