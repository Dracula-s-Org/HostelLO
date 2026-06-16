import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { Button } from "../../components/Button";
import { Card, Chip, EmptyState, ErrorNote, Spinner } from "../../components/primitives";
import { NumberField, SelectField } from "../../components/form";
import { api, ApiError } from "../../lib/api";
import { useAsync } from "../../lib/useAsync";

// Existing rooms come from the owner's hostel list; new rooms post to
// POST /api/hostels/:id/rooms (multipart, optional images).
export function ConfigureRooms() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { data, loading, error, reload } = useAsync(() => api.owners.listHostels(), []);
  const entry = data?.hostels.find((h) => h.hostel.id === id);

  const [type, setType] = useState("SINGLE");
  const [capacity, setCapacity] = useState<number | "">(1);
  const [price, setPrice] = useState<number | "">(8000);
  const [images, setImages] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function addRoom(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!capacity || !price) {
      setFormError("Capacity and price are required.");
      return;
    }
    setSubmitting(true);
    try {
      await api.owners.createRoom(id, { type, capacity: Number(capacity), price: Number(price), images });
      setImages([]);
      reload();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Could not add the room.");
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
        {entry ? entry.hostel.name : "Rooms"}
      </h1>

      {error && <ErrorNote message={error} />}

      <div className="space-y-3">
        {entry && entry.rooms.length === 0 && <EmptyState icon="meeting_room" title="No rooms yet." hint="Add your first below." />}
        {entry?.rooms.map((room) => (
          <Card key={room.id}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Icon name={room.type === "SHARED" ? "group" : "single_bed"} className="text-2xl text-primary" />
                <div>
                  <p className="text-label-md text-on-surface">{room.type === "SHARED" ? "Shared" : "Single"}</p>
                  <p className="text-label-sm text-on-surface-variant">
                    ₹{room.price.toLocaleString("en-IN")}/mo · {room.occupied_count}/{room.capacity} filled
                  </p>
                </div>
              </div>
              <Chip tone={room.status === "FULL" ? "neutral" : "primary"}>{room.status}</Chip>
            </div>
          </Card>
        ))}
      </div>

      <Card>
        <h3 className="text-headline-md text-primary mb-3">Add a room</h3>
        <form onSubmit={addRoom} className="space-y-stack-sm">
          <div className="grid grid-cols-2 gap-3">
            <SelectField
              label="Type"
              value={type}
              onChange={setType}
              options={[
                { value: "SINGLE", label: "Single" },
                { value: "SHARED", label: "Shared" },
              ]}
            />
            <NumberField label="Capacity" value={capacity} onChange={setCapacity} min={1} />
          </div>
          <NumberField label="Price (₹/mo)" value={price} onChange={setPrice} min={1} />

          <label className="flex items-center gap-2 rounded-lg border border-dashed border-outline-variant p-3 cursor-pointer hover:border-primary/50 transition-colors">
            <Icon name="add_photo_alternate" className="text-2xl text-primary" />
            <span className="text-label-md text-on-surface-variant">
              {images.length ? `${images.length} image(s) selected` : "Add room photos (optional)"}
            </span>
            <input
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              onChange={(e) => setImages(Array.from(e.target.files ?? []))}
            />
          </label>

          {formError && <ErrorNote message={formError} />}

          <Button type="submit" fullWidth disabled={submitting}>
            {submitting ? "Adding…" : "Add room"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
