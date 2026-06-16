import { Link, useParams } from "react-router-dom";
import { Icon, type IconName } from "../../components/Icon";
import { Button } from "../../components/Button";
import { Card, ErrorNote, Spinner } from "../../components/primitives";
import { api } from "../../lib/api";
import { useAsync } from "../../lib/useAsync";
import type { BookingStatus } from "../../lib/types";

const STATUS_STYLE: Record<BookingStatus, { tone: string; icon: IconName; label: string }> = {
  REQUESTED: { tone: "bg-secondary-fixed text-on-secondary-fixed-variant", icon: "hourglass_top", label: "Awaiting approval" },
  CONFIRMED: { tone: "bg-tertiary-fixed text-on-tertiary-fixed-variant", icon: "check_circle", label: "Confirmed" },
  REJECTED: { tone: "bg-error-container text-on-error-container", icon: "cancel", label: "Rejected" },
  CANCELLED: { tone: "bg-surface-container text-on-surface-variant", icon: "block", label: "Cancelled" },
};

// GET /api/bookings/:id — booking detail screen. Owner contact is present only
// when the booking is CONFIRMED (the backend gates the PII).
export function BookingDetail() {
  const { id = "" } = useParams();
  const { data, loading, error } = useAsync(() => api.bookings.detail(id), [id]);

  if (loading) {
    return (
      <div className="flex justify-center py-stack-lg text-on-surface-variant">
        <Spinner className="text-3xl" />
      </div>
    );
  }
  if (error) return <ErrorNote message={error} />;
  if (!data) return null;

  const style = STATUS_STYLE[data.status];

  return (
    <div className="space-y-stack-md">
      <Link to="/resident/bookings" className="inline-flex items-center gap-1 text-label-md text-on-surface-variant hover:text-primary">
        <Icon name="arrow_back" className="text-[18px]" /> Back to my bookings
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-headline-lg-mobile md:text-headline-lg text-primary">{data.hostel.name}</h1>
          <p className="text-body-md text-on-surface-variant flex items-center gap-1">
            <Icon name="place" className="text-[18px]" />
            {data.hostel.address}
          </p>
        </div>
        <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-label-sm ${style.tone}`}>
          <Icon name={style.icon} className="text-[16px]" filled />
          {style.label}
        </span>
      </div>

      <Card>
        <h3 className="text-headline-md text-primary mb-3">Your room</h3>
        <p className="text-body-md text-on-surface">
          {data.room.type === "SHARED" ? "Shared" : "Single"} room · ₹{data.room.price.toLocaleString("en-IN")}/mo
        </p>
      </Card>

      {data.owner ? (
        <Card>
          <h3 className="text-headline-md text-primary mb-3">Owner contact</h3>
          <div className="space-y-2 text-label-md">
            <div className="flex items-center gap-2">
              <Icon name="handshake" className="text-[20px] text-primary" />
              <span className="text-on-surface">{data.owner.name}</span>
            </div>
            <a
              href={`tel:${data.owner.contact}`}
              className="inline-flex items-center gap-2 text-body-lg text-primary font-semibold hover:underline"
            >
              {data.owner.contact}
            </a>
          </div>
        </Card>
      ) : (
        <Card>
          <p className="text-label-md text-on-surface-variant flex items-center gap-2">
            <Icon name="hourglass_top" className="text-[18px]" />
            The owner's contact details unlock once your booking is confirmed.
          </p>
        </Card>
      )}

      <Link to={`/resident/hostels/${data.hostel.id}`}>
        <Button fullWidth size="lg">
          View full listing <Icon name="arrow_forward" className="text-[18px]" />
        </Button>
      </Link>
    </div>
  );
}
