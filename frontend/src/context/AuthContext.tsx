import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, ApiError, tokenStore } from "../services/api";
import type { User } from "../types/api";

interface AuthState {
  user: User | null;
  loading: boolean; // true while a saved sign-in is being restored
  setUser: (u: User | null) => void;
  signOut: () => Promise<void>;
}

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(() => tokenStore.get() !== null);

  // restore a previous sign-in; an expired or invalid token silently falls back to guest mode
  useEffect(() => {
    if (!tokenStore.get()) return;
    api.me()
      .then(setUser)
      .catch((e) => { if (e instanceof ApiError && e.status === 401) tokenStore.set(null); })
      .finally(() => setLoading(false));
  }, []);

  const signOut = useCallback(async () => {
    try { await api.logout(); } catch { /* token may already be invalid */ }
    tokenStore.set(null);
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, loading, setUser, signOut }), [user, loading, signOut]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAuth must be used inside AuthProvider");
  return v;
}
