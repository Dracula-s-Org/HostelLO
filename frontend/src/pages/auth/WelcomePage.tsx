import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { AuthLayout } from "./AuthLayout";
import { Button } from "../../components/Button";
import { Icon, type IconName } from "../../components/Icon";
import { ErrorNote } from "../../components/primitives";
import { api, ApiError } from "../../lib/api";
import type { Role } from "../../lib/types";

const PHONE_RE = /^\+?\d{10,15}$/;

export function WelcomePage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const initialRole = params.get("role") === "OWNER" ? "OWNER" : "RESIDENT";

  const [role, setRole] = useState<Role>(initialRole as Role);
  const [phone, setPhone] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!PHONE_RE.test(phone)) {
      setError("Enter a valid phone number (10–15 digits).");
      return;
    }
    setSubmitting(true);
    try {
      await api.auth.requestOtp(phone, role);
      navigate("/auth/otp", { state: { phone, role } });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not send the code. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  const roles: { value: Role; label: string; icon: IconName; hint: string }[] = [
    { value: "RESIDENT", label: "Student", icon: "school", hint: "Find a hostel & roommates" },
    { value: "OWNER", label: "Hostel owner", icon: "apartment", hint: "List & manage your property" },
  ];

  return (
    <AuthLayout title="Welcome to HostelLo" subtitle="Choose your role and verify your phone to continue.">
      <form onSubmit={handleSubmit} className="space-y-stack-md">
        <div className="grid grid-cols-2 gap-3">
          {roles.map((r) => {
            const active = role === r.value;
            return (
              <button
                type="button"
                key={r.value}
                onClick={() => setRole(r.value)}
                className={`text-left p-4 rounded-xl border-2 transition-colors ${
                  active ? "border-primary bg-primary-fixed/40" : "border-outline-variant hover:border-primary/40"
                }`}
              >
                <Icon name={r.icon} className={`text-2xl mb-2 ${active ? "text-primary" : "text-on-surface-variant"}`} />
                <p className="text-label-md text-on-surface">{r.label}</p>
                <p className="text-label-sm text-on-surface-variant mt-0.5">{r.hint}</p>
              </button>
            );
          })}
        </div>

        <div>
          <label htmlFor="phone" className="block text-label-md text-on-surface mb-1.5">
            Phone number
          </label>
          <input
            id="phone"
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="+91 98765 43210"
            className="w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-4 py-3 text-body-md focus:outline-none focus:border-primary"
          />
        </div>

        {error && <ErrorNote message={error} />}

        <Button type="submit" fullWidth size="lg" disabled={submitting}>
          {submitting ? "Sending code…" : "Send OTP"}
          {!submitting && <Icon name="arrow_forward" className="text-[18px]" />}
        </Button>
      </form>
    </AuthLayout>
  );
}
