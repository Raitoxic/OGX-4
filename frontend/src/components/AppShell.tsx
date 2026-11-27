import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  BarChart3,
  FlaskConical,
  History,
  LayoutGrid,
  LogOut,
  Menu,
  Moon,
  Plus,
  Search,
  Settings,
  Sun,
  X,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import type { TaskSummary } from '../types/hai';
import { dispatchWorkspaceCommand } from './CommandPalette';
import { VyroLogo } from './VyroLogo';

interface AppShellProps {
  children: React.ReactNode;
  onOpenCommandPalette: () => void;
}

const NAV_ITEMS = [
  { label: 'Workspace', to: '/workspace', icon: LayoutGrid },
  { label: 'History', to: '/history', icon: History },
  { label: 'Analytics & ML', to: '/analytics', icon: BarChart3 },
  { label: 'Evaluation', to: '/evaluation', icon: FlaskConical },
  { label: 'Settings', to: '/settings', icon: Settings },
];

export const AppShell: React.FC<AppShellProps> = ({ children, onOpenCommandPalette }) => {
  const { user, resolvedDark, setTheme, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const [mobileOpen, setMobileOpen] = useState(false);
  const [recentTasks, setRecentTasks] = useState<TaskSummary[]>([]);

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!user) return;
    api
      .listTasks('vyrox')
      .then((res) => setRecentTasks(res.tasks.slice(0, 5)))
      .catch(() => {});
  }, [user, location.pathname]);

  const handleSignOut = async () => {
    await logout();
    navigate('/');
  };

  const handleQuickNewTask = () => {
    if (location.pathname.startsWith('/workspace')) {
      dispatchWorkspaceCommand('new-task');
    } else {
      navigate('/workspace');
      setTimeout(() => dispatchWorkspaceCommand('new-task'), 120);
    }
  };

  const SidebarContent = (
    <div className="flex h-full flex-col bg-apple-sidebar text-apple-ink">
      {/* Brand Header */}
      <div className="flex h-12 items-center justify-between border-b border-apple-border px-3.5">
        <Link to="/" className="transition-opacity hover:opacity-80" aria-label="VYRO-X Overview">
          <VyroLogo size="sm" />
        </Link>
        <button
          type="button"
          onClick={() => setMobileOpen(false)}
          className="rounded-md p-1 text-apple-tertiary hover:bg-apple-hover hover:text-apple-ink lg:hidden"
          aria-label="Close sidebar"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Command Palette Trigger + Quick New Task */}
      <div className="space-y-1.5 p-2.5">
        <button
          type="button"
          onClick={onOpenCommandPalette}
          className="flex w-full items-center justify-between rounded-lg border border-apple-border bg-apple-surface px-2.5 py-1.5 text-[12px] text-apple-tertiary transition hover:border-apple-borderStrong hover:text-apple-ink"
        >
          <span className="flex items-center gap-2">
            <Search className="h-3.5 w-3.5" />
            <span>Commands...</span>
          </span>
          <span className="vyrox-kbd">⌘K</span>
        </button>

        <button
          type="button"
          onClick={handleQuickNewTask}
          className="apple-pill-primary w-full py-1.5 text-[12px]"
        >
          <Plus className="h-3.5 w-3.5" />
          <span>New Task</span>
        </button>
      </div>

      {/* Primary Navigation */}
      <nav className="space-y-0.5 px-2 py-1" aria-label="Workspace Navigation">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const active = location.pathname.startsWith(item.to);
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-[13px] font-medium transition-colors ${
                active
                  ? 'bg-apple-hover text-apple-ink'
                  : 'text-apple-secondary hover:bg-apple-hover/60 hover:text-apple-ink'
              }`}
            >
              <Icon className={`h-4 w-4 ${active ? 'text-apple-blue' : 'text-apple-tertiary'}`} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Recent Tasks Switcher */}
      {recentTasks.length > 0 && (
        <div className="mt-4 flex-1 overflow-y-auto border-t border-apple-border px-2 pt-3">
          <p className="px-2.5 text-[10.5px] font-semibold uppercase tracking-[0.08em] text-apple-tertiary">
            Recent Tasks
          </p>
          <div className="mt-1.5 space-y-0.5">
            {recentTasks.map((t) => {
              const active = location.pathname === `/workspace/${t.id}`;
              return (
                <Link
                  key={t.id}
                  to={`/workspace/${t.id}`}
                  className={`flex items-center justify-between gap-2 rounded-lg px-2.5 py-1.5 text-[12px] transition-colors ${
                    active
                      ? 'bg-apple-hover font-medium text-apple-ink'
                      : 'text-apple-secondary hover:bg-apple-hover/60 hover:text-apple-ink'
                  }`}
                >
                  <span className="truncate">{t.title}</span>
                  <span
                    className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                      t.status === 'RUNNING'
                        ? 'bg-apple-blue animate-pulse'
                        : t.status === 'COMPLETED'
                          ? 'bg-emerald-500'
                          : t.status === 'AWAITING_APPROVAL'
                            ? 'bg-amber-500'
                            : t.status === 'INTERRUPTED'
                              ? 'bg-orange-500'
                              : 'bg-neutral-500'
                    }`}
                  />
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* Footer Profile & Appearance */}
      <div className="mt-auto border-t border-apple-border p-2.5">
        <div className="flex items-center justify-between gap-2 rounded-lg px-2 py-1.5">
          <div className="min-w-0">
            <p className="truncate text-[12.5px] font-medium text-apple-ink">{user?.full_name}</p>
            <p className="truncate text-[11px] text-apple-tertiary">{user?.email}</p>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setTheme(resolvedDark ? 'light' : 'dark')}
              className="rounded-md p-1.5 text-apple-tertiary transition hover:bg-apple-hover hover:text-apple-ink"
              title={resolvedDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
              aria-label="Toggle theme"
            >
              {resolvedDark ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
            </button>
            <button
              type="button"
              onClick={handleSignOut}
              className="rounded-md p-1.5 text-apple-tertiary transition hover:bg-apple-hover hover:text-red-500"
              title="Sign Out"
              aria-label="Sign Out"
            >
              <LogOut className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-apple-bg text-apple-ink">
      {/* Desktop Fixed Compact Sidebar */}
      <aside className="hidden w-[228px] shrink-0 border-r border-apple-border lg:block">
        <div className="sticky top-0 h-screen">{SidebarContent}</div>
      </aside>

      {/* Mobile / Tablet Slide-Over Sidebar */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div className="fixed inset-0 bg-black/55 backdrop-blur-[2px]" onClick={() => setMobileOpen(false)} />
          <div className="relative z-10 h-full w-[256px] border-r border-apple-border shadow-apple-lg">
            {SidebarContent}
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Compact Mobile/Tablet Header */}
        <header className="apple-glass sticky top-0 z-30 flex h-12 items-center justify-between px-3 lg:hidden">
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              className="rounded-md p-1.5 text-apple-secondary hover:bg-apple-hover hover:text-apple-ink"
              aria-label="Open navigation"
            >
              <Menu className="h-4 w-4" />
            </button>
            <VyroLogo size="sm" />
          </div>
          <button
            type="button"
            onClick={onOpenCommandPalette}
            className="flex items-center gap-1.5 rounded-md border border-apple-border bg-apple-surface px-2.5 py-1 text-[11.5px] text-apple-secondary"
          >
            <Search className="h-3 w-3" />
            <span>⌘K</span>
          </button>
        </header>

        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
};
