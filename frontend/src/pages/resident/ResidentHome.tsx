import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { Card, ErrorNote, Spinner, StatusDot } from "../../components/primitives";
import { Button } from "../../components/Button";
import { api, ApiError } from "../../lib/api";
import type { KycStatusResponse, ResidentProfile } from "../../lib/types";

// Resident dashboard. A missing profile (404 from /me) means onboarding isn't
// done yet, so we route there first.
export function ResidentHome() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<ResidentProfile | null>(null);
  const [kyc, setKyc] = useState<KycStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const me = await api.residents.me();
        if (!alive) return;
        setProfile(me);
        try {
          setKyc(await api.kyc.status());
        } catch {
          /* kyc status is non-critical for the dashboard */
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          navigate("/onboarding", { replace: true });
          return;
        }
        if (alive) setError(err instanceof ApiError ? err.message : "Could not load your dashboard.");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [navigate]);

  if (loading) {
    return (
      <div className="flex justify-center py-stack-lg text-on-surface-variant">
        <Spinner className="text-3xl" />
      </div>
    );
  }
  if (error) return <ErrorNote message={error} />;
  if (!profile) return null;

  const verified = kyc?.kyc_status === "VERIFIED";

  return (
    <div className="space-y-stack-md">
      <div>
        <h1 className="text-headline-lg-mobile md:text-headline-lg text-primary">
          Hey {profile.name.split(" ")[0]} 👋
        </h1>
        <p className="text-body-md text-on-surface-variant">Let's find your place.</p>
      </div>

      {!verified && (
        <Card className="border-secondary-container/40">
          <div className="flex items-start gap-3">
            <StatusDot status={kyc?.kyc_status ?? "NONE"} />
            <div className="flex-1">
              <p className="text-label-md text-on-surface">Finish KYC to book a room</p>
              <p className="text-label-sm text-on-surface-variant mt-0.5">
                Verification unlocks booking and roommate matching.
              </p>
            </div>
            <Link to="/kyc">
              <Button size="md">Verify</Button>
            </Link>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-gutter">
        <Link to="/resident/hostels">
          <Card hover className="h-full">
            <Icon name="search" className="text-3xl text-primary mb-2" />
            <h3 className="text-headline-md text-primary">Hostels for you</h3>
            <p className="text-label-md text-on-surface-variant">Ranked by your lifestyle fit.</p>
          </Card>
        </Link>
        <Link to="/resident/bookings">
          <Card hover className="h-full">
            <Icon name="receipt_long" className="text-3xl text-primary mb-2" />
            <h3 className="text-headline-md text-primary">My bookings</h3>
            <p className="text-label-md text-on-surface-variant">Track requests and confirmations.</p>
          </Card>
        </Link>
      </div>
    </div>
  );
}
