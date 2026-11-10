import { useMutation, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from '../../../api/client'
import type { Package, PackageRequest } from '../../../api/types'

export function useCreatePackage() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: PackageRequest) => apiFetch<Package>('/packages/', { method: 'POST', body: data }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['students'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}
