// Domain types mirroring the FastAPI backend (app/models.py + app/serializers.py).
// Enums are string-union types matching the values the API sends/accepts.

export type Role = "OWNER" | "RESIDENT";
export type KycStatus = "NONE" | "PENDING" | "VERIFIED" | "REJECTED";
export type Gender = "MALE" | "FEMALE";
export type SleepSchedule = "EARLY" | "NIGHT";
export type Diet = "VEG" | "NONVEG" | "EGGETARIAN";
export type SocialType = "INTROVERT" | "EXTROVERT";
export type GenderPolicy = "MALE" | "FEMALE" | "COED";
export type ListingTier = "FREE" | "PREMIUM";
export type RoomType = "SINGLE" | "SHARED";
export type RoomStatus = "AVAILABLE" | "FULL";
export type BookingStatus = "REQUESTED" | "CONFIRMED" | "REJECTED" | "CANCELLED";
export type MatchStatus = "PROPOSED" | "CONFIRMED" | "REJECTED";

// GET /api/residents/me — to_resident_self_view
export interface ResidentProfile {
  user_id: string;
  name: string;
  age: number;
  gender: Gender;
  budget_min: number;
  budget_max: number;
  preferred_location: string;
  smoking: boolean;
  drinking: boolean;
  sleep_schedule: SleepSchedule;
  cleanliness: number; // 1..5
  diet: Diet;
  social_type: SocialType;
  gaming_freq: number; // 1..4
  study_habits: number; // 1..4
  fitness_freq: number; // 1..4
  visitors_freq: number; // 1..4
  seeking_shared: boolean;
  amenity_preferences: string[];
  has_prebooked_roommate: boolean;
  prebooked_roommate_phone_masked: string;
}

// GET /api/owners/me — to_owner_self_view
export interface OwnerProfile {
  user_id: string;
  name: string;
  contact: string;
}

// to_hostel_view
export interface Hostel {
  id: string;
  name: string;
  address: string;
  location: string;
  gender_policy: GenderPolicy;
  listing_tier: ListingTier;
  verified: boolean;
  amenities: string[];
  veg_only: boolean;
  allow_smoking: boolean;
  allow_drinking: boolean;
  min_age: number | null;
  max_age: number | null;
}

// to_room_view
export interface Room {
  id: string;
  type: RoomType;
  capacity: number;
  occupied_count: number;
  price: number;
  status: RoomStatus;
  image_count: number;
}

// GET /api/residents/recommendations -> { results: Recommendation[] }
export interface Recommendation {
  hostel: Hostel;
  rooms: Room[];
  score: number;
  price_fit: number;
  location_fit: number;
  amenity_fit: number;
}

// GET /api/bookings/mine -> { bookings: BookingSummary[] }
export interface BookingSummary {
  id: string;
  status: BookingStatus;
  created_at: string;
  room: { id: string; type: RoomType; price: number };
  hostel: { id: string; name: string; location: string };
  roommate_match_id: string | null;
}

// GET /api/bookings/{id} -> single booking + facility detail. `owner` (name +
// contact) is populated ONLY for CONFIRMED bookings; null otherwise.
export interface BookingDetail {
  id: string;
  status: BookingStatus;
  created_at: string;
  room: { id: string; type: RoomType; price: number };
  hostel: { id: string; name: string; location: string; address: string };
  roommate_match_id: string | null;
  owner: { name: string; contact: string } | null;
}

// POST /api/bookings -> booking placement result
export interface BookingPlacement {
  id: string;
  status: BookingStatus;
  room_id: string;
  roommate_match_id: string | null;
  is_shared: boolean;
  prebooked_match: boolean;
}

// to_candidate_view (roommate-recommendations)
export interface Candidate {
  candidate_id: string;
  first_name: string;
  overall_score: number;
  breakdown: Record<string, number>;
  habits: {
    sleep_schedule: SleepSchedule;
    cleanliness: number;
    social_type: SocialType;
  };
}

// GET /api/roommate-matches/pending -> { pending: PendingMatch[] }
export interface PendingMatch {
  match_id: string;
  score: number;
  breakdown: Record<string, number>;
  from: { first_name: string };
}

// POST /api/roommate-matches/{id}/accept -> confirmed roommate (to_match_confirmed_view)
export interface ConfirmedRoommate {
  resident_id: string;
  full_name: string;
  phone: string;
  kyc_status: KycStatus;
}

// to_owner_applicant_view (owner review queue, pre-approval gated)
export interface OwnerApplicant {
  resident_id: string;
  first_name: string;
  age: number;
  habits: {
    smoking: boolean;
    drinking: boolean;
    diet: Diet;
    sleep_schedule: SleepSchedule;
    cleanliness: number;
    social_type: SocialType;
    gaming_freq: number;
    study_habits: number;
    fitness_freq: number;
    visitors_freq: number;
  };
}

// GET /api/owners/bookings -> { queue: ReviewItem[] }
export interface ReviewItem {
  booking: { id: string; status: BookingStatus; created_at: string };
  room: Room;
  hostel: { id: string; name: string };
  applicant: OwnerApplicant | null;
  match: { score: number; breakdown: Record<string, number> } | null;
}

// GET /api/owners/hostels -> { hostels: OwnerHostel[] }
export interface OwnerHostel {
  hostel: Hostel;
  rooms: Room[];
  pending_count: number;
}

// GET /api/kyc/status
export interface KycStatusResponse {
  kyc_status: KycStatus;
  latest_submission: { id: string; doc_type: string; status: KycStatus } | null;
}
