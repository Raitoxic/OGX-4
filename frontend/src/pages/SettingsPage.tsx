import React, { useState } from 'react';
import { Check, KeyRound, Shield, Sliders, User as UserIcon } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { ModeBanner } from '../components/ModeBanner';
import { api, ApiError } from '../services/api';
import type { AutonomyMode } from '../types/hai';

export const SettingsPage: React.FC = () => {
  const { user, updateUserProfile, setTheme } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [autonomyMode, setAutonomyMode] = useState<AutonomyMode>(
    user?.default_autonomy_mode || 'balanced',
  );
  const [adaptiveEnabled, setAdaptiveEnabled] = useState(user?.adaptive_autonomy_enabled ?? true);
  const [mlRecsEnabled, setMlRecsEnabled] = useState(user?.ml_recommendations_enabled ?? true);
  const [trainingConsent, setTrainingConsent] = useState(user?.training_consent_opt_in ?? false);
  const [requirePlanApproval, setRequirePlanApproval] = useState(user?.require_plan_approval ?? true);
  const [notificationsEnabled, setNotificationsEnabled] = useState(user?.notifications_enabled ?? true);
  const [themePref, setThemePref] = useState<'light' | 'dark' | 'system'>(
    user?.theme_preference || 'light',
  );
  const [savedNotice, setSavedNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [pwNotice, setPwNotice] = useState<string | null>(null);
  const [pwError, setPwError] = useState<string | null>(null);

  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSavedNotice(null);
    try {
      await updateUserProfile({
        full_name: fullName.trim(),
        default_autonomy_mode: autonomyMode,
        adaptive_autonomy_enabled: adaptiveEnabled,
        ml_recommendations_enabled: mlRecsEnabled,
        training_consent_opt_in: trainingConsent,
        require_plan_approval: requirePlanApproval,
        notifications_enabled: notificationsEnabled,
        theme_preference: themePref,
      });
      setTheme(themePref);
      setSavedNotice('Settings saved and persisted to your profile.');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to save settings.');
    } finally {
      setSaving(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setPwError(null);
    setPwNotice(null);
    try {
      await api.changePassword({ current_password: currentPassword, new_password: newPassword });
      setCurrentPassword('');
      setNewPassword('');
      setPwNotice('Password updated securely.');
    } catch (err) {
      setPwError(err instanceof ApiError ? err.message : 'Unable to update password.');
    }
  };

  return (
    <div className="min-h-[calc(100vh-3rem)] bg-apple-surface px-4 py-10 sm:px-6">
      <div className="mx-auto max-w-[820px] space-y-6">
        <div>
          <p className="text-[12px] font-semibold uppercase tracking-[0.12em] text-apple-blue">
            Preferences
          </p>
          <h1 className="apple-headline mt-1 text-[34px]">Settings</h1>
          <p className="mt-1 text-[14.5px] text-apple-secondary">
            Configure your default agent autonomy, human approval safeguards, appearance, and account security.
          </p>
        </div>

        <ModeBanner />

        <form
          onSubmit={handleSaveSettings}
          className="space-y-6 rounded-xl border border-apple-border bg-apple-elevated p-7 shadow-apple-sm"
        >
          {/* Profile */}
          <div>
            <h2 className="flex items-center gap-2 text-[17px] font-semibold">
              <UserIcon className="h-4 w-4 text-apple-blue" /> Profile & Workspace Appearance
            </h2>
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-[12.5px] font-medium text-apple-secondary">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="w-full rounded-xl border border-apple-border bg-apple-bg px-3.5 py-2 text-[14px] outline-none focus:border-apple-blue"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-[12.5px] font-medium text-apple-secondary">
                  Email
                </label>
                <input
                  type="email"
                  disabled
                  value={user?.email || ''}
                  className="w-full rounded-xl border border-apple-border bg-apple-surface px-3.5 py-2 text-[14px] text-apple-secondary"
                />
              </div>
            </div>

            <div className="mt-4">
              <label className="mb-1.5 block text-[12.5px] font-medium text-apple-secondary">
                Appearance
              </label>
              <div className="inline-flex rounded-full border border-apple-border bg-apple-surface p-1">
                {(['light', 'dark', 'system'] as const).map((opt) => (
                  <button
                    key={opt}
                    type="button"
                    onClick={() => {
                      setThemePref(opt);
                      setTheme(opt);
                    }}
                    className={`rounded-full px-4 py-1.5 text-[12.5px] font-medium capitalize transition ${
                      themePref === opt
                        ? 'bg-apple-elevated text-apple-ink shadow-apple-sm'
                        : 'text-apple-secondary hover:text-apple-ink'
                    }`}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <hr className="border-apple-border" />

          {/* Agent Autonomy */}
          <div>
            <h2 className="flex items-center gap-2 text-[17px] font-semibold">
              <Sliders className="h-4 w-4 text-apple-blue" /> Agent Autonomy & Approval Defaults
            </h2>
            <p className="mt-1 text-[13px] text-apple-secondary">
              You can always override autonomy mode live per task inside the Workspace.
            </p>

            <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
              {(
                [
                  {
                    id: 'supervised',
                    label: 'Supervised',
                    desc: 'Approve every step explicitly before execution.',
                  },
                  {
                    id: 'balanced',
                    label: 'Balanced',
                    desc: 'Gate medium/high-risk steps; adapt to edits & interrupts.',
                  },
                  {
                    id: 'higher_autonomy',
                    label: 'Higher Autonomy',
                    desc: 'Auto-run low/medium steps; high-risk always gated.',
                  },
                ] as const
              ).map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setAutonomyMode(m.id)}
                  className={`rounded-2xl border p-4 text-left transition ${
                    autonomyMode === m.id
                      ? 'border-apple-blue bg-blue-50/50 dark:bg-blue-950/25'
                      : 'border-apple-border bg-apple-bg hover:border-apple-blue/40'
                  }`}
                >
                  <div className="text-[14px] font-semibold">{m.label}</div>
                  <p className="mt-1 text-[12px] text-apple-secondary">{m.desc}</p>
                </button>
              ))}
            </div>

            <div className="mt-4 space-y-3">
              <label className="flex items-start justify-between gap-4 rounded-xl border border-apple-border bg-apple-bg p-3.5">
                <div>
                  <div className="text-[13.5px] font-medium">Adaptive Autonomy Calibration</div>
                  <p className="text-[12px] text-apple-secondary">
                    Adjust check-in frequency based on rejections, edits, interruptions, and consecutive approvals.
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={adaptiveEnabled}
                  onChange={(e) => setAdaptiveEnabled(e.target.checked)}
                  className="mt-1 h-4 w-4 accent-[#0071E3]"
                />
              </label>

              <label className="flex items-start justify-between gap-4 rounded-xl border border-apple-border bg-apple-bg p-3.5">
                <div>
                  <div className="text-[13.5px] font-medium">ML Supervision Recommendations (Advisory)</div>
                  <p className="text-[12px] text-apple-secondary">
                    Display advisory autonomy suggestions from the trained supervision model. Never overrides manual mode or high-risk gates.
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={mlRecsEnabled}
                  onChange={(e) => setMlRecsEnabled(e.target.checked)}
                  className="mt-1 h-4 w-4 accent-[#0071E3]"
                />
              </label>

              <label className="flex items-start justify-between gap-4 rounded-xl border border-apple-border bg-apple-bg p-3.5">
                <div>
                  <div className="text-[13.5px] font-medium">Opt-In Consent for Future ML Model Training</div>
                  <p className="text-[12px] text-apple-secondary">
                    Off by default. Private interaction logs are never used for model training without your explicit consent.
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={trainingConsent}
                  onChange={(e) => setTrainingConsent(e.target.checked)}
                  className="mt-1 h-4 w-4 accent-[#0071E3]"
                />
              </label>

              <label className="flex items-start justify-between gap-4 rounded-xl border border-apple-border bg-apple-bg p-3.5">
                <div>
                  <div className="text-[13.5px] font-medium">Require Initial Plan Approval</div>
                  <p className="text-[12px] text-apple-secondary">
                    Always pause after generating a new plan so you can inspect, edit, or lock steps before starting.
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={requirePlanApproval}
                  onChange={(e) => setRequirePlanApproval(e.target.checked)}
                  className="mt-1 h-4 w-4 accent-[#0071E3]"
                />
              </label>

              <div className="flex items-start justify-between gap-4 rounded-xl border border-emerald-500/25 bg-emerald-50/50 p-3.5 dark:bg-emerald-950/20">
                <div className="flex items-start gap-2.5">
                  <Shield className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                  <div>
                    <div className="text-[13.5px] font-medium">High-Impact Safety Invariant (Always Enforced)</div>
                    <p className="text-[12px] text-apple-secondary">
                      Consequential or high-risk steps always require explicit human authorization regardless of autonomy mode.
                    </p>
                  </div>
                </div>
                <span className="rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-700 dark:text-emerald-300">
                  Locked On
                </span>
              </div>

              <label className="flex items-start justify-between gap-4 rounded-xl border border-apple-border bg-apple-bg p-3.5">
                <div>
                  <div className="text-[13.5px] font-medium">Real-Time Workspace Notifications</div>
                  <p className="text-[12px] text-apple-secondary">
                    Show toast alerts for approval requests, safe interrupts, rollbacks, and task completions.
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={notificationsEnabled}
                  onChange={(e) => setNotificationsEnabled(e.target.checked)}
                  className="mt-1 h-4 w-4 accent-[#0071E3]"
                />
              </label>
            </div>
          </div>

          {error && <p className="text-[13px] text-red-600">{error}</p>}
          {savedNotice && (
            <p className="flex items-center gap-1.5 text-[13px] text-emerald-600 dark:text-emerald-400">
              <Check className="h-4 w-4" /> {savedNotice}
            </p>
          )}

          <div className="flex justify-end">
            <button type="submit" disabled={saving} className="apple-pill-primary px-6 py-2 text-[14px]">
              {saving ? 'Saving...' : 'Save Preferences'}
            </button>
          </div>
        </form>

        {/* Password Change */}
        <form
          onSubmit={handlePasswordChange}
          className="space-y-4 rounded-xl border border-apple-border bg-apple-elevated p-7 shadow-apple-sm"
        >
          <h2 className="flex items-center gap-2 text-[17px] font-semibold">
            <KeyRound className="h-4 w-4 text-apple-blue" /> Account Security
          </h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-[12.5px] font-medium text-apple-secondary">
                Current Password
              </label>
              <input
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full rounded-xl border border-apple-border bg-apple-bg px-3.5 py-2 text-[14px] outline-none focus:border-apple-blue"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-[12.5px] font-medium text-apple-secondary">
                New Password (min 8 chars)
              </label>
              <input
                type="password"
                required
                minLength={8}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full rounded-xl border border-apple-border bg-apple-bg px-3.5 py-2 text-[14px] outline-none focus:border-apple-blue"
              />
            </div>
          </div>
          {pwError && <p className="text-[13px] text-red-600">{pwError}</p>}
          {pwNotice && <p className="text-[13px] text-emerald-600 dark:text-emerald-400">{pwNotice}</p>}
          <div className="flex justify-end">
            <button
              type="submit"
              className="rounded-full border border-apple-border px-5 py-2 text-[13.5px] font-medium hover:bg-black/5 dark:hover:bg-white/10"
            >
              Update Password
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
