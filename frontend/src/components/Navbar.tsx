import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { LogOut, Moon, Sun } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { VyroLogo } from './VyroLogo';

export const Navbar: React.FC = () => {
  const { user, resolvedDark, setTheme, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const navItems = user
    ? [
        { label: 'Overview', to: '/' },
        { label: 'Workspace', to: '/workspace' },
        { label: 'History', to: '/history' },
        { label: 'Analytics', to: '/analytics' },
        { label: 'Evaluation', to: '/evaluation' },
      ]
    : [
        { label: 'Product', to: '/#product' },
        { label: 'Planning', to: '/#planning' },
        { label: 'Autonomy', to: '/#autonomy' },
        { label: 'Architecture', to: '/#architecture' },
      ];

  const handleSignOut = async () => {
    await logout();
    navigate('/');
  };

  return (
    <header className="apple-glass sticky top-0 z-40 h-12 w-full">
      <div className="mx-auto flex h-full max-w-[1200px] items-center justify-between px-4 sm:px-6">
        <Link to="/" className="transition-opacity hover:opacity-80" aria-label="VYRO-X Home">
          <VyroLogo size="sm" />
        </Link>

        <nav className="hidden items-center gap-6 md:flex" aria-label="Primary Navigation">
          {navItems.map((item) => {
            if (item.to.startsWith('/#')) {
              return (
                <a
                  key={item.to}
                  href={item.to}
                  className="text-[13px] text-apple-secondary transition-colors hover:text-apple-ink"
                >
                  {item.label}
                </a>
              );
            }
            const active =
              item.to === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.to);
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`text-[13px] transition-colors ${
                  active ? 'font-medium text-apple-ink' : 'text-apple-secondary hover:text-apple-ink'
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={() => setTheme(resolvedDark ? 'light' : 'dark')}
            className="flex h-7 w-7 items-center justify-center rounded-md text-apple-secondary transition-colors hover:bg-apple-hover hover:text-apple-ink"
            title={resolvedDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            aria-label="Toggle color theme"
          >
            {resolvedDark ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
          </button>

          {user ? (
            <div className="flex items-center gap-2">
              <Link to="/workspace" className="apple-pill-primary px-3 py-1 text-[12px]">
                Open Workspace
              </Link>
              <button
                type="button"
                onClick={handleSignOut}
                className="inline-flex items-center gap-1 rounded-md border border-apple-border px-2.5 py-1 text-[12px] font-medium text-apple-secondary transition-colors hover:bg-apple-hover hover:text-apple-ink"
              >
                <LogOut className="h-3 w-3" />
                <span className="hidden sm:inline">Sign Out</span>
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link
                to="/login"
                className="rounded-md px-2.5 py-1 text-[12.5px] font-medium text-apple-secondary transition-colors hover:text-apple-ink"
              >
                Sign In
              </Link>
              <Link to="/register" className="apple-pill-primary px-3.5 py-1 text-[12.5px]">
                Get Started
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
