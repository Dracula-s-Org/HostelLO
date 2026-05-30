/**
 * HostelLO - Pendo Track Events
 *
 * Centralized tracking module for all Pendo track events.
 * Each function wraps a pendo.track() call for a specific user action.
 * Import and call these from the appropriate handlers once the application
 * UI and logic are implemented.
 *
 * Usage:
 *   import { trackUserRegistrationCompleted } from './src/tracking/pendoTrackEvents.js';
 *   trackUserRegistrationCompleted({ user_type: 'student', registration_method: 'email' });
 */

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function safePendoTrack(eventName, properties) {
  try {
    if (typeof pendo !== "undefined" && typeof pendo.track === "function") {
      pendo.track(eventName, properties);
    }
  } catch (e) {
    // Never let tracking break application flow
    console.error("[PendoTrack] Failed to track event:", eventName, e);
  }
}

// ---------------------------------------------------------------------------
// 1. User Registration & Onboarding
// ---------------------------------------------------------------------------

/**
 * Fires when a new user successfully completes registration.
 * Call from the registration form submission success handler.
 *
 * @param {Object} props
 * @param {string} props.user_type          - "student" | "property_owner"
 * @param {string} props.registration_method - "email" | "google" | "facebook" etc.
 * @param {string} [props.referral_source]   - Where the user came from
 */
export function trackUserRegistrationCompleted({
  user_type,
  registration_method,
  referral_source,
}) {
  safePendoTrack("user_registration_completed", {
    user_type,
    registration_method,
    referral_source: referral_source || "direct",
  });
}

/**
 * Fires when a user completes their profile setup.
 * Call from the profile setup form submission success callback.
 *
 * @param {Object} props
 * @param {string}  props.user_type                    - "student" | "property_owner"
 * @param {number}  props.profile_completion_percentage - 0-100
 * @param {number}  [props.habits_filled_count]         - Number of habit fields filled
 * @param {number}  props.fields_completed              - Total fields completed
 */
export function trackProfileCompleted({
  user_type,
  profile_completion_percentage,
  habits_filled_count,
  fields_completed,
}) {
  safePendoTrack("profile_completed", {
    user_type,
    profile_completion_percentage,
    habits_filled_count: habits_filled_count || 0,
    fields_completed,
  });
}

/**
 * Fires when a student submits or updates their habits/lifestyle preferences.
 * Call from the habits preferences form submission success handler.
 *
 * @param {Object} props
 * @param {number} props.habits_count      - Total habits submitted
 * @param {string} props.sleep_schedule    - e.g. "early_bird" | "night_owl"
 * @param {string} props.noise_preference  - e.g. "quiet" | "moderate" | "loud"
 * @param {string} props.cleanliness_level - e.g. "very_clean" | "moderate" | "relaxed"
 * @param {string} props.study_habits      - e.g. "in_room" | "library" | "mixed"
 */
export function trackHabitsProfileSubmitted({
  habits_count,
  sleep_schedule,
  noise_preference,
  cleanliness_level,
  study_habits,
}) {
  safePendoTrack("habits_profile_submitted", {
    habits_count,
    sleep_schedule,
    noise_preference,
    cleanliness_level,
    study_habits,
  });
}

/**
 * Fires when a user completes the full onboarding workflow.
 * Call at the final step of the onboarding workflow completion.
 *
 * @param {Object} props
 * @param {string} props.user_type              - "student" | "property_owner"
 * @param {number} props.steps_completed        - Number of steps completed
 * @param {number} props.total_duration_minutes - Total time spent in onboarding
 * @param {number} [props.skipped_steps]        - Number of steps skipped
 */
export function trackOnboardingCompleted({
  user_type,
  steps_completed,
  total_duration_minutes,
  skipped_steps,
}) {
  safePendoTrack("onboarding_completed", {
    user_type,
    steps_completed,
    total_duration_minutes,
    skipped_steps: skipped_steps || 0,
  });
}

/**
 * Fires when a user successfully changes their password.
 * Call from the password change form submission success handler.
 *
 * @param {Object} props
 * @param {string} props.change_method - "settings" | "forgot_password" | "forced_reset"
 */
export function trackPasswordChanged({ change_method }) {
  safePendoTrack("password_changed", {
    change_method,
  });
}

// ---------------------------------------------------------------------------
// 2. Property Listings
// ---------------------------------------------------------------------------

/**
 * Fires when a property owner creates and publishes a new listing.
 * Call from the listing creation form submission success handler.
 *
 * @param {Object} props
 * @param {string} props.property_type        - "hostel" | "room" | "apartment"
 * @param {number} props.room_count           - Number of rooms
 * @param {string} props.price_range          - e.g. "budget" | "mid" | "premium"
 * @param {number} props.amenities_count      - Number of amenities listed
 * @param {string} props.location_city        - City of the listing
 * @param {number} props.photos_uploaded_count - Photos uploaded
 * @param {string} props.listing_id           - Created listing ID
 */
