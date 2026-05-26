import React, { useState } from 'react';
import { Field, Icon } from './AdminUI';
import { admin } from '../lib/api';

export default function Login({ onLogin }) {
  const [form, setForm] = useState({ login: '', pin: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await admin.login(form);
      if (res?.ok) {
        onLogin();
      } else {
        setError('Invalid login, PIN code, or password.');
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="admin">
      <div className="ad-login">
        <form className="ad-login__panel" onSubmit={submit}>
          <div className="ad-login__head">
            <span className="ad-login__icon">
              <Icon name="lock" size={20} />
            </span>
            <h1>Sign in to CRM</h1>
          </div>

          <Field label="Login">
            <input
              className="ad-input"
              autoFocus
              autoComplete="username"
              value={form.login}
              onChange={update('login')}
            />
          </Field>

          <Field label="PIN code">
            <input
              className="ad-input"
              type="password"
              inputMode="numeric"
              autoComplete="one-time-code"
              value={form.pin}
              onChange={update('pin')}
            />
          </Field>

          <Field label="Password">
            <input
              className="ad-input"
              type="password"
              autoComplete="current-password"
              value={form.password}
              onChange={update('password')}
            />
          </Field>

          {error && <div className="ad-login__error">{error}</div>}

          <button
            type="submit"
            className="ad-btn ad-btn--primary ad-btn--block"
            disabled={busy}
          >
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  );
}
