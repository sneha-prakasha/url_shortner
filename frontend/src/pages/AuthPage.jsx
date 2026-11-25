import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth";

export default function AuthPage({ mode }) {
  const { login, signup } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const isSignup = mode === "signup";

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await (isSignup ? signup : login)(email, password);
      // GuestOnly wrapper redirects to the dashboard once the user is set
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <div className="logo big">snip<span>.</span></div>
        <h1>{isSignup ? "Create your account" : "Welcome back"}</h1>
        <p className="muted">Short links with click analytics.</p>

        <label className="field">
          <span>Email</span>
          <input
            type="email"
            required
            autoFocus
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className="field">
          <span>Password</span>
          <input
            type="password"
            required
            minLength={8}
            maxLength={72}
            autoComplete={isSignup ? "new-password" : "current-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {isSignup && <small className="muted">At least 8 characters</small>}
        </label>

        {error && <p className="error">{error}</p>}

        <button className="btn primary block" disabled={busy}>
          {busy ? "Please wait…" : isSignup ? "Sign up" : "Log in"}
        </button>

        <p className="muted small center">
          {isSignup ? (
            <>Already have an account? <Link to="/login">Log in</Link></>
          ) : (
            <>New here? <Link to="/signup">Create an account</Link></>
          )}
        </p>
      </form>
    </div>
  );
}
