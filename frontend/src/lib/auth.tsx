import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { Role } from "./types";

// The session itself lives in an httpOnly cookie the JS can't read. We keep a
// lightweight hint (role + signed-in flag) in localStorage so the router can
// pick the right shell; the API is still the source of truth and returns 401
// when the cookie is gone.
interface Session {
  role: Role | null;
  isAuthed: boolean;
}

interface AuthContextValue extends Session {
  login: (role: Role) => void;
  logout: () => void;
}

const STORAGE_KEY = "hostello.session";
const AuthContext = createContext<AuthContextValue | null>(null);

function readSession(): Session {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as Session;
  } catch {
    /* ignore malformed storage */
  }
  return { role: null, isAuthed: false };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session>(readSession);

  const login = useCallback((role: Role) => {
    const next = { role, isAuthed: true };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setSession(next);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setSession({ role: null, isAuthed: false });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ ...session, login, logout }),
    [session, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
