import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Configuration
const API_BASE_URL = import.meta.env.REACT_APP_API_URL || 'http://localhost:9000/api';

const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isLoading: false,
      error: null,

      // Computed values
      isAuthenticated: () => {
        const { user, token } = get();
        return !!(user && token);
      },

      // Initialize authentication on app start
      initializeAuth: async () => {
        const { user, token } = get();
        if (user && token) {
          try {
            const response = await fetch(`${API_BASE_URL}/auth/me`, {
              headers: {
                'Authorization': `Bearer ${token}`,
              },
            });

            if (response.ok) {
              const userData = await response.json();
              set({ user: userData });
            } else {
              // Token invalid, clear auth state
              get().logout();
            }
          } catch (error) {
            console.error('Failed to verify token:', error);
            get().logout();
          }
        }
      },

      // Registration with proper data mapping
      register: async (userData) => {
        set({ isLoading: true, error: null });

        try {
          // Map frontend fields to backend schema
          const backendData = {
            email: userData.email,
            password: userData.password,
            full_name: userData.username, 
            user_mode: userData.user_type === 'auditor' ? 'auditor' : 'normal'
          };

          const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(backendData),
          });

          const data = await response.json();

          if (response.ok) {
            set({ 
              isLoading: false,
              error: null
            });
            return { success: true };
          } else {
            set({ 
              error: data.detail || 'Registration failed', 
              isLoading: false 
            });
            return { success: false, error: data.detail };
          }
        } catch (error) {
          const errorMessage = 'Network error occurred';
          set({ 
            error: errorMessage, 
            isLoading: false 
          });
          return { success: false, error: errorMessage };
        }
      },

      // Login with consistent error handling
      login: async (credentials) => {
        set({ isLoading: true, error: null });

        try {
          const response = await fetch(`${API_BASE_URL}/auth/login-json`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(credentials),
          });

          const data = await response.json();

          if (response.ok) {
            set({ 
              user: data.user, 
              token: data.access_token,
              isLoading: false,
            });
            return { success: true };
          } else {
            set({ 
              error: data.detail || 'Login failed', 
              isLoading: false 
            });
            return { success: false, error: data.detail };
          }
        } catch (error) {
          const errorMessage = 'Network error occurred';
          set({ 
            error: errorMessage, 
            isLoading: false 
          });
          return { success: false, error: errorMessage };
        }
      },

      updateUserMode: async (newMode) => {
        const { token } = get();
        if (!token) return { success: false, error: 'Not authenticated' };

        try {
          const response = await fetch('/api/auth/mode', {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ user_mode: newMode })
          });

          if (response.ok) {
            const updatedUser = await response.json();
            set({ user: updatedUser });
            return { success: true };
          } else {
            const errorData = await response.json();
            return { success: false, error: errorData.detail };
          }
        } catch (error) {
          return { success: false, error: 'Network error occurred' };
        }
      },

      logout: async () => {
        try {
          const { token } = get();
          if (token) {
            await fetch('/api/auth/logout', {
              method: 'POST',
              headers: {
                'Authorization': `Bearer ${token}`
              }
            });
          }
        } catch (error) {
          console.error('Logout error:', error);
        } finally {
          localStorage.removeItem('access_token');
          set({ user: null, token: null, error: null });
        }
      },

      // Utility functions
      clearError: () => set({ error: null }),

      getCurrentUser: async () => {
        const { token } = get();
        if (!token) return;

        try {
          const response = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          });

          if (response.ok) {
            const userData = await response.json();
            set({ user: userData });
          } else {
            get().logout();
          }
        } catch (error) {
          console.error('Failed to get current user:', error);
          get().logout();
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ 
        user: state.user, 
        token: state.token 
      }),
      // Only rehydrate if the stored state is valid
      onRehydrateStorage: () => (state) => {
        if (state) {
          // Validate token on rehydration
          state.initializeAuth();
        }
      },
    }
  )
);

export { useAuthStore }; // Named export
export default useAuthStore;