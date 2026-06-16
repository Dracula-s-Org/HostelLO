import { useState } from "react";
import { Button } from "../../components/Button";
import { Card, ErrorNote } from "../../components/primitives";
import { TextField } from "../../components/form";
import { api, ApiError } from "../../lib/api";

// Shown when an owner has no profile yet (POST /api/owners/profile is an upsert).
export function OwnerProfileSetup({ onDone }: { onDone: () => void }) {
  const [name, setName] = useState("");
  const [contact, setContact] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.owners.upsertProfile(name.trim(), contact.trim());
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save your details.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-md mx-auto">
      <h1 className="text-headline-lg-mobile text-primary mb-2">Tell us about you</h1>
      <p className="text-body-md text-on-surface-variant mb-stack-md">
        This is how residents and our team reach you.
      </p>
      <Card>
        <form onSubmit={submit} className="space-y-stack-sm">
          <TextField label="Your name" value={name} onChange={setName} placeholder="Full name" />
          <TextField label="Contact" value={contact} onChange={setContact} placeholder="Phone or email" />
          {error && <ErrorNote message={error} />}
          <Button type="submit" fullWidth size="lg" disabled={submitting || !name.trim() || !contact.trim()}>
            {submitting ? "Saving…" : "Save & continue"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
