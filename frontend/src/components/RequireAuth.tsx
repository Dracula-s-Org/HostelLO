import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { AppShell } from "./AppShell";
import type { Role } from "../lib/types";

// Gate for authenticated routes. Unauthed → /welcome. Wrong role → that role's
// home. `chrome` wraps the page in the app shell (off for full-bleed onboarding).
export function RequireAuth({
  role,
  chrome = true,
  children,
}: {
  role?: Role;
  chrome?: boolean;
  children: ReactNode;
}) {
  const auth = useAuth();
  if (!auth.isAuthed) return <Navigate to="/welcome" replace />;
  if (role && auth.role !== role) {
    return <Navigate to={auth.role === "OWNER" ? "/owner" : "/resident"} replace />;
  }
  return chrome ? <AppShell>{children}</AppShell> : <>{children}</>;
}
