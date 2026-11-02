import { Navigate, Route, Routes } from 'react-router-dom';

import styles from './App.module.css';
import { TabBar } from './components/TabBar';
import { Calendar } from './pages/Calendar';
import { Coach } from './pages/Coach';
import { Progress } from './pages/Progress';
import { Today } from './pages/Today';

/** App shell: routed page above a fixed bottom tab bar. Router and providers live in main.tsx. */
export function App() {
  return (
    <div className={styles.shell}>
      <main className={styles.main}>
        <Routes>
          <Route path="/" element={<Today />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/progress" element={<Progress />} />
          <Route path="/coach" element={<Coach />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <TabBar />
    </div>
  );
}
