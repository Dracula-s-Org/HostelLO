import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { AuthLayout } from "./AuthLayout";
import { Button } from "../../components/Button";
import { ErrorNote } from "../../components/primitives";
import { api, ApiError } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { pendoTrack, setPendoRole } from "../../lib/pendo";
import type { Role } from "../../lib/types";

interface OtpState {
  phone: string;
  role: Role;
}

export function OtpPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const state = location.state as OtpState | null;

  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [resent, setResent] = useState(false);

  // Reached directly without a phone in hand → restart the flow.
  if (!state?.phone) return <Navigate to="/welcome" replace />;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await api.auth.verifyOtp(state!.phone, code.trim());
      login(res.role);
      setPendoRole(res.role);
      pendoTrack("user_login_completed", { user_type: res.role, method: "otp" });
      navigate(res.redirect, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Verification failed. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  async function resend() {
    setError(null);
    try {
      await api.auth.requestOtp(state!.phone, state!.role);
      setResent(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not resend the code.");
    }
  }

  return (
    <AuthLayout title="Verify your phone" subtitle={`We sent a code to ${state.phone}.`}>
      <form onSubmit={handleSubmit} className="space-y-stack-md">
        <div>
          <label htmlFor="otp" className="block text-label-md text-on-surface mb-1.5">
            One-time code
          </label>
          <input
            id="otp"
            inputMode="numeric"
            autoComplete="one-time-code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Enter OTP"
            className="w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-4 py-3 text-headline-md tracking-[0.3em] text-center focus:outline-none focus:border-primary"
          />
        </div>

        {error && <ErrorNote message={error} />}

        <Button type="submit" fullWidth size="lg" disabled={submitting || !code.trim()}>
          {submitting ? "Verifying…" : "Verify & continue"}
        </Button>

        <div className="text-center text-label-md text-on-surface-variant">
          {resent ? (
            <span className="text-tertiary-container">A new code is on its way.</span>
          ) : (
            <button type="button" onClick={resend} className="text-primary hover:underline">
              Didn't get it? Resend code
            </button>
          )}
        </div>
      </form>
    </AuthLayout>
  );
}
