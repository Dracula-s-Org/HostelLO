import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { Button } from "../../components/Button";
import { Card, ErrorNote, Spinner } from "../../components/primitives";
import { NumberField, SelectField, TextField, ToggleField } from "../../components/form";
import { api, ApiError } from "../../lib/api";
import type { HostelInput } from "../../lib/api";

const EMPTY: HostelInput = {
  name: "",
  address: "",
  location: "",
  gender_policy: "COED",
  listing_tier: "FREE",
  allow_smoking: false,
  allow_drinking: false,
  veg_only: false,
  min_age: null,
  max_age: null,
  amenities: "",
};

// POST /api/owners/hostels (create) or PUT /api/owners/hostels/:id (edit).
// Edit prefills from the owner's hostel list (no owner-facing single-GET exists).
export function CreateEditHostel() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  const [form, setForm] = useState<HostelInput>(EMPTY);
  const [loading, setLoading] = useState(isEdit);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const set = <K extends keyof HostelInput>(key: K, value: HostelInput[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  useEffect(() => {
    if (!isEdit) return;
    let alive = true;
    (async () => {
      try {
        const { hostels } = await api.owners.listHostels();
        const match = hostels.find((h) => h.hostel.id === id);
        if (!match) {
          if (alive) setError("Hostel not found.");
          return;
        }
        const h = match.hostel;
        if (alive)
          setForm({
            name: h.name,
            address: h.address,
            location: h.location,
            gender_policy: h.gender_policy,
            listing_tier: h.listing_tier,
            allow_smoking: h.allow_smoking,
            allow_drinking: h.allow_drinking,
            veg_only: h.veg_only,
            min_age: h.min_age,
            max_age: h.max_age,
            amenities: h.amenities.join(", "),
          });
      } catch (err) {
        if (alive) setError(err instanceof ApiError ? err.message : "Could not load the hostel.");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [id, isEdit]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!form.name.trim() || !form.address.trim() || !form.location.trim()) {
      setError("Name, address, and location are required.");
      return;
    }
    setSubmitting(true);
    try {
      if (isEdit && id) {
        await api.owners.updateHostel(id, form);
        navigate("/owner");
      } else {
        const created = await api.owners.createHostel(form);
        navigate(`/owner/hostels/${created.id}/rooms`);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save the hostel.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-stack-lg text-on-surface-variant">
        <Spinner className="text-3xl" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-stack-md">
      <button
        onClick={() => navigate("/owner")}
        className="inline-flex items-center gap-1 text-label-md text-on-surface-variant hover:text-primary"
      >
        <Icon name="arrow_back" className="text-[18px]" /> Dashboard
      </button>
      <h1 className="text-headline-lg-mobile md:text-headline-lg text-primary">
        {isEdit ? "Edit hostel" : "Add a hostel"}
      </h1>

      <Card>
        <form onSubmit={submit} className="space-y-stack-sm">
          <TextField label="Hostel name" value={form.name} onChange={(v) => set("name", v)} />
          <TextField label="Address" value={form.address} onChange={(v) => set("address", v)} />
          <TextField label="Location (city/area)" value={form.location} onChange={(v) => set("location", v)} placeholder="e.g. Bangalore" />

          <div className="grid grid-cols-2 gap-3">
            <SelectField
              label="Gender policy"
              value={form.gender_policy}
              onChange={(v) => set("gender_policy", v)}
              options={[
                { value: "COED", label: "Co-ed" },
                { value: "MALE", label: "Male only" },
                { value: "FEMALE", label: "Female only" },
              ]}
            />
            <SelectField
              label="Listing tier"
              value={form.listing_tier}
              onChange={(v) => set("listing_tier", v)}
              options={[
                { value: "FREE", label: "Free" },
                { value: "PREMIUM", label: "Premium" },
              ]}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <NumberField label="Min age" value={form.min_age ?? ""} onChange={(v) => set("min_age", v === "" ? null : Number(v))} />
            <NumberField label="Max age" value={form.max_age ?? ""} onChange={(v) => set("max_age", v === "" ? null : Number(v))} />
          </div>

          <ToggleField label="Allow smoking" checked={form.allow_smoking} onChange={(v) => set("allow_smoking", v)} />
          <ToggleField label="Allow drinking" checked={form.allow_drinking} onChange={(v) => set("allow_drinking", v)} />
          <ToggleField label="Vegetarian only" checked={form.veg_only} onChange={(v) => set("veg_only", v)} />

          <TextField
            label="Amenities (comma-separated)"
            value={form.amenities ?? ""}
            onChange={(v) => set("amenities", v)}
            placeholder="wifi, ac, laundry"
          />

          {error && <ErrorNote message={error} />}

          <Button type="submit" fullWidth size="lg" disabled={submitting}>
            {submitting ? "Saving…" : isEdit ? "Save changes" : "Create & add rooms"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
