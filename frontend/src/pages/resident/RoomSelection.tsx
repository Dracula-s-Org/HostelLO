import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { RoomThumb } from "../../components/RoomThumb";
import { Button } from "../../components/Button";
import { Card, Chip, EmptyState, ErrorNote, Spinner } from "../../components/primitives";
import { api, ApiError } from "../../lib/api";
import { useAsync } from "../../lib/useAsync";
import type { Room } from "../../lib/types";

// GET /api/hostels/:id/rooms + POST /api/bookings.
export function RoomSelection() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const { data, loading, error } = useAsync(() => api.hostels.rooms(id), [id]);

  const [bookingId, setBookingId] = useState<string | null>(null);
  const [bookError, setBookError] = useState<string | null>(null);

  async function book(room: Room) {
    setBookError(null);
    setBookingId(room.id);
    try {
      const placement = await api.bookings.place(room.id);
      // Shared room with no pre-arranged roommate → go find one; otherwise the
      // request is in for owner approval.
      if (placement.is_shared && !placement.prebooked_match) {
        navigate(`/resident/bookings/${placement.id}/roommates`);
      } else {
        navigate("/resident/bookings");
      }
    } catch (err) {
      setBookError(err instanceof ApiError ? err.message : "Could not place the booking.");
      setBookingId(null);
    }
  }

  return (
    <div className="space-y-stack-md">
      <button
        onClick={() => navigate(`/resident/hostels/${id}`)}
        className="inline-flex items-center gap-1 text-label-md text-on-surface-variant hover:text-primary"
      >
        <Icon name="arrow_back" className="text-[18px]" /> Back to hostel
      </button>

      <h1 className="text-headline-lg-mobile md:text-headline-lg text-primary">Choose a room</h1>

      {loading && (
        <div className="flex justify-center py-stack-lg text-on-surface-variant">
          <Spinner className="text-3xl" />
        </div>
      )}
      {error && <ErrorNote message={error} />}
      {bookError && <ErrorNote message={bookError} />}
      {data && data.rooms.length === 0 && (
        <EmptyState icon="meeting_room" title="No rooms listed yet." />
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-gutter">
        {data?.rooms.map((room) => {
          const full = room.status === "FULL";
          const spots = room.capacity - room.occupied_count;
          return (
            <Card key={room.id}>
              <div className="flex gap-4">
                <RoomThumb room={room} className="w-24 h-24 shrink-0 rounded-lg" />
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-headline-md text-primary">{room.type === "SHARED" ? "Shared" : "Single"}</h3>
                    <Chip tone={full ? "neutral" : "primary"}>{full ? "Full" : `${spots} left`}</Chip>
                  </div>
                  <p className="text-headline-md text-on-surface">
                    ₹{room.price.toLocaleString("en-IN")}
                    <span className="text-label-sm text-on-surface-variant font-body"> /mo</span>
                  </p>
                  <p className="text-label-sm text-on-surface-variant">
                    Capacity {room.capacity} · {room.occupied_count} occupied
                  </p>
                </div>
              </div>
              <Button
                fullWidth
                className="mt-4"
                disabled={full || bookingId === room.id}
                onClick={() => book(room)}
              >
                {bookingId === room.id ? "Booking…" : full ? "Unavailable" : "Request to book"}
              </Button>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
