import React, { createContext, useContext, useEffect, useState } from 'react';
import { api } from '../api/client';
import { AuthTokens, User, UserRole } from '../types';

interface AuthContextType {
  user: User | null;
  token: string | null;
  role: UserRole | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (usernameOrEmail: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('geovertex_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('geovertex_access_token');
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshProfile = async () => {
    try {
      const currentUser = await api.get<User>('/auth/me');
      setUser(currentUser);
      localStorage.setItem('geovertex_user', JSON.stringify(currentUser));
    } catch (err) {
      console.warn('Failed to refresh user profile:', err);
      setUser(null);
      setToken(null);
      localStorage.removeItem('geovertex_user');
      localStorage.removeItem('geovertex_access_token');
      localStorage.removeItem('geovertex_refresh_token');
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('geovertex_access_token');
      if (storedToken) {
        await refreshProfile();
      }
      setIsLoading(false);
    };

    initAuth();

    const handleExpired = () => {
      setUser(null);
      setToken(null);
    };

    window.addEventListener('geovertex_auth_expired', handleExpired);
    return () => window.removeEventListener('geovertex_auth_expired', handleExpired);
  }, []);

  const login = async (usernameOrEmail: string, password: string): Promise<User> => {
    setIsLoading(true);
    try {
      const response = await api.post<AuthTokens>('/auth/login', {
        username_or_email: usernameOrEmail,
        password,
      });

      localStorage.setItem('geovertex_access_token', response.access_token);
      localStorage.setItem('geovertex_refresh_token', response.refresh_token);
      localStorage.setItem('geovertex_user', JSON.stringify(response.user));

      setToken(response.access_token);
      setUser(response.user);
      return response.user;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem('geovertex_refresh_token');
    try {
      await api.post('/auth/logout', { refresh_token: refreshToken });
    } catch (err) {
      console.warn('Logout API call failed:', err);
    } finally {
      localStorage.removeItem('geovertex_access_token');
      localStorage.removeItem('geovertex_refresh_token');
      localStorage.removeItem('geovertex_user');
      setUser(null);
      setToken(null);
    }
  };

  const value: AuthContextType = {
    user,
    token,
    role: user ? user.role : null,
    isLoading,
    isAuthenticated: !!user && !!token && user.is_active,
    login,
    logout,
    refreshProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
