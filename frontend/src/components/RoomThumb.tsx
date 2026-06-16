import { useState } from "react";
import { Icon, type IconName } from "./Icon";
import { api } from "../lib/api";
import type { Room } from "../lib/types";

// Room image via the gated proxy (GET /api/assets/rooms/:id/:index — any
// authenticated user can read). Falls back to a tonal block when there's no
// image or the file 404s, so a broken asset never shows a busted <img>.
export function RoomThumb({
  room,
  className = "",
  fallbackIcon,
}: {
  room: Pick<Room, "id" | "type" | "image_count">;
  className?: string;
  fallbackIcon?: IconName;
}) {
  const [failed, setFailed] = useState(false);
  const icon: IconName = fallbackIcon ?? (room.type === "SHARED" ? "group" : "single_bed");
  const showImage = room.image_count > 0 && !failed;

  return (
    <div className={`overflow-hidden bg-gradient-to-br from-primary-fixed to-tertiary-fixed flex items-center justify-center ${className}`}>
      {showImage ? (
        <img
          src={api.roomImageUrl(room.id, 0)}
          alt=""
          loading="lazy"
          onError={() => setFailed(true)}
          className="w-full h-full object-cover"
        />
      ) : (
        <Icon name={icon} className="text-3xl text-primary/40" />
      )}
    </div>
  );
}
