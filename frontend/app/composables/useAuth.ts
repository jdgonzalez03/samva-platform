
const isAuthenticated = useState('auth', () => false)
// TODO: Implement actual authentication logic to set isAuthenticated based on user login status
export function useAuth() {
  return {
    isAuthenticated: readonly(isAuthenticated)
  }
}