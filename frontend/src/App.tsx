import { Navigate, Route, Routes } from "react-router-dom";
import { RequireAuth } from "./components/RequireAuth";
import { LandingPage } from "./pages/LandingPage";
import { WelcomePage } from "./pages/auth/WelcomePage";
import { OtpPage } from "./pages/auth/OtpPage";
import { KycPage } from "./pages/auth/KycPage";
import { OnboardingWizard } from "./pages/resident/OnboardingWizard";
import { ResidentHome } from "./pages/resident/ResidentHome";
import { Recommendations } from "./pages/resident/Recommendations";
import { HostelDetail } from "./pages/resident/HostelDetail";
import { RoomSelection } from "./pages/resident/RoomSelection";
import { Bookings } from "./pages/resident/Bookings";
import { BookingDetail } from "./pages/resident/BookingDetail";
import { RoommateMatching } from "./pages/resident/RoommateMatching";
import { RoommateRequests } from "./pages/resident/RoommateRequests";
import { OwnerDashboard } from "./pages/owner/OwnerDashboard";
import { CreateEditHostel } from "./pages/owner/CreateEditHostel";
import { ConfigureRooms } from "./pages/owner/ConfigureRooms";
import { ReviewQueue } from "./pages/owner/ReviewQueue";

export function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/welcome" element={<WelcomePage />} />
      <Route path="/auth/otp" element={<OtpPage />} />

      {/* KYC — shared by both roles, no shell */}
      <Route path="/kyc" element={<RequireAuth chrome={false}><KycPage /></RequireAuth>} />

      {/* Resident onboarding wizard (no shell) */}
      <Route path="/onboarding" element={<RequireAuth role="RESIDENT" chrome={false}><OnboardingWizard /></RequireAuth>} />

      {/* Resident vertical */}
      <Route path="/resident" element={<RequireAuth role="RESIDENT"><ResidentHome /></RequireAuth>} />
      <Route path="/resident/hostels" element={<RequireAuth role="RESIDENT"><Recommendations /></RequireAuth>} />
      <Route path="/resident/hostels/:id" element={<RequireAuth role="RESIDENT"><HostelDetail /></RequireAuth>} />
      <Route path="/resident/hostels/:id/rooms" element={<RequireAuth role="RESIDENT"><RoomSelection /></RequireAuth>} />
      <Route path="/resident/bookings" element={<RequireAuth role="RESIDENT"><Bookings /></RequireAuth>} />
      <Route path="/resident/bookings/:id" element={<RequireAuth role="RESIDENT"><BookingDetail /></RequireAuth>} />
      <Route path="/resident/bookings/:id/roommates" element={<RequireAuth role="RESIDENT"><RoommateMatching /></RequireAuth>} />
      <Route path="/resident/roommate-requests" element={<RequireAuth role="RESIDENT"><RoommateRequests /></RequireAuth>} />

      {/* Owner vertical */}
      <Route path="/owner" element={<RequireAuth role="OWNER"><OwnerDashboard /></RequireAuth>} />
      <Route path="/owner/hostels/new" element={<RequireAuth role="OWNER"><CreateEditHostel /></RequireAuth>} />
      <Route path="/owner/hostels/:id/edit" element={<RequireAuth role="OWNER"><CreateEditHostel /></RequireAuth>} />
      <Route path="/owner/hostels/:id/rooms" element={<RequireAuth role="OWNER"><ConfigureRooms /></RequireAuth>} />
      <Route path="/owner/bookings" element={<RequireAuth role="OWNER"><ReviewQueue /></RequireAuth>} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
