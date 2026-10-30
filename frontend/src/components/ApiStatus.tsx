import { useHealth } from '../api/useHealth';
import styles from './ApiStatus.module.css';

type State = 'checking' | 'ok' | 'unreachable';

const copy: Record<State, string> = {
  checking: 'Checking API',
  ok: 'API ok',
  unreachable: 'API unreachable',
};

export function ApiStatus() {
  const { isPending, isError } = useHealth();
  const state: State = isPending ? 'checking' : isError ? 'unreachable' : 'ok';

  return (
    <p role="status" className={styles.status} data-state={state}>
      <span className={styles.dot} aria-hidden="true" />
      {copy[state]}
    </p>
  );
}