export function trackPropertyListingCreated({
  property_type,
  room_count,
  price_range,
  amenities_count,
  location_city,
  photos_uploaded_count,
  listing_id,
}) {
  safePendoTrack("property_listing_created", {
    property_type,
    room_count,
    price_range,
    amenities_count,
    location_city,
    photos_uploaded_count,
    listing_id,
  });
}

/**
 * Fires when a property owner updates an existing listing.
 * Call from the listing edit form submission success handler.
 *
 * @param {Object} props
 * @param {string}  props.listing_id           - Listing ID
 * @param {string}  props.fields_updated       - Comma-separated list of updated fields
 * @param {boolean} props.price_changed        - Whether price was modified
 * @param {boolean} props.availability_changed - Whether availability was modified
 * @param {number}  [props.photos_added]       - Number of new photos added
 */
export function trackPropertyListingUpdated({
  listing_id,
  fields_updated,
  price_changed,
  availability_changed,
  photos_added,
}) {
  safePendoTrack("property_listing_updated", {
    listing_id,
    fields_updated,
    price_changed,
    availability_changed,
    photos_added: photos_added || 0,
  });
}

/**
 * Fires when a property owner uploads photos for a listing.
 * Call from the photo upload completion callback.
 *
 * @param {Object} props
 * @param {string} props.listing_id      - Listing ID
 * @param {number} props.photo_count     - Number of photos uploaded
 * @param {number} props.total_file_size - Total size in KB
 * @param {string} props.file_types      - Comma-separated file extensions
 */
export function trackPropertyPhotosUploaded({
  listing_id,
  photo_count,
  total_file_size,
  file_types,
}) {
  safePendoTrack("property_photos_uploaded", {
    listing_id,
    photo_count,
    total_file_size,
    file_types,
  });
}

/**
 * Fires when a user shares a listing via link, email, or social media.
 * Call from the share action success handler.
 *
 * @param {Object} props
 * @param {string} props.listing_id        - Listing ID
 * @param {string} props.share_method      - "link" | "email" | "social"
 * @param {string} props.share_destination - e.g. "twitter" | "facebook" | "whatsapp" | "email"
 */
export function trackListingShared({
  listing_id,
  share_method,
  share_destination,
}) {
  safePendoTrack("listing_shared", {
    listing_id,
    share_method,
    share_destination,
  });
}

/**
 * Fires when a property owner bulk-updates multiple listings.
 * Call from the bulk action completion handler.
 *
 * @param {Object} props
 * @param {string} props.action_type    - "activate" | "deactivate" | "update_availability"
 * @param {number} props.listings_count - Total listings targeted
 * @param {number} props.success_count  - Listings successfully updated
 * @param {number} props.failure_count  - Listings that failed to update
 */
export function trackBulkListingStatusUpdate({
  action_type,
  listings_count,
  success_count,
  failure_count,
}) {
  safePendoTrack("bulk_listing_status_update", {
    action_type,
    listings_count,
    success_count,
    failure_count,
  });
}

// ---------------------------------------------------------------------------
// 3. Search & Discovery
// ---------------------------------------------------------------------------

/**
 * Fires when a student executes a search for available hostels/rooms.
 * Call from the search execution handler after results are returned.
 *
 * @param {Object} props
 * @param {string} [props.search_query]    - Text search query
 * @param {string} [props.location_filter] - Location filter applied
 * @param {number} [props.price_min]       - Minimum price filter
 * @param {number} [props.price_max]       - Maximum price filter
 * @param {string} [props.amenity_filters] - Comma-separated amenity filters
 * @param {number} props.results_count     - Number of results returned
 * @param {string} [props.sort_order]      - Sort order used
 */
export function trackSearchExecuted({
  search_query,
  location_filter,
  price_min,
  price_max,
  amenity_filters,
  results_count,
  sort_order,
}) {
  safePendoTrack("search_executed", {
    search_query: search_query || "",
    location_filter: location_filter || "",
    price_min: price_min || 0,
    price_max: price_max || 0,
    amenity_filters: amenity_filters || "",
    results_count,
    sort_order: sort_order || "default",
  });
}

/**
 * Fires when a student applies advanced filters to narrow search results.
 * Call from the filter application success handler.
 *
 * @param {Object} props
 * @param {string} props.filters_applied - Comma-separated list of filters
 * @param {number} props.filter_count    - Number of filters applied
 * @param {number} props.results_before  - Results count before filtering
 * @param {number} props.results_after   - Results count after filtering
 * @param {string} props.filter_types    - Comma-separated filter type categories
 */
