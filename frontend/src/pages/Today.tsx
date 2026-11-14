import { ApiStatus } from '../components/ApiStatus';
import { EmptyState, Page } from '../components/Page';
import styles from './Today.module.css';

export function Today({ now = new Date() }: { now?: Date }) {
  const weekday = now.toLocaleDateString(undefined, { weekday: 'long' });
  const month = now.toLocaleDateString(undefined, { month: 'long' });

  return (
    <Page
      accent="red"
      title="Today"
      heading={
        <span className={styles.date}>
          <span className={styles.day}>{now.getDate()}</span>
          <span className={styles.meta}>
            <span className={styles.weekday}>{weekday}</span>
            <span className={styles.month}>{month}</span>
          </span>
        </span>
      }
    >
      <ApiStatus />
      <EmptyState>Nothing logged today.</EmptyState>
      <button type="button" className={styles.start} disabled>
        Start workout
      </button>
    </Page>
  );
}
