import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { Icon, type IconName } from "./Icon";
import { useAuth } from "../lib/auth";
import { api } from "../lib/api";
import type { Role } from "../lib/types";

interface NavItem {
  to: string;
  label: string;
  icon: IconName;
}

const NAV: Record<Role, NavItem[]> = {
  RESIDENT: [
    { to: "/resident", label: "Home", icon: "dashboard" },
    { to: "/resident/hostels", label: "Search", icon: "search" },
    { to: "/resident/roommate-requests", label: "Matches", icon: "handshake" },
    { to: "/resident/bookings", label: "Bookings", icon: "receipt_long" },
  ],
  OWNER: [
    { to: "/owner", label: "Dashboard", icon: "dashboard" },
    { to: "/owner/hostels/new", label: "Add", icon: "add_business" },
    { to: "/owner/bookings", label: "Requests", icon: "inbox" },
  ],
};

// App chrome shared by the authenticated verticals: fixed top bar (desktop nav)
// + bottom tab bar (mobile), matching the Stitch screens.
export function AppShell({ children }: { children: ReactNode }) {
  const { role, logout } = useAuth();
  const navigate = useNavigate();
  const items = role ? NAV[role] : [];

  async function handleLogout() {
    try {
      await api.auth.logout();
    } finally {
      logout();
      navigate("/");
    }
  }

  return (
    <div className="min-h-screen bg-surface">
      <header className="fixed top-0 left-0 w-full z-50 flex justify-between items-center px-margin-mobile md:px-margin-desktop py-4 bg-surface-container-lowest shadow-sm">
        <NavLink to={role === "OWNER" ? "/owner" : "/resident"} className="text-headline-md font-heading text-primary">
          HostelLo
        </NavLink>
        <nav className="hidden md:flex gap-8 items-center">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/resident" || item.to === "/owner"}
              className={({ isActive }) =>
                `text-label-md transition-colors ${
                  isActive ? "text-primary font-bold border-b-2 border-primary" : "text-on-surface-variant hover:text-primary"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <button
          onClick={handleLogout}
          className="flex items-center gap-1.5 text-label-md text-on-surface-variant hover:text-primary"
        >
          <Icon name="logout" className="text-[20px]" />
          <span className="hidden md:inline">Sign out</span>
        </button>
      </header>

      <main className="pt-24 pb-28 md:pb-16 px-margin-mobile md:px-margin-desktop max-w-container-max mx-auto">
        {children}
      </main>

      <nav className="fixed bottom-0 left-0 w-full z-50 flex justify-around items-center px-2 py-3 bg-surface-container-low shadow-nav-up rounded-t-xl md:hidden">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/resident" || item.to === "/owner"}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center gap-0.5 px-3 ${
                isActive ? "text-primary" : "text-on-surface-variant"
              }`
            }
          >
            <Icon name={item.icon} className="text-[22px]" />
            <span className="text-label-sm">{item.label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
