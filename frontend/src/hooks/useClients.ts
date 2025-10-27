/**
 * useClients Hook
 *
 * React Query hooks for client management.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ClientsAPI, type Client, type ClientCreate } from '@/services/clients';

/**
 * Query key factory for clients
 */
const clientKeys = {
  all: ['clients'] as const,
  lists: () => [...clientKeys.all, 'list'] as const,
  list: (skip: number, limit: number) =>
    [...clientKeys.lists(), { skip, limit }] as const,
};

/**
 * Fetch clients list
 *
 * @example
 * const { data: clients, isLoading } = useClients()
 */
export function useClients(skip = 0, limit = 100) {
  return useQuery({
    queryKey: clientKeys.list(skip, limit),
    queryFn: () => ClientsAPI.list(skip, limit),
  });
}

/**
 * Create new client
 *
 * @example
 * const createClient = useCreateClient()
 * await createClient.mutateAsync({ company_name: 'ABC Ltd' })
 */
export function useCreateClient() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ClientCreate) => ClientsAPI.create(data),
    onSuccess: () => {
      // Invalidate clients list to refetch
      queryClient.invalidateQueries({ queryKey: clientKeys.lists() });
    },
  });
}
