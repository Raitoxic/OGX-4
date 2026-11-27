import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Activity,
  BarChart3,
  CheckCircle2,
  FlaskConical,
  History,
  Home,
  LayoutGrid,
  LogOut,
  Moon,
  Pause,
  Play,
  Plus,
  RotateCcw,
  Search,
  Settings,
  Square,
  Sun,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export type WorkspaceCommandAction =
  | 'new-task'
  | 'start-or-resume'
  | 'pause'
  | 'interrupt'
  | 'approve'
  | 'checkpoints'
  | 'events';

export function dispatchWorkspaceCommand(action: WorkspaceCommandAction): void {
  window.dispatchEvent(new CustomEvent('vyrox:workspace-command', { detail: { action } }));
}

interface CommandItem {
  id: string;
  label: string;
  section: 'Navigation' | 'Workspace Actions' | 'System';
  shortcut?: string;
  icon: React.FC<{ className?: string }>;
  onSelect: () => void;
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ open, onClose }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, resolvedDark, setTheme, logout } = useAuth();

  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const isInWorkspace = location.pathname.startsWith('/workspace');

  const commands = useMemo<CommandItem[]>(() => {
    const list: CommandItem[] = [
      {
        id: 'nav-workspace',
        label: 'Go to Workspace',
        section: 'Navigation',
        shortcut: 'W',
        icon: LayoutGrid,
        onSelect: () => navigate('/workspace'),
      },
      {
        id: 'nav-history',
        label: 'Go to Task History',
        section: 'Navigation',
        shortcut: 'H',
        icon: History,
        onSelect: () => navigate('/history'),
      },
      {
        id: 'nav-analytics',
        label: 'Go to Analytics & ML Model',
        section: 'Navigation',
        shortcut: 'A',
        icon: BarChart3,
        onSelect: () => navigate('/analytics'),
      },
      {
        id: 'nav-evaluation',
        label: 'Go to Scientific Evaluation',
        section: 'Navigation',
        shortcut: 'E',
        icon: FlaskConical,
        onSelect: () => navigate('/evaluation'),
      },
      {
        id: 'nav-settings',
        label: 'Go to Settings & Autonomy Defaults',
        section: 'Navigation',
        shortcut: ',',
        icon: Settings,
        onSelect: () => navigate('/settings'),
      },
      {
        id: 'nav-home',
        label: 'Go to Product Overview',
        section: 'Navigation',
        icon: Home,
        onSelect: () => navigate('/'),
      },
    ];

    if (user) {
      list.push({
        id: 'act-new-task',
        label: 'Create New Collaborative Task',
        section: 'Workspace Actions',
        shortcut: 'N',
        icon: Plus,
        onSelect: () => {
          if (!isInWorkspace) {
            navigate('/workspace');
            setTimeout(() => dispatchWorkspaceCommand('new-task'), 120);
          } else {
            dispatchWorkspaceCommand('new-task');
          }
        },
      });
    }

    if (isInWorkspace) {
      list.push(
        {
          id: 'act-start',
          label: 'Start or Resume Active Task',
          section: 'Workspace Actions',
          icon: Play,
          onSelect: () => dispatchWorkspaceCommand('start-or-resume'),
        },
        {
          id: 'act-interrupt',
          label: 'Interrupt Running Execution Safely',
          section: 'Workspace Actions',
          icon: Square,
          onSelect: () => dispatchWorkspaceCommand('interrupt'),
        },
        {
          id: 'act-pause',
          label: 'Pause Active Execution',
          section: 'Workspace Actions',
          icon: Pause,
          onSelect: () => dispatchWorkspaceCommand('pause'),
        },
        {
          id: 'act-approve',
          label: 'Approve Pending Plan or Step',
          section: 'Workspace Actions',
          icon: CheckCircle2,
          onSelect: () => dispatchWorkspaceCommand('approve'),
        },
        {
          id: 'act-checkpoints',
          label: 'Open Checkpoints & Rollback Drawer',
          section: 'Workspace Actions',
          icon: RotateCcw,
          onSelect: () => dispatchWorkspaceCommand('checkpoints'),
        },
        {
          id: 'act-events',
          label: 'Open Interaction Event Timeline',
          section: 'Workspace Actions',
          icon: Activity,
          onSelect: () => dispatchWorkspaceCommand('events'),
        },
      );
    }

    list.push({
      id: 'sys-theme',
      label: resolvedDark ? 'Switch to Light Appearance' : 'Switch to Dark Appearance',
      section: 'System',
      icon: resolvedDark ? Sun : Moon,
      onSelect: () => setTheme(resolvedDark ? 'light' : 'dark'),
    });

    if (user) {
      list.push({
        id: 'sys-logout',
        label: 'Sign Out of VYRO-X',
        section: 'System',
        icon: LogOut,
        onSelect: async () => {
          await logout();
          navigate('/');
        },
      });
    }

    return list;
  }, [user, isInWorkspace, resolvedDark, navigate, setTheme, logout]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter(
      (c) => c.label.toLowerCase().includes(q) || c.section.toLowerCase().includes(q),
    );
  }, [commands, query]);

  useEffect(() => {
    if (open) {
      setQuery('');
      setActiveIndex(0);
      setTimeout(() => inputRef.current?.focus(), 20);
    }
  }, [open]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveIndex((i) => (filtered.length ? (i + 1) % filtered.length : 0));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveIndex((i) => (filtered.length ? (i - 1 + filtered.length) % filtered.length : 0));
      } else if (e.key === 'Enter' && filtered[activeIndex]) {
        e.preventDefault();
        filtered[activeIndex].onSelect();
        onClose();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [open, filtered, activeIndex, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/55 px-4 pt-[14vh] backdrop-blur-[3px]"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="VYRO-X Command Palette"
    >
      <div
        className="w-full max-w-[560px] overflow-hidden rounded-xl border border-apple-borderStrong bg-apple-elevated shadow-apple-lg"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input */}
        <div className="flex items-center gap-2.5 border-b border-apple-border px-4 py-3">
          <Search className="h-4 w-4 shrink-0 text-apple-tertiary" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command or jump to a page..."
            className="w-full bg-transparent text-[14px] text-apple-ink placeholder:text-apple-tertiary outline-none"
          />
          <span className="vyrox-kbd">ESC</span>
        </div>

        {/* Results */}
        <div className="max-h-[340px] overflow-y-auto p-1.5">
          {filtered.length === 0 ? (
            <div className="px-4 py-8 text-center text-[13px] text-apple-tertiary">
              No matching commands found.
            </div>
          ) : (
            filtered.map((cmd, idx) => {
              const Icon = cmd.icon;
              const selected = idx === activeIndex;
              return (
                <button
                  key={cmd.id}
                  type="button"
                  onMouseEnter={() => setActiveIndex(idx)}
                  onClick={() => {
                    cmd.onSelect();
                    onClose();
                  }}
                  className={`flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-[13px] transition-colors ${
                    selected
                      ? 'bg-apple-blue/12 text-apple-ink'
                      : 'text-apple-secondary hover:bg-apple-hover hover:text-apple-ink'
                  }`}
                >
                  <span className="flex items-center gap-2.5">
                    <Icon className={`h-4 w-4 ${selected ? 'text-apple-blue' : 'text-apple-tertiary'}`} />
                    <span className="font-medium">{cmd.label}</span>
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="text-[11px] text-apple-tertiary">{cmd.section}</span>
                    {cmd.shortcut && <span className="vyrox-kbd">{cmd.shortcut}</span>}
                  </span>
                </button>
              );
            })
          )}
        </div>

        <div className="flex items-center justify-between border-t border-apple-border bg-apple-sidebar px-4 py-2 text-[11px] text-apple-tertiary">
          <span>VYRO-X Command Palette</span>
          <span className="flex items-center gap-2">
            <span>↑↓ Navigate</span>
            <span>↵ Run</span>
          </span>
        </div>
      </div>
    </div>
  );
};
