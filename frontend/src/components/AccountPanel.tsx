import { useState, type FormEvent } from "react";
import { api, tokenStore } from "../services/api";
import type { User } from "../types/api";

interface Props {
  user: User | null;
  onUser: (u: User | null) => void;
}

export default function AccountPanel({ user, onUser }: Props) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      const out = mode === "login" ? await api.login(username, password) : await api.register(username, password);
      tokenStore.set(out.token);
      onUser(out.user);
      setPassword("");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const signOut = async () => {
    try { await api.logout(); } catch { /* token may already be invalid */ }
    tokenStore.set(null);
    onUser(null);
  };

  const deleteAll = async () => {
    try { await api.deleteMe(); } catch (err) { setError((err as Error).message); return; }
    tokenStore.set(null);
    onUser(null);
    setConfirmDelete(false);
  };

  if (user) {
    return (
      <section className="card" aria-label="Account">
        <div className="row spread">
          <span>Signed in as <strong>{user.username}</strong>. Sessions and the adaptive history are saved on this computer.</span>
          <span className="row">
            <button onClick={signOut}>Sign out</button>
            {!confirmDelete
              ? <button onClick={() => setConfirmDelete(true)}>Delete my data</button>
              : <button className="danger" onClick={deleteAll}>Confirm: delete account and all data</button>}
          </span>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
      </section>
    );
  }

  return (
    <section className="card" aria-label="Account">
      <p><strong>Guest mode.</strong> You can try everything without an account; progress is not saved and difficulty stays at the default.
        Sign in to save sessions and get personalised difficulty suggestions.</p>
      <form className="row" onSubmit={submit}>
        <input aria-label="Username" placeholder="Username (3-32 letters, numbers, . _ -)" value={username}
               onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
        <input aria-label="Password" type="password" placeholder="Password (8+ characters)" value={password}
               onChange={(e) => setPassword(e.target.value)} autoComplete={mode === "login" ? "current-password" : "new-password"} required />
        <button type="submit" disabled={busy}>{mode === "login" ? "Sign in" : "Create account"}</button>
        <button type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }}>
          {mode === "login" ? "Need an account?" : "Have an account?"}
        </button>
      </form>
      <p className="muted">Use a password you do not use anywhere else. Do not enter medical details anywhere in this app.</p>
      {error && <p className="error" role="alert">{error}</p>}
    </section>
  );
}
