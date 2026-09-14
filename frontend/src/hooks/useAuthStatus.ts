import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api'

/**
 * Backs the login/logout UI in the topbar. Safe to call unconditionally —
 * /auth/status never requires a session itself. In auth_provider="local"
 * (the default) `authenticated` is always true and `user.role` is always
 * ADMIN, so nothing changes from V1's behavior unless Google login is
 * actually configured and used.
 */
export function useAuthStatus() {
  return useQuery({
    queryKey: ['auth', 'status'],
    queryFn: () => api.auth.status(),
    staleTime: 60_000,
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  return async () => {
    await api.auth.logout()
    await queryClient.invalidateQueries({ queryKey: ['auth', 'status'] })
    window.location.reload()
  }
}
