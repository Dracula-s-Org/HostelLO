import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { Button } from "../../components/Button";
import { Card, Chip, CompatibilityBar, EmptyState, ErrorNote, Spinner } from "../../components/primitives";
import { api, ApiError } from "../../lib/api";
import { useAsync } from "../../lib/useAsync";

// GET /api/bookings/:id/roommate-recommendations + POST /api/roommate-matches.
// Proposing sends an invite; the candidate accepts on their own requests screen.
export function RoommateMatching() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { data, loading, error } = useAsync(() => api.bookings.roommateRecommendations(id), [id]);

  const [proposed, setProposed] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  async function propose(candidateId: string) {
    setActionError(null);
    setBusy(candidateId);
    try {
      await api.roommateMatches.create(candidateId);
      setProposed(candidateId);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Could not send the invite.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-stack-md">
      <button
        onClick={() => navigate("/resident/bookings")}
        className="inline-flex items-center gap-1 text-label-md text-on-surface-variant hover:text-primary"
      >
        <Icon name="arrow_back" className="text-[18px]" /> My bookings
      </button>

      <div>
        <h1 className="text-headline-lg-mobile md:text-headline-lg text-primary">Find your roommate</h1>
        <p className="text-body-md text-on-surface-variant max-w-2xl">
          Ranked by lifestyle compatibility. Send an invite — they confirm from their side, then the
          owner approves the pair.
        </p>
      </div>

      {loading && (
        <div className="flex justify-center py-stack-lg text-on-surface-variant">
          <Spinner className="text-3xl" />
        </div>
      )}
      {error && <ErrorNote message={error} />}
      {actionError && <ErrorNote message={actionError} />}
      {data && data.candidates.length === 0 && (
        <EmptyState icon="person_search" title="No compatible candidates yet." hint="Check back as more residents join this room." />
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-gutter">
        {data?.candidates.map((c) => {
          const sent = proposed === c.candidate_id;
          return (
            <Card key={c.candidate_id}>
              <div className="flex items-start gap-4 mb-4">
                <div className="w-14 h-14 rounded-full bg-primary-container text-white flex items-center justify-center text-headline-md font-heading">
                  {c.first_name.charAt(0)}
                </div>
                <div className="flex-1">
                  <h3 className="text-headline-md text-primary">{c.first_name}</h3>
                  <div className="flex flex-wrap gap-2 mt-1">
                    <Chip tone="neutral">{c.habits.sleep_schedule === "EARLY" ? "Early bird" : "Night owl"}</Chip>
                    <Chip tone="neutral">{c.habits.social_type === "INTROVERT" ? "Introvert" : "Extrovert"}</Chip>
                  </div>
                </div>
                <span className="text-label-md text-primary bg-primary-fixed rounded-full px-3 py-1">
                  {Math.round(c.overall_score)}%
                </span>
              </div>

              <div className="space-y-3">
                {Object.entries(c.breakdown).map(([key, value]) => (
                  <CompatibilityBar key={key} label={key.replace(/_/g, " ")} value={value} />
                ))}
              </div>

              <Button fullWidth className="mt-4" disabled={sent || busy === c.candidate_id} onClick={() => propose(c.candidate_id)}>
                {sent ? "Invite sent" : busy === c.candidate_id ? "Sending…" : "Send roommate invite"}
              </Button>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
