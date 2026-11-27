import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, ShieldCheck } from 'lucide-react';
import { VyroLogo } from '../components/VyroLogo';
import { useAuth } from '../context/AuthContext';
import { ApiError } from '../services/api';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = (location.state as { from?: string } | null)?.from || '/workspace';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to sign in. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-[calc(100vh-3rem)] items-center justify-center bg-apple-bg px-4 py-14">
      <div className="w-full max-w-[400px] rounded-xl border border-apple-borderStrong bg-apple-elevated p-7 shadow-apple-md">
        <div className="flex flex-col items-center text-center">
          <VyroLogo size="lg" />
          <h1 className="apple-headline mt-5 text-[28px]">Sign in to VYRO-X</h1>
          <p className="mt-1.5 text-[14px] text-apple-secondary">
            Human Intelligence. Agent Evolution.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-7 space-y-4">
          {error && (
            <div className="rounded-xl border border-red-500/25 bg-red-50 px-3.5 py-2.5 text-[13px] text-red-700 dark:bg-red-950/40 dark:text-red-300">
              {error}
            </div>
          )}

          <div>
            <label className="mb-1.5 block text-[12.5px] font-medium text-apple-secondary">
              Email Address
            </label>
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@domain.com"
              className="w-full rounded-xl border border-apple-border bg-apple-bg px-3.5 py-2.5 text-[14px] text-apple-ink outline-none transition focus:border-apple-blue"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-[12.5px] font-medium text-apple-secondary">
              Password
            </label>
            <input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              className="w-full rounded-xl border border-apple-border bg-apple-bg px-3.5 py-2.5 text-[14px] text-apple-ink outline-none transition focus:border-apple-blue"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="apple-pill-primary mt-2 w-full py-2.5 text-[14.5px] disabled:opacity-60"
          >
            <span>{submitting ? 'Signing in...' : 'Sign In'}</span>
            <ArrowRight className="h-4 w-4" />
          </button>
        </form>

        <div className="mt-6 flex items-center justify-center gap-1.5 text-[12px] text-apple-secondary">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
          <span>PBKDF2-SHA256 hashed credentials · User-isolated tasks</span>
        </div>

        <p className="mt-5 text-center text-[13.5px] text-apple-secondary">
          New to VYRO-X?{' '}
          <Link to="/register" className="font-medium text-apple-blue hover:underline">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
};
