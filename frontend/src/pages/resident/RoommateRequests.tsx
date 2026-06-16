import { useState } from "react";
import { Icon } from "../../components/Icon";
import { Button } from "../../components/Button";
import { Card, CompatibilityBar, EmptyState, ErrorNote, Spinner } from "../../components/primitives";
import { api, ApiError } from "../../lib/api";
import { useAsync } from "../../lib/useAsync";

// GET /api/roommate-matches/pending + accept/reject. This is the resident-side
// inbox for incoming roommate invites (the booking_approval_* screens).
export function RoommateRequests() {
  const { data, loading, error, reload } = useAsync(() => api.roommateMatches.pending(), []);
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [confirmed, setConfirmed] = useState<{ name: string; phone: string } | null>(null);

  async function accept(matchId: string) {
    setActionError(null);
    setBusy(matchId);
    try {
      const res = await api.roommateMatches.accept(matchId);
      setConfirmed({ name: res.roommate.full_name, phone: res.roommate.phone });
      reload();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Could not accept.");
    } finally {
      setBusy(null);
    }
  }

  async function reject(matchId: string) {
    setActionError(null);
    setBusy(matchId);
    try {
      await api.roommateMatches.reject(matchId);
      reload();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Could not decline.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-stack-md">
      <h1 className="text-headline-lg-mobile md:text-headline-lg text-primary">Roommate requests</h1>

      {confirmed && (
        <Card className="border-tertiary-container/40">
          <div className="flex items-center gap-3">
            <Icon name="celebration" className="text-3xl text-tertiary-container" filled />
            <div>
              <p className="text-label-md text-on-surface">You're matched with {confirmed.name}!</p>
              <p className="text-label-sm text-on-surface-variant">
                Coordinate move-in at {confirmed.phone}. The owner approves the booking next.
              </p>
            </div>
          </div>
        </Card>
      )}

      {loading && (
        <div className="flex justify-center py-stack-lg text-on-surface-variant">
          <Spinner className="text-3xl" />
        </div>
      )}
      {error && <ErrorNote message={error} />}
      {actionError && <ErrorNote message={actionError} />}
      {data && data.pending.length === 0 && (
        <EmptyState icon="inbox" title="No pending requests." hint="Invites from other residents show up here." />
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-gutter">
        {data?.pending.map((m) => (
          <Card key={m.match_id}>
            <div className="flex items-center gap-4 mb-4">
              <div className="w-14 h-14 rounded-full bg-secondary-container text-white flex items-center justify-center text-headline-md font-heading">
                {m.from.first_name.charAt(0)}
              </div>
              <div className="flex-1">
                <h3 className="text-headline-md text-primary">{m.from.first_name}</h3>
                <p className="text-label-md text-on-surface-variant">wants to be your roommate</p>
              </div>
              <span className="text-label-md text-primary bg-primary-fixed rounded-full px-3 py-1">{m.score}%</span>
            </div>

            <div className="space-y-3">
              {Object.entries(m.breakdown).map(([key, value]) => (
                <CompatibilityBar key={key} label={key.replace(/_/g, " ")} value={value} />
              ))}
            </div>

            <div className="flex gap-3 mt-4">
              <Button fullWidth disabled={busy === m.match_id} onClick={() => accept(m.match_id)}>
                {busy === m.match_id ? "…" : "Accept"}
              </Button>
              <Button variant="ghost" disabled={busy === m.match_id} onClick={() => reject(m.match_id)}>
                Decline
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
