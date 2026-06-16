import { Link, useParams } from "react-router-dom";
import { Icon, type IconName } from "../../components/Icon";
import { Badge, Card, Chip, ErrorNote, Spinner } from "../../components/primitives";
import { Button } from "../../components/Button";
import { api } from "../../lib/api";
import { useAsync } from "../../lib/useAsync";

// GET /api/hostels/:id — hostel detail screen.
export function HostelDetail() {
  const { id = "" } = useParams();
  const { data: hostel, loading, error } = useAsync(() => api.hostels.detail(id), [id]);

  if (loading) {
    return (
      <div className="flex justify-center py-stack-lg text-on-surface-variant">
        <Spinner className="text-3xl" />
      </div>
    );
  }
  if (error) return <ErrorNote message={error} />;
  if (!hostel) return null;

  return (
    <div className="space-y-stack-md">
      <Link to="/resident/hostels" className="inline-flex items-center gap-1 text-label-md text-on-surface-variant hover:text-primary">
        <Icon name="arrow_back" className="text-[18px]" /> Back to results
      </Link>

      <div className="aspect-[21/9] rounded-xl bg-gradient-to-br from-primary-fixed via-surface-container to-tertiary-fixed flex items-center justify-center">
        <Icon name="apartment" className="text-6xl text-primary/30" />
      </div>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-headline-lg-mobile md:text-headline-lg text-primary">{hostel.name}</h1>
          <p className="text-body-md text-on-surface-variant flex items-center gap-1">
            <Icon name="place" className="text-[18px]" />
            {hostel.address}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {hostel.verified && <Badge icon="verified">Verified</Badge>}
          {hostel.listing_tier === "PREMIUM" && <Chip tone="secondary">Premium</Chip>}
        </div>
      </div>

      <Card>
        <h3 className="text-headline-md text-primary mb-3">House rules & policy</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-label-md">
          <Fact icon="wc" label="Gender" value={hostel.gender_policy} />
          <Fact icon="smoking_rooms" label="Smoking" value={hostel.allow_smoking ? "Allowed" : "No"} />
          <Fact icon="local_bar" label="Drinking" value={hostel.allow_drinking ? "Allowed" : "No"} />
          <Fact icon="restaurant" label="Diet" value={hostel.veg_only ? "Veg only" : "Any"} />
          {(hostel.min_age || hostel.max_age) && (
            <Fact icon="cake" label="Age" value={`${hostel.min_age ?? "—"}–${hostel.max_age ?? "—"}`} />
          )}
        </div>
      </Card>

      {hostel.amenities.length > 0 && (
        <Card>
          <h3 className="text-headline-md text-primary mb-3">Amenities</h3>
          <div className="flex flex-wrap gap-2">
            {hostel.amenities.map((a) => (
              <Chip key={a} tone="neutral">
                {a}
              </Chip>
            ))}
          </div>
        </Card>
      )}

      <Link to={`/resident/hostels/${hostel.id}/rooms`}>
        <Button fullWidth size="lg">
          View rooms <Icon name="arrow_forward" className="text-[18px]" />
        </Button>
      </Link>
    </div>
  );
}

function Fact({ icon, label, value }: { icon: IconName; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2">
      <Icon name={icon} className="text-[20px] text-primary" />
      <div>
        <p className="text-label-sm text-on-surface-variant">{label}</p>
        <p className="text-label-md text-on-surface">{value}</p>
      </div>
    </div>
  );
}
