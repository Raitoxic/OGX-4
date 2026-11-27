import React, { useEffect, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { CommandPalette } from './components/CommandPalette';
import { Navbar } from './components/Navbar';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { EvaluationPage } from './pages/EvaluationPage';
import { HistoryPage } from './pages/HistoryPage';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { SettingsPage } from './pages/SettingsPage';
import { WorkspacePage } from './pages/WorkspacePage';

const ProtectedShellRoute: React.FC<{
  children: React.ReactNode;
  onOpenPalette: () => void;
}> = ({ children, onOpenPalette }) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-apple-bg text-[13px] text-apple-secondary">
        Verifying session...
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  return <AppShell onOpenCommandPalette={onOpenPalette}>{children}</AppShell>;
};

const PublicLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="min-h-screen bg-apple-bg text-apple-ink">
    <Navbar />
    {children}
  </div>
);

const AppRoutes: React.FC = () => {
  const [paletteOpen, setPaletteOpen] = useState(false);

  // Global Cmd+K / Ctrl+K Raycast-style Command Palette shortcut
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  return (
    <>
      <Routes>
        <Route
          path="/"
          element={
            <PublicLayout>
              <LandingPage />
            </PublicLayout>
          }
        />
        <Route
          path="/login"
          element={
            <PublicLayout>
              <LoginPage />
            </PublicLayout>
          }
        />
        <Route
          path="/register"
          element={
            <PublicLayout>
              <RegisterPage />
            </PublicLayout>
          }
        />
        <Route
          path="/workspace"
          element={
            <ProtectedShellRoute onOpenPalette={() => setPaletteOpen(true)}>
              <WorkspacePage />
            </ProtectedShellRoute>
          }
        />
        <Route
          path="/workspace/:taskId"
          element={
            <ProtectedShellRoute onOpenPalette={() => setPaletteOpen(true)}>
              <WorkspacePage />
            </ProtectedShellRoute>
          }
        />
        <Route
          path="/history"
          element={
            <ProtectedShellRoute onOpenPalette={() => setPaletteOpen(true)}>
              <HistoryPage />
            </ProtectedShellRoute>
          }
        />
        <Route
          path="/analytics"
          element={
            <ProtectedShellRoute onOpenPalette={() => setPaletteOpen(true)}>
              <AnalyticsPage />
            </ProtectedShellRoute>
          }
        />
        <Route
          path="/evaluation"
          element={
            <ProtectedShellRoute onOpenPalette={() => setPaletteOpen(true)}>
              <EvaluationPage />
            </ProtectedShellRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedShellRoute onOpenPalette={() => setPaletteOpen(true)}>
              <SettingsPage />
            </ProtectedShellRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </>
  );
};

export const App: React.FC = () => (
  <BrowserRouter>
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  </BrowserRouter>
);

export default App;
