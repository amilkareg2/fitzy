import { useQuery } from '@tanstack/react-query';

import { api } from './client';

export const healthQueryKey = ['health'] as const;

export function useHealth() {
  return useQuery({
    queryKey: healthQueryKey,
    queryFn: ({ signal }) => api.health(signal),
    refetchInterval: 30_000,
  });
}
