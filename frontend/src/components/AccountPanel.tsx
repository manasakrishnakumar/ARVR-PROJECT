import { useState, type FormEvent } from "react";
import { useAuth } from "../context/AuthContext";
import { api, tokenStore } from "../services/api";

/** Sign in / create account form. Guest mode needs no account. */
export default function AccountPanel({ onDone }: { onDone?: () => void }) {
  const { setUser } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      const out = mode === "login" ? await api.login(username, password) : await api.register(username, password);
      tokenStore.set(out.token);
      setUser(out.user);
      setPassword("");
      onDone?.();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card" aria-label="Account">
      <h2>{mode === "login" ? "Sign in" : "Create an account"}</h2>
      <p>
        <strong>Guest mode needs no account</strong>: you can try everything, but progress is not saved and difficulty stays at the default.
        An account saves your sessions on this computer and gives personalised difficulty suggestions.
      </p>
      <form className="row" onSubmit={submit}>
        <input aria-label="Username" placeholder="Username (3-32 letters, numbers, . _ -)" value={username}
               onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
        <input aria-label="Password" type="password" placeholder="Password (8+ characters)" value={password}
               onChange={(e) => setPassword(e.target.value)} autoComplete={mode === "login" ? "current-password" : "new-password"} required />
        <button type="submit" className="primary" disabled={busy}>{mode === "login" ? "Sign in" : "Create account"}</button>
        <button type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }}>
          {mode === "login" ? "Need an account?" : "Have an account?"}
        </button>
      </form>
      <p className="muted">Use a password you do not use anywhere else. Do not enter medical details anywhere in this app.</p>
      {error && <p className="error" role="alert">{error}</p>}
    </section>
  );
}
