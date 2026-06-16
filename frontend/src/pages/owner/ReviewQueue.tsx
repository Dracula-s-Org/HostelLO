import { useState } from "react";
import { Icon } from "../../components/Icon";
import { Button } from "../../components/Button";
import { Card, Chip, CompatibilityBar, EmptyState, ErrorNote, Spinner } from "../../components/primitives";
import { api, ApiError } from "../../lib/api";
import { useAsync } from "../../lib/useAsync";
import type { OwnerApplicant } from "../../lib/types";

// GET /api/owners/bookings + approve/reject. Applicant data is pre-approval
// gated (first name + habits only).
export function ReviewQueue() {
  const { data, loading, error, reload } = useAsync(() => api.ownerBookings.queue(), []);
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  async function decide(bookingId: string, action: "approve" | "reject") {
    setActionError(null);
    setNote(null);
    setBusy(bookingId);
    try {
      if (action === "approve") {
        const res = await api.ownerBookings.approve(bookingId);
        setNote(res.room_full ? "Approved. Room is now full — competing requests were declined." : "Booking approved.");
      } else {
        await api.ownerBookings.reject(bookingId);
        setNote("Booking declined.");
      }
      reload();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Action failed.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-stack-md">
      <h1 className="text-headline-lg-mobile md:text-headline-lg text-primary">Review queue</h1>

      {note && (
        <div className="flex items-center gap-2 rounded-lg bg-tertiary-fixed text-on-tertiary-fixed-variant p-3 text-label-md">
          <Icon name="check_circle" className="text-[18px]" filled />
          {note}
        </div>
      )}
      {loading && (
        <div className="flex justify-center py-stack-lg text-on-surface-variant">
          <Spinner className="text-3xl" />
        </div>
      )}
      {error && <ErrorNote message={error} />}
      {actionError && <ErrorNote message={actionError} />}
      {data && data.queue.length === 0 && (
        <EmptyState icon="inbox" title="No pending requests." hint="New booking requests show up here." />
      )}

      <div className="space-y-gutter">
        {data?.queue.map((item) => (
          <Card key={item.booking.id}>
            <div className="flex items-start justify-between gap-3 mb-3">
              <div>
                <h3 className="text-headline-md text-primary">
                  {item.applicant?.first_name ?? "Applicant"}
                  {item.applicant && <span className="text-on-surface-variant font-body">, {item.applicant.age}</span>}
                </h3>
                <p className="text-label-md text-on-surface-variant">
                  {item.hostel.name} · {item.room.type === "SHARED" ? "Shared" : "Single"} · ₹
                  {item.room.price.toLocaleString("en-IN")}/mo
                </p>
              </div>
              {item.match && <Chip tone="secondary">{item.match.score}% pair</Chip>}
            </div>

            {item.applicant && <HabitTags habits={item.applicant.habits} />}

            {item.match && (
              <div className="space-y-2 mt-3 pt-3 border-t border-outline-variant/40">
                <p className="text-label-sm text-on-surface-variant uppercase tracking-wide">Roommate compatibility</p>
                {Object.entries(item.match.breakdown).map(([key, value]) => (
                  <CompatibilityBar key={key} label={key.replace(/_/g, " ")} value={value} />
                ))}
              </div>
            )}

            <div className="flex gap-3 mt-4">
              <Button fullWidth disabled={busy === item.booking.id} onClick={() => decide(item.booking.id, "approve")}>
                {busy === item.booking.id ? "…" : "Approve"}
              </Button>
              <Button variant="ghost" disabled={busy === item.booking.id} onClick={() => decide(item.booking.id, "reject")}>
                Decline
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function HabitTags({ habits }: { habits: OwnerApplicant["habits"] }) {
  const tags = [
    habits.sleep_schedule === "EARLY" ? "Early bird" : "Night owl",
    habits.social_type === "INTROVERT" ? "Introvert" : "Extrovert",
    `Diet: ${habits.diet}`,
    `Cleanliness ${habits.cleanliness}/5`,
    habits.smoking ? "Smoker" : "Non-smoker",
    habits.drinking ? "Drinks" : "No alcohol",
  ];
  return (
    <div className="flex flex-wrap gap-2">
      {tags.map((t) => (
        <Chip key={t} tone="neutral">
          {t}
        </Chip>
      ))}
    </div>
  );
}
