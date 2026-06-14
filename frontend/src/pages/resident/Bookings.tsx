import { useState } from "react";
import { Link } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { Button } from "../../components/Button";
import { Card, EmptyState, ErrorNote, Spinner } from "../../components/primitives";
import { api, ApiError } from "../../lib/api";
import { useAsync } from "../../lib/useAsync";
import type { IconName } from "../../components/Icon";
import type { BookingStatus } from "../../lib/types";

const STATUS_STYLE: Record<BookingStatus, { tone: string; icon: IconName; label: string }> = {
  REQUESTED: { tone: "bg-secondary-fixed text-on-secondary-fixed-variant", icon: "hourglass_top", label: "Awaiting approval" },
  CONFIRMED: { tone: "bg-tertiary-fixed text-on-tertiary-fixed-variant", icon: "check_circle", label: "Confirmed" },
  REJECTED: { tone: "bg-error-container text-on-error-container", icon: "cancel", label: "Rejected" },
  CANCELLED: { tone: "bg-surface-container text-on-surface-variant", icon: "block", label: "Cancelled" },
};

// GET /api/bookings/mine + POST /api/bookings/:id/cancel.
export function Bookings() {
  const { data, loading, error, reload } = useAsync(() => api.bookings.mine(), []);
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  async function cancel(id: string) {
    setActionError(null);
    setBusy(id);
    try {
      await api.bookings.cancel(id);
      reload();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Could not cancel.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-stack-md">
      <h1 className="text-headline-lg-mobile md:text-headline-lg text-primary">My bookings</h1>

      {loading && (
        <div className="flex justify-center py-stack-lg text-on-surface-variant">
          <Spinner className="text-3xl" />
        </div>
      )}
      {error && <ErrorNote message={error} />}
      {actionError && <ErrorNote message={actionError} />}
      {data && data.bookings.length === 0 && (
        <EmptyState icon="receipt_long" title="No bookings yet." hint="Find a hostel to get started." />
      )}

      <div className="space-y-gutter">
        {data?.bookings.map((b) => {
          const style = STATUS_STYLE[b.status];
          const isActive = b.status === "REQUESTED" || b.status === "CONFIRMED";
          const needsRoommate = b.status === "REQUESTED" && b.room.type === "SHARED" && !b.roommate_match_id;
          return (
            <Card key={b.id}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-headline-md text-primary">{b.hostel.name}</h3>
                  <p className="text-label-md text-on-surface-variant">
                    {b.room.type === "SHARED" ? "Shared" : "Single"} room · ₹{b.room.price.toLocaleString("en-IN")}/mo
                  </p>
                </div>
                <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-label-sm ${style.tone}`}>
                  <Icon name={style.icon} className="text-[16px]" filled />
                  {style.label}
                </span>
              </div>

              {(needsRoommate || isActive) && (
                <div className="flex gap-3 mt-4">
                  {needsRoommate && (
                    <Link to={`/resident/bookings/${b.id}/roommates`} className="flex-1">
                      <Button fullWidth>Find a roommate</Button>
                    </Link>
                  )}
                  {isActive && (
                    <Button variant="ghost" disabled={busy === b.id} onClick={() => cancel(b.id)}>
                      {busy === b.id ? "Cancelling…" : "Cancel"}
                    </Button>
                  )}
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