export function trackSearchFiltersApplied({
  filters_applied,
  filter_count,
  results_before,
  results_after,
  filter_types,
}) {
  safePendoTrack("search_filters_applied", {
    filters_applied,
    filter_count,
    results_before,
    results_after,
    filter_types,
  });
}

/**
 * Fires when a student saves a listing to favorites.
 * Call from the save-to-favorites success callback.
 *
 * @param {Object} props
 * @param {string} props.listing_id           - Listing ID
 * @param {string} props.source_page          - Page where the action occurred
 * @param {number} [props.match_score]        - Compatibility score if available
 * @param {number} props.total_favorites_count - Total favorites after saving
 */
export function trackListingSavedToFavorites({
  listing_id,
  source_page,
  match_score,
  total_favorites_count,
}) {
  safePendoTrack("listing_saved_to_favorites", {
    listing_id,
    source_page,
    match_score: match_score || 0,
    total_favorites_count,
  });
}

// ---------------------------------------------------------------------------
// 4. Matching
// ---------------------------------------------------------------------------

/**
 * Fires when the habits-match algorithm generates compatibility results.
 * Call from the matching algorithm results callback.
 *
 * @param {Object} props
 * @param {number} props.match_count            - Total matches returned
 * @param {number} props.top_match_score        - Highest compatibility score
 * @param {number} props.average_match_score    - Average compatibility score
 * @param {number} props.matching_criteria_count - Number of criteria used
 */
export function trackMatchGenerated({
  match_count,
  top_match_score,
  average_match_score,
  matching_criteria_count,
}) {
  safePendoTrack("match_generated", {
    match_count,
    top_match_score,
    average_match_score,
    matching_criteria_count,
  });
}

/**
 * Fires when a student checks roommate compatibility with another student/room.
 * Call from the compatibility check result handler.
 *
 * @param {Object} props
 * @param {number} props.compatibility_score - Overall compatibility score
 * @param {string} props.matching_habits     - Comma-separated matching habit categories
 * @param {string} props.conflicting_habits  - Comma-separated conflicting habit categories
 * @param {string} [props.target_room_id]    - Room ID being checked
 */
export function trackRoommateCompatibilityChecked({
  compatibility_score,
  matching_habits,
  conflicting_habits,
  target_room_id,
}) {
  safePendoTrack("roommate_compatibility_checked", {
    compatibility_score,
    matching_habits,
    conflicting_habits,
    target_room_id: target_room_id || "",
  });
}

// ---------------------------------------------------------------------------
// 5. Booking
// ---------------------------------------------------------------------------

/**
 * Fires when a student submits a booking request.
 * Call from the booking request form submission success handler.
 *
 * @param {Object} props
 * @param {string} props.listing_id     - Listing ID
 * @param {string} props.room_type      - Room type booked
 * @param {string} props.check_in_date  - ISO date string
 * @param {string} props.check_out_date - ISO date string
 * @param {number} props.duration_days  - Duration of stay in days
 * @param {number} props.price_total    - Total price
 * @param {number} [props.match_score]  - Compatibility score if available
 */
export function trackBookingRequestSubmitted({
  listing_id,
  room_type,
  check_in_date,
  check_out_date,
  duration_days,
  price_total,
  match_score,
}) {
  safePendoTrack("booking_request_submitted", {
    listing_id,
    room_type,
    check_in_date,
    check_out_date,
    duration_days,
    price_total,
    match_score: match_score || 0,
  });
}

/**
 * Fires when a property owner confirms a booking request.
 * Call from the booking confirmation success handler.
 *
 * @param {Object} props
 * @param {string} props.booking_id          - Booking ID
 * @param {string} props.listing_id          - Listing ID
 * @param {number} props.response_time_hours - Time taken to respond
 * @param {number} props.price_total         - Total booking price
 * @param {number} props.duration_days       - Duration of stay
 */
export function trackBookingConfirmed({
  booking_id,
  listing_id,
  response_time_hours,
  price_total,
  duration_days,
}) {
  safePendoTrack("booking_confirmed", {
    booking_id,
    listing_id,
    response_time_hours,
    price_total,
    duration_days,
  });
}

/**
 * Fires when a booking is cancelled.
 * Call from the booking cancellation success handler.
 *
 * @param {Object} props
 * @param {string} props.booking_id          - Booking ID
 * @param {string} props.cancelled_by        - "student" | "property_owner"
 * @param {string} props.cancellation_reason - Reason for cancellation
 * @param {number} props.days_before_checkin - Days remaining before check-in
 * @param {number} [props.refund_amount]     - Refund amount if applicable
 */
