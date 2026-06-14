// Typed client for the HostelLo FastAPI backend.
//
// Auth is a JWT in an httpOnly cookie; the app is served same-origin, so every
// request just needs `credentials: "include"`. Most write endpoints take form
// fields (`Form(...)` in FastAPI); POST /api/bookings is the one JSON body.
import type {
  BookingPlacement,
  BookingSummary,
  Candidate,
  ConfirmedRoommate,
  Hostel,
  KycStatusResponse,
  OwnerHostel,
  OwnerProfile,
  PendingMatch,
  Recommendation,
  ResidentProfile,
  ReviewItem,
  Role,
  Room,
} from "./types";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type Primitive = string | number | boolean | null | undefined;

function toForm(fields: Record<string, Primitive>): URLSearchParams {
  const body = new URLSearchParams();
  for (const [key, value] of Object.entries(fields)) {
    if (value === null || value === undefined) continue;
    body.append(key, typeof value === "boolean" ? String(value) : String(value));
  }
  return body;
}

async function parseError(res: Response): Promise<never> {
  let message = res.statusText || `Request failed (${res.status})`;
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") {
      message = data.detail;
    } else if (Array.isArray(data?.detail) && data.detail[0]?.msg) {
      message = data.detail[0].msg; // FastAPI validation error
    }
  } catch {
    /* non-JSON body — keep the status text */
  }
  throw new ApiError(res.status, message);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(path, { credentials: "include", ...init });
  if (!res.ok) await parseError(res);
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return (await res.json()) as T;
  // A few endpoints (kyc/submit) still answer with an HTML snippet; callers
  // that need fresh state re-fetch the JSON status endpoint afterwards.
  return undefined as T;
}

function getJson<T>(path: string): Promise<T> {
  return request<T>(path, { headers: { Accept: "application/json" } });
}

function postForm<T>(path: string, fields: Record<string, Primitive>): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Accept: "application/json",
    },
    body: toForm(fields),
  });
}

function putForm<T>(path: string, fields: Record<string, Primitive>): Promise<T> {
  return request<T>(path, {
    method: "PUT",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Accept: "application/json",
    },
    body: toForm(fields),
  });
}

function postJson<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
}

function postMultipart<T>(path: string, form: FormData): Promise<T> {
  // No explicit Content-Type — the browser sets the multipart boundary.
  return request<T>(path, { method: "POST", headers: { Accept: "application/json" }, body: form });
}

export interface HostelInput {
  name: string;
  address: string;
  location: string;
  gender_policy: string;
  listing_tier: string;
  allow_smoking: boolean;
  allow_drinking: boolean;
  veg_only: boolean;
  min_age?: number | null;
  max_age?: number | null;
  amenities?: string; // comma-separated, as the form endpoint expects
}

export interface ResidentProfileInput {
  name: string;
  age: number;
  gender: string;
  budget_min: number;
  budget_max: number;
  preferred_location: string;
  sleep_schedule: string;
  cleanliness: number;
  diet: string;
  social_type: string;
  gaming_freq: number;
  study_habits: number;
  fitness_freq: number;
  visitors_freq: number;
  smoking: boolean;
  drinking: boolean;
  seeking_shared: boolean;
  prebooked_roommate_phone?: string;
  amenity_preferences?: string;
}

export const api = {
  auth: {
    requestOtp: (phone: string, role: Role) =>
      postForm<{ detail: string }>("/api/auth/request-otp", { phone, role }),
    verifyOtp: (phone: string, code: string) =>
      postForm<{ detail: string; role: Role; redirect: string }>("/api/auth/verify-otp", {
        phone,
        code,
      }),
    logout: () => postJson<{ detail: string }>("/api/auth/logout", {}),
  },

  kyc: {
    status: () => getJson<KycStatusResponse>("/api/kyc/status"),
    submit: (docType: string, document: File) => {
      const form = new FormData();
      form.append("doc_type", docType);
      form.append("document", document);
      return postMultipart<void>("/api/kyc/submit", form);
    },
  },

  residents: {
    me: () => getJson<ResidentProfile>("/api/residents/me"),
    createProfile: (input: ResidentProfileInput) =>
      postForm<void>("/api/residents/profile", { ...input }),
    updateProfile: (input: Partial<ResidentProfileInput>) =>
      putForm<void>("/api/residents/profile", { ...input }),
    recommendations: () =>
      getJson<{ results: Recommendation[] }>("/api/residents/recommendations"),
  },

  hostels: {
    detail: (id: string) => getJson<Hostel>(`/api/hostels/${id}`),
    rooms: (id: string) => getJson<{ rooms: Room[] }>(`/api/hostels/${id}/rooms`),
  },

  bookings: {
    place: (roomId: string) => postJson<BookingPlacement>("/api/bookings", { roomId }),
    cancel: (id: string) =>
      postJson<{ id: string; status: string; detail: string }>(`/api/bookings/${id}/cancel`, {}),
    roommateRecommendations: (bookingId: string) =>
      getJson<{ candidates: Candidate[] }>(`/api/bookings/${bookingId}/roommate-recommendations`),
    mine: () => getJson<{ bookings: BookingSummary[] }>("/api/bookings/mine"),
  },

  roommateMatches: {
    create: (candidateId: string) =>
      postForm<{ match_id: string; status: string; score: number; breakdown: Record<string, number> }>(
        "/api/roommate-matches",
        { candidateId },
      ),
    accept: (matchId: string) =>
      postJson<{ match_id: string; status: string; booking_id: string; roommate: ConfirmedRoommate }>(
        `/api/roommate-matches/${matchId}/accept`,
        {},
      ),
    reject: (matchId: string) =>
      postJson<{ match_id: string; status: string }>(`/api/roommate-matches/${matchId}/reject`, {}),
    pending: () => getJson<{ pending: PendingMatch[] }>("/api/roommate-matches/pending"),
  },

  owners: {
    me: () => getJson<OwnerProfile>("/api/owners/me"),
    upsertProfile: (name: string, contact: string) =>
      postForm<OwnerProfile>("/api/owners/profile", { name, contact }),
    createHostel: (input: HostelInput) => postForm<Hostel>("/api/owners/hostels", { ...input }),
    updateHostel: (id: string, input: HostelInput) =>
      putForm<Hostel>(`/api/owners/hostels/${id}`, { ...input }),
    listHostels: () => getJson<{ hostels: OwnerHostel[] }>("/api/owners/hostels"),
    createRoom: (
      hostelId: string,
      data: { type: string; capacity: number; price: number; images: File[] },
    ) => {
      const form = new FormData();
      form.append("type", data.type);
      form.append("capacity", String(data.capacity));
      form.append("price", String(data.price));
      for (const img of data.images) form.append("images", img);
      return postMultipart<Room>(`/api/hostels/${hostelId}/rooms`, form);
    },
  },

  ownerBookings: {
    queue: () => getJson<{ queue: ReviewItem[] }>("/api/owners/bookings"),
    approve: (id: string) =>
      postJson<{ result: string; confirmed?: number; room_full?: boolean }>(
        `/api/bookings/${id}/approve`,
        {},
      ),
    reject: (id: string) =>
      postJson<{ result: string; rejected: number }>(`/api/bookings/${id}/reject`, {}),
  },

  // Gated room image URL (the backend streams or 302-redirects per index).
  roomImageUrl: (roomId: string, index: number) => `/api/assets/rooms/${roomId}/${index}`,
};
