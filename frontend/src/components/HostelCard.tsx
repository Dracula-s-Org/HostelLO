import { Link } from "react-router-dom";
import { Icon } from "./Icon";
import { RoomThumb } from "./RoomThumb";
import { Badge, Chip } from "./primitives";
import type { Hostel, Room } from "../lib/types";

function fromPrice(rooms: Room[]): number | null {
  const prices = rooms.map((r) => r.price).filter((p) => p > 0);
  return prices.length ? Math.min(...prices) : null;
}

// Hostel listing card used in recommendations and search.
export function HostelCard({
  hostel,
  rooms,
  score,
}: {
  hostel: Hostel;
  rooms: Room[];
  score?: number;
}) {
  const price = fromPrice(rooms);
  const cover = rooms.find((r) => r.image_count > 0);
  return (
    <Link to={`/resident/hostels/${hostel.id}`}>
      <article className="bg-surface-container-lowest rounded-xl overflow-hidden border border-outline-variant/30 shadow-card hover:shadow-card-hover transition-all">
        {cover ? (
          <RoomThumb room={cover} className="aspect-[16/9]" fallbackIcon="apartment" />
        ) : (
          <div className="aspect-[16/9] bg-gradient-to-br from-primary-fixed to-tertiary-fixed flex items-center justify-center">
            <Icon name="apartment" className="text-5xl text-primary/30" />
          </div>
        )}
        <div className="p-stack-md space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-headline-md text-primary">{hostel.name}</h3>
              <p className="text-label-md text-on-surface-variant flex items-center gap-1">
                <Icon name="place" className="text-[16px]" />
                {hostel.location}
              </p>
            </div>
            {score !== undefined && (
              <span className="shrink-0 text-label-md text-primary bg-primary-fixed rounded-full px-3 py-1">
                {Math.round(score)}% match
              </span>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            {hostel.verified && <Badge icon="verified">Verified</Badge>}
            {hostel.listing_tier === "PREMIUM" && <Chip tone="secondary">Premium</Chip>}
            <Chip tone="neutral">{hostel.gender_policy}</Chip>
            {hostel.veg_only && <Chip>Veg only</Chip>}
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-headline-md text-on-surface">
              {price !== null ? `₹${price.toLocaleString("en-IN")}` : "—"}
              <span className="text-label-sm text-on-surface-variant font-body"> /mo</span>
            </span>
            <span className="text-label-md text-primary flex items-center gap-1">
              View <Icon name="arrow_forward" className="text-[16px]" />
            </span>
          </div>
        </div>
      </article>
    </Link>
  );
}
