import { EmptyState, Page } from '../components/Page';

export function Calendar() {
  return (
    <Page accent="blue" title="Calendar">
      <EmptyState>Days you train will be marked here once you log a workout.</EmptyState>
    </Page>
  );
}
