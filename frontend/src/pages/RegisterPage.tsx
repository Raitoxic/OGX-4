import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { VyroLogo } from '../components/VyroLogo';
import { useAuth } from '../context/AuthContext';
import { ApiError } from '../services/api';

export const RegisterPage: React.FC = () => {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    setSubmitting(true);
    try {
      await register(email.trim(), fullName.trim(), password);
      navigate('/workspace', { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to create account.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-[calc(100vh-3rem)] items-center justify-center bg-apple-bg px-4 py-14">
      <div className="w-full max-w-[400px] rounded-xl border border-apple-borderStrong bg-apple-elevated p-7 shadow-apple-md">
        <div className="flex flex-col items-center text-center">
          <VyroLogo size="lg" />
          <h1 className="apple-headline mt-5 text-[28px]">Create your VYRO-X account</h1>
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
              Full Name
            </label>
            <input
              type="text"
              required
              minLength={2}
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Alex Rivera"
              className="w-full rounded-xl border border-apple-border bg-apple-bg px-3.5 py-2.5 text-[14px] text-apple-ink outline-none transition focus:border-apple-blue"
            />
          </div>

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
              placeholder="alex@organization.org"
              className="w-full rounded-xl border border-apple-border bg-apple-bg px-3.5 py-2.5 text-[14px] text-apple-ink outline-none transition focus:border-apple-blue"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-[12.5px] font-medium text-apple-secondary">
              Password (minimum 8 characters)
            </label>
            <input
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Create a secure password"
              className="w-full rounded-xl border border-apple-border bg-apple-bg px-3.5 py-2.5 text-[14px] text-apple-ink outline-none transition focus:border-apple-blue"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="apple-pill-primary mt-2 w-full py-2.5 text-[14.5px] disabled:opacity-60"
          >
            <span>{submitting ? 'Creating account...' : 'Create Account & Launch'}</span>
            <ArrowRight className="h-4 w-4" />
          </button>
        </form>

        <p className="mt-6 text-center text-[13.5px] text-apple-secondary">
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-apple-blue hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
};
