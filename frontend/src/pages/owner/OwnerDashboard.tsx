import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { Button } from "../../components/Button";
import { Badge, Card, Chip, EmptyState, ErrorNote, Spinner, StatusDot } from "../../components/primitives";
import { OwnerProfileSetup } from "./OwnerProfileSetup";
import { api, ApiError } from "../../lib/api";
import type { KycStatusResponse, OwnerHostel } from "../../lib/types";

// Owner dashboard: properties with room matrix + pending counts. Falls back to
// profile setup when the owner has none, and nudges KYC (required to list).
export function OwnerDashboard() {
  const [needsProfile, setNeedsProfile] = useState(false);
  const [hostels, setHostels] = useState<OwnerHostel[] | null>(null);
  const [kyc, setKyc] = useState<KycStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      await api.owners.me();
      setNeedsProfile(false);
      const [list, kycRes] = await Promise.all([
        api.owners.listHostels(),
        api.kyc.status().catch(() => null),
      ]);
      setHostels(list.hostels);
      setKyc(kycRes);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setNeedsProfile(true);
      } else {
        setError(err instanceof ApiError ? err.message : "Could not load your dashboard.");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-stack-lg text-on-surface-variant">
        <Spinner className="text-3xl" />
      </div>
    );
  }
  if (needsProfile) return <OwnerProfileSetup onDone={load} />;
  if (error) return <ErrorNote message={error} />;

  const verified = kyc?.kyc_status === "VERIFIED";

  return (
    <div className="space-y-stack-md">
      <div className="flex items-center justify-between">
        <h1 className="text-headline-lg-mobile md:text-headline-lg text-primary">Your properties</h1>
        {verified && (
          <Link to="/owner/hostels/new">
            <Button>
              <Icon name="add" className="text-[18px]" /> Add hostel
            </Button>
          </Link>
        )}
      </div>

      {!verified && (
        <Card className="border-secondary-container/40">
          <div className="flex items-start gap-3">
            <StatusDot status={kyc?.kyc_status ?? "NONE"} />
            <div className="flex-1">
              <p className="text-label-md text-on-surface">Verify your identity to list hostels</p>
              <p className="text-label-sm text-on-surface-variant mt-0.5">KYC is required before you can create a listing.</p>
            </div>
            <Link to="/kyc">
              <Button>Verify</Button>
            </Link>
          </div>
        </Card>
      )}

      {hostels && hostels.length === 0 && (
        <EmptyState icon="apartment" title="No listings yet." hint={verified ? "Add your first hostel." : "Verify KYC, then add a hostel."} />
      )}

      <div className="space-y-gutter">
        {hostels?.map(({ hostel, rooms, pending_count }) => (
          <Card key={hostel.id}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-headline-md text-primary">{hostel.name}</h3>
                  {hostel.verified && <Badge icon="verified">Verified</Badge>}
                </div>
                <p className="text-label-md text-on-surface-variant">{hostel.location}</p>
              </div>
              {pending_count > 0 && (
                <Link to="/owner/bookings">
                  <Chip tone="secondary">{pending_count} pending</Chip>
                </Link>
              )}
            </div>

            <div className="flex flex-wrap gap-3 mt-3 text-label-md text-on-surface-variant">
              <span className="flex items-center gap-1">
                <Icon name="meeting_room" className="text-[18px]" /> {rooms.length} rooms
              </span>
              <span className="flex items-center gap-1">
                <Icon name="bed" className="text-[18px]" />
                {rooms.reduce((n, r) => n + r.occupied_count, 0)}/{rooms.reduce((n, r) => n + r.capacity, 0)} filled
              </span>
            </div>

            <div className="flex gap-3 mt-4">
              <Link to={`/owner/hostels/${hostel.id}/rooms`} className="flex-1">
                <Button fullWidth variant="secondary">
                  Manage rooms
                </Button>
              </Link>
              <Link to={`/owner/hostels/${hostel.id}/edit`}>
                <Button variant="ghost">
                  <Icon name="edit" className="text-[18px]" />
                </Button>
              </Link>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
