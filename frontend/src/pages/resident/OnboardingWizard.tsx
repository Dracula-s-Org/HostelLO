import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AuthLayout } from "../auth/AuthLayout";
import { Button } from "../../components/Button";
import { Stepper, ErrorNote } from "../../components/primitives";
import { NumberField, ScaleField, SelectField, TextField, ToggleField } from "../../components/form";
import { api, ApiError } from "../../lib/api";
import type { ResidentProfileInput } from "../../lib/api";

const STEPS = ["Identity", "Lifestyle", "Habits"];

const DEFAULTS: ResidentProfileInput = {
  name: "",
  age: 18,
  gender: "MALE",
  budget_min: 5000,
  budget_max: 15000,
  preferred_location: "",
  sleep_schedule: "EARLY",
  cleanliness: 3,
  diet: "VEG",
  social_type: "INTROVERT",
  gaming_freq: 2,
  study_habits: 2,
  fitness_freq: 2,
  visitors_freq: 2,
  smoking: false,
  drinking: false,
  seeking_shared: true,
  prebooked_roommate_phone: "",
  amenity_preferences: "",
};

// Multi-step resident profile setup. All steps write to one profile via
// POST /api/residents/profile on the final submit.
export function OnboardingWizard() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<ResidentProfileInput>(DEFAULTS);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const set = <K extends keyof ResidentProfileInput>(key: K, value: ResidentProfileInput[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  function next() {
    if (step === 0 && (!form.name.trim() || !form.preferred_location.trim())) {
      setError("Name and preferred location are required.");
      return;
    }
    setError(null);
    setStep((s) => Math.min(s + 1, STEPS.length - 1));
  }

  async function submit() {
    setError(null);
    setSubmitting(true);
    try {
      await api.residents.createProfile(form);
      navigate("/resident", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save your profile.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout title="Set up your profile" subtitle="This powers your hostel and roommate matches.">
      <div className="space-y-stack-md">
        <Stepper steps={STEPS} current={step} />

        {step === 0 && (
          <div className="space-y-stack-sm">
            <TextField label="Full name" value={form.name} onChange={(v) => set("name", v)} placeholder="Your name" />
            <div className="grid grid-cols-2 gap-3">
              <NumberField label="Age" value={form.age} onChange={(v) => set("age", Number(v) || 0)} min={16} max={99} />
              <SelectField
                label="Gender"
                value={form.gender}
                onChange={(v) => set("gender", v)}
                options={[
                  { value: "MALE", label: "Male" },
                  { value: "FEMALE", label: "Female" },
                ]}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <NumberField label="Budget min (₹)" value={form.budget_min} onChange={(v) => set("budget_min", Number(v) || 0)} />
              <NumberField label="Budget max (₹)" value={form.budget_max} onChange={(v) => set("budget_max", Number(v) || 0)} />
            </div>
            <TextField
              label="Preferred location"
              value={form.preferred_location}
              onChange={(v) => set("preferred_location", v)}
              placeholder="e.g. Bangalore"
            />
          </div>
        )}

        {step === 1 && (
          <div className="space-y-stack-sm">
            <SelectField
              label="Sleep schedule"
              value={form.sleep_schedule}
              onChange={(v) => set("sleep_schedule", v)}
              options={[
                { value: "EARLY", label: "Early bird" },
                { value: "NIGHT", label: "Night owl" },
              ]}
            />
            <SelectField
              label="Diet"
              value={form.diet}
              onChange={(v) => set("diet", v)}
              options={[
                { value: "VEG", label: "Vegetarian" },
                { value: "NONVEG", label: "Non-vegetarian" },
                { value: "EGGETARIAN", label: "Eggetarian" },
              ]}
            />
            <SelectField
              label="Social type"
              value={form.social_type}
              onChange={(v) => set("social_type", v)}
              options={[
                { value: "INTROVERT", label: "Introvert" },
                { value: "EXTROVERT", label: "Extrovert" },
              ]}
            />
            <ToggleField label="I smoke" checked={form.smoking} onChange={(v) => set("smoking", v)} />
            <ToggleField label="I drink" checked={form.drinking} onChange={(v) => set("drinking", v)} />
            <ToggleField label="Open to a shared room" checked={form.seeking_shared} onChange={(v) => set("seeking_shared", v)} />
            <TextField
              label="Pre-arranged roommate's phone (optional)"
              value={form.prebooked_roommate_phone ?? ""}
              onChange={(v) => set("prebooked_roommate_phone", v)}
              placeholder="+91…"
            />
          </div>
        )}

        {step === 2 && (
          <div className="space-y-stack-md">
            <ScaleField label="Cleanliness" value={form.cleanliness} onChange={(v) => set("cleanliness", v)} max={5} lowHint="Relaxed" highHint="Spotless" />
            <ScaleField label="Gaming" value={form.gaming_freq} onChange={(v) => set("gaming_freq", v)} max={4} lowHint="Never" highHint="Daily" />
            <ScaleField label="Study habits" value={form.study_habits} onChange={(v) => set("study_habits", v)} max={4} lowHint="Light" highHint="Intense" />
            <ScaleField label="Fitness" value={form.fitness_freq} onChange={(v) => set("fitness_freq", v)} max={4} lowHint="Never" highHint="Daily" />
            <ScaleField label="Visitors" value={form.visitors_freq} onChange={(v) => set("visitors_freq", v)} max={4} lowHint="Rarely" highHint="Often" />
            <TextField
              label="Preferred amenities (comma-separated)"
              value={form.amenity_preferences ?? ""}
              onChange={(v) => set("amenity_preferences", v)}
              placeholder="wifi, ac, gym"
            />
          </div>
        )}

        {error && <ErrorNote message={error} />}

        <div className="flex gap-3">
          {step > 0 && (
            <Button variant="ghost" onClick={() => setStep((s) => s - 1)}>
              Back
            </Button>
          )}
          {step < STEPS.length - 1 ? (
            <Button fullWidth onClick={next}>
              Continue
            </Button>
          ) : (
            <Button fullWidth onClick={submit} disabled={submitting}>
              {submitting ? "Saving…" : "Finish setup"}
            </Button>
          )}
        </div>
      </div>
    </AuthLayout>
  );
}