export function trackBookingCancelled({
  booking_id,
  cancelled_by,
  cancellation_reason,
  days_before_checkin,
  refund_amount,
}) {
  safePendoTrack("booking_cancelled", {
    booking_id,
    cancelled_by,
    cancellation_reason,
    days_before_checkin,
    refund_amount: refund_amount || 0,
  });
}

/**
 * Fires when a property owner rejects a booking request.
 * Call from the booking rejection handler.
 *
 * @param {Object} props
 * @param {string} props.booking_id          - Booking ID
 * @param {string} props.listing_id          - Listing ID
 * @param {string} props.rejection_reason    - Reason for rejection
 * @param {number} props.response_time_hours - Time taken to respond
 */
export function trackBookingRejected({
  booking_id,
  listing_id,
  rejection_reason,
  response_time_hours,
}) {
  safePendoTrack("booking_rejected", {
    booking_id,
    listing_id,
    rejection_reason,
    response_time_hours,
  });
}

// ---------------------------------------------------------------------------
// 6. Messaging
// ---------------------------------------------------------------------------

/**
 * Fires when a user sends a message.
 * Call from the message send success handler.
 *
 * @param {Object} props
 * @param {string}  props.sender_type        - "student" | "property_owner"
 * @param {string}  props.recipient_type     - "student" | "property_owner"
 * @param {string}  props.conversation_id    - Conversation thread ID
 * @param {boolean} props.is_first_message   - Whether this is the first message in thread
 * @param {boolean} props.has_attachment     - Whether message has an attachment
 * @param {string}  [props.related_listing_id] - Listing ID if conversation is about a listing
 */
export function trackMessageSent({
  sender_type,
  recipient_type,
  conversation_id,
  is_first_message,
  has_attachment,
  related_listing_id,
}) {
  safePendoTrack("message_sent", {
    sender_type,
    recipient_type,
    conversation_id,
    is_first_message,
    has_attachment,
    related_listing_id: related_listing_id || "",
  });
}

/**
 * Fires when a new conversation thread is initiated.
 * Call from the new conversation creation success handler.
 *
 * @param {Object} props
 * @param {string} props.initiator_type    - "student" | "property_owner"
 * @param {string} props.recipient_type    - "student" | "property_owner"
 * @param {string} [props.source_listing_id] - Listing that prompted the conversation
 * @param {string} props.source_page       - Page where conversation was started
 */
export function trackConversationStarted({
  initiator_type,
  recipient_type,
  source_listing_id,
  source_page,
}) {
  safePendoTrack("conversation_started", {
    initiator_type,
    recipient_type,
    source_listing_id: source_listing_id || "",
    source_page,
  });
}

// ---------------------------------------------------------------------------
// 7. Dashboard & Reporting
// ---------------------------------------------------------------------------

/**
 * Fires when a property owner generates a dashboard report.
 * Call from the report generation completion callback.
 *
 * @param {Object} props
 * @param {string} props.report_type              - "occupancy" | "earnings" | "bookings"
 * @param {string} props.date_range               - e.g. "last_30_days" | "last_quarter"
 * @param {number} props.properties_included_count - Number of properties in report
 */
export function trackDashboardReportGenerated({
  report_type,
  date_range,
  properties_included_count,
}) {
  safePendoTrack("dashboard_report_generated", {
    report_type,
    date_range,
    properties_included_count,
  });
}

/**
 * Fires when a user exports data from their dashboard.
 * Call from the data export completion handler.
 *
 * @param {Object} props
 * @param {string} props.export_type  - Type of data exported
 * @param {string} props.file_format  - "csv" | "pdf" | "xlsx"
 * @param {number} props.record_count - Number of records exported
 * @param {string} props.date_range   - Date range of exported data
 */
export function trackDashboardDataExported({
  export_type,
  file_format,
  record_count,
  date_range,
}) {
  safePendoTrack("dashboard_data_exported", {
    export_type,
    file_format,
    record_count,
    date_range,
  });
}

// ---------------------------------------------------------------------------
// 8. Settings
// ---------------------------------------------------------------------------

/**
 * Fires when a user saves changes to their account settings.
 * Call from the settings form submission success handler.
 *
 * @param {Object} props
 * @param {string}  props.settings_section                - Section updated
 * @param {string}  props.fields_changed                  - Comma-separated changed fields
 * @param {boolean} props.notification_preferences_changed - Whether notifications changed
 * @param {boolean} props.privacy_settings_changed         - Whether privacy settings changed
 */
export function trackSettingsUpdated({
  settings_section,
  fields_changed,
  notification_preferences_changed,
  privacy_settings_changed,
}) {
  safePendoTrack("settings_updated", {
    settings_section,
    fields_changed,
    notification_preferences_changed,
    privacy_settings_changed,
  });
}
