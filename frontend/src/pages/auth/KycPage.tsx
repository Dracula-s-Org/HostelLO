import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AuthLayout } from "./AuthLayout";
import { Button } from "../../components/Button";
import { Icon } from "../../components/Icon";
import { ErrorNote, Spinner, StatusDot } from "../../components/primitives";
import { api, ApiError } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { useAsync } from "../../lib/useAsync";

const DOC_TYPES = [
  { value: "AADHAAR", label: "Aadhaar" },
  { value: "PAN", label: "PAN card" },
  { value: "PASSPORT", label: "Passport" },
  { value: "DRIVING_LICENSE", label: "Driving licence" },
  { value: "VOTER_ID", label: "Voter ID" },
];

export function KycPage() {
  const navigate = useNavigate();
  const { role } = useAuth();
  const { data, loading, error, reload } = useAsync(() => api.kyc.status(), []);

  const [docType, setDocType] = useState("AADHAAR");
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const status = data?.kyc_status ?? "NONE";
  const verified = status === "VERIFIED";
  const homePath = role === "OWNER" ? "/owner" : "/resident";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setSubmitError(null);
    setSubmitting(true);
    try {
      await api.kyc.submit(docType, file);
      reload(); // submit returns an HTML snippet; refetch the JSON status
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "Upload failed. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout title="Identity verification" subtitle="A one-time KYC check keeps the community safe.">
      {loading ? (
        <div className="flex justify-center py-stack-lg text-on-surface-variant">
          <Spinner className="text-3xl" />
        </div>
      ) : (
        <div className="space-y-stack-md">
          {error && <ErrorNote message={error} />}

          <div className="flex items-center gap-2 rounded-lg bg-surface-container-low p-3">
            <StatusDot status={status} />
            <span className="text-label-md text-on-surface">
              Status: <b>{status}</b>
            </span>
          </div>

          {verified ? (
            <>
              <div className="flex items-center gap-2 rounded-lg bg-tertiary-fixed text-on-tertiary-fixed-variant p-3 text-label-md">
                <Icon name="verified" filled className="text-[18px]" />
                You're verified. Welcome aboard.
              </div>
              <Button fullWidth size="lg" onClick={() => navigate(homePath, { replace: true })}>
                Continue
              </Button>
            </>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-stack-md">
              <div>
                <label htmlFor="docType" className="block text-label-md text-on-surface mb-1.5">
                  Document type
                </label>
                <select
                  id="docType"
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                  className="w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-4 py-3 text-body-md focus:outline-none focus:border-primary"
                >
                  {DOC_TYPES.map((d) => (
                    <option key={d.value} value={d.value}>
                      {d.label}
                    </option>
                  ))}
                </select>
              </div>

              <label className="flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-outline-variant p-6 cursor-pointer hover:border-primary/50 transition-colors">
                <Icon name="upload_file" className="text-3xl text-primary" />
                <span className="text-label-md text-on-surface">
                  {file ? file.name : "Upload document (PDF or image)"}
                </span>
                <input
                  type="file"
                  accept="image/*,application/pdf"
                  className="hidden"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
              </label>

              {submitError && <ErrorNote message={submitError} />}

              <Button type="submit" fullWidth size="lg" disabled={!file || submitting}>
                {submitting ? "Submitting…" : "Submit for verification"}
              </Button>
            </form>
          )}
        </div>
      )}
    </AuthLayout>
  );
}
