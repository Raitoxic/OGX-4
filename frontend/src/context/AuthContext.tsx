import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { api, getStoredToken, setStoredToken } from '../services/api';
import type { SystemInfo, UserProfile } from '../types/hai';

type ThemeMode = 'light' | 'dark' | 'system';

interface AuthContextValue {
  user: UserProfile | null;
  systemInfo: SystemInfo | null;
  loading: boolean;
  theme: ThemeMode;
  resolvedDark: boolean;
  setTheme: (t: ThemeMode) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, fullName: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  updateUserProfile: (patch: Partial<UserProfile>) => Promise<UserProfile>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const THEME_STORAGE_KEY = 'vyrox_theme_preference';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [theme, setThemeState] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    return saved === 'dark' || saved === 'light' || saved === 'system' ? saved : 'dark';
  });
  const [resolvedDark, setResolvedDark] = useState(false);

  useEffect(() => {
    const apply = () => {
      const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      const shouldDark = theme === 'dark' || (theme === 'system' && prefersDark);
      setResolvedDark(shouldDark);
      document.documentElement.classList.toggle('dark', shouldDark);
    };
    apply();
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    mq.addEventListener('change', apply);
    return () => mq.removeEventListener('change', apply);
  }, [theme]);

  const setTheme = useCallback((next: ThemeMode) => {
    setThemeState(next);
    localStorage.setItem(THEME_STORAGE_KEY, next);
  }, []);

  const refreshUser = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setUser(null);
      return;
    }
    try {
      const profile = await api.getMe();
      setUser(profile);
      if (profile.theme_preference) {
        setTheme(profile.theme_preference);
      }
    } catch {
      setStoredToken(null);
      setUser(null);
    }
  }, [setTheme]);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const info = await api.systemInfo();
        if (active) setSystemInfo(info);
      } catch {
        // backend may still be starting
      }
      await refreshUser();
      if (active) setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, [refreshUser]);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await api.login({ email, password });
      setStoredToken(res.access_token);
      setUser(res.user);
      if (res.user.theme_preference) setTheme(res.user.theme_preference);
    },
    [setTheme],
  );

  const register = useCallback(
    async (email: string, fullName: string, password: string) => {
      const res = await api.register({ email, full_name: fullName, password });
      setStoredToken(res.access_token);
      setUser(res.user);
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      // ignore if token already expired
    }
    setStoredToken(null);
    setUser(null);
  }, []);

  const updateUserProfile = useCallback(
    async (patch: Partial<UserProfile>) => {
      const updated = await api.updateProfile(patch);
      setUser(updated);
      if (patch.theme_preference) {
        setTheme(patch.theme_preference);
      }
      return updated;
    },
    [setTheme],
  );

  return (
    <AuthContext.Provider
      value={{
        user,
        systemInfo,
        loading,
        theme,
        resolvedDark,
        setTheme,
        login,
        register,
        logout,
        refreshUser,
        updateUserProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return ctx;
}
