import { Link, useNavigate } from "react-router-dom";
import { Icon, type IconName } from "../components/Icon";

interface Feature {
  icon: IconName;
  tone: string;
  title: string;
  body: string;
  tags: string[];
}

// Public marketing landing page (converted from the Stitch "Modern Student
// Living" prototype). No backend calls. CTAs route into the role-pick / OTP flow.
export function LandingPage() {
  const navigate = useNavigate();
  const go = (role: "RESIDENT" | "OWNER") => navigate(`/welcome?role=${role}`);

  return (
    <div className="antialiased">
      <nav className="fixed top-0 left-0 w-full z-50 flex justify-between items-center px-5 md:px-16 py-4 bg-surface-container-lowest shadow-sm">
        <div className="flex items-center gap-8">
          <span className="font-heading text-headline-md text-primary font-extrabold tracking-tight">HostelLo</span>
          <div className="hidden md:flex gap-6">
            <a className="text-primary font-bold border-b-2 border-primary text-label-md" href="#top">Home</a>
            <a className="text-on-surface-variant hover:text-primary transition-colors text-label-md" href="#engine">How it works</a>
          </div>
        </div>
        <Link to="/welcome" className="text-label-md text-primary hover:underline">Sign in</Link>
      </nav>

      <main className="pt-24" id="top">
        {/* Hero */}
        <section className="max-w-container-max mx-auto px-5 md:px-margin-desktop py-12 md:py-24 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="space-y-8">
            <div className="space-y-4">
              <span className="inline-block px-4 py-1.5 rounded-full bg-primary-fixed text-primary text-label-md">
                Modern India's Choice
              </span>
              <h1 className="font-heading text-[40px] md:text-display-lg text-primary leading-tight">
                Your home away from home, <span className="text-secondary-container">simplified.</span>
              </h1>
              <p className="text-body-lg text-on-surface-variant max-w-lg">
                Find hostels that fit your lifestyle. Whether you're a night owl or an early bird, our
                match-engine helps you find the right roommates and space.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-4">
              <button
                onClick={() => go("RESIDENT")}
                className="bg-secondary-container text-white px-8 py-4 rounded-xl text-label-md flex items-center justify-center gap-2 shadow-[0_2px_0_0_#ac3509] hover:scale-105 transition-transform"
              >
                I'm a student
                <Icon name="arrow_forward" />
              </button>
              <button
                onClick={() => go("OWNER")}
                className="border-2 border-primary text-primary px-8 py-4 rounded-xl text-label-md hover:bg-primary/5 transition-colors"
              >
                I'm a hostel owner
              </button>
            </div>
            <div className="flex items-center gap-4 pt-4">
              <div className="flex -space-x-3">
                {["AK", "RS", "SM"].map((initials, i) => (
                  <div
                    key={initials}
                    className={`w-10 h-10 rounded-full border-2 border-white flex items-center justify-center text-white text-label-sm ${
                      ["bg-primary-container", "bg-tertiary-container", "bg-secondary-container"][i]
                    }`}
                  >
                    {initials}
                  </div>
                ))}
              </div>
              <p className="text-label-sm text-on-surface-variant">
                <span className="font-bold text-primary">5,000+</span> students verified this month
              </p>
            </div>
          </div>

          <div className="relative group">
            <div className="absolute -inset-4 bg-primary-fixed/20 rounded-[40px] blur-2xl" />
            <div className="relative bg-surface-container-lowest p-6 rounded-[32px] shadow-card overflow-hidden">
              <div className="w-full aspect-[4/3] rounded-2xl bg-gradient-to-br from-primary-fixed via-surface-container to-tertiary-fixed flex items-center justify-center">
                <Icon name="diversity_3" className="text-6xl text-primary/40" />
              </div>
              <div className="absolute bottom-10 right-10 p-4 bg-white/80 backdrop-blur rounded-2xl shadow-card border border-white/50">
                <div className="flex items-center gap-3 mb-2">
                  <Icon name="favorite" className="text-secondary-container" filled />
                  <span className="text-label-md text-primary">98% match found</span>
                </div>
                <div className="h-1.5 w-32 bg-outline-variant rounded-full overflow-hidden">
                  <div className="h-full bg-secondary-container w-[98%]" />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Habits-Match Engine */}
        <section id="engine" className="bg-surface-container-low py-24">
          <div className="max-w-container-max mx-auto px-5 md:px-margin-desktop">
            <div className="text-center max-w-2xl mx-auto mb-16 space-y-4">
              <h2 className="text-headline-lg text-primary">The Habits-Match Engine</h2>
              <p className="text-body-md text-on-surface-variant">
                Relocation shouldn't be a gamble. We analyze your daily rhythm to find your living ecosystem.
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              {([
                {
                  icon: "schedule",
                  tone: "bg-primary-fixed text-primary",
                  title: "Sync your rhythm",
                  body: "Night owl or early bird? We match you with roommates who share your sleep-wake cycle.",
                  tags: ["Early bird", "Quiet study"],
                },
                {
                  icon: "restaurant",
                  tone: "bg-secondary-fixed text-secondary",
                  title: "Lifestyle pillars",
                  body: "From diet to gym timings, the engine weighs what actually matters in shared living.",
                  tags: ["Vegetarian", "Fitness"],
                },
                {
                  icon: "verified_user",
                  tone: "bg-tertiary-fixed text-tertiary-container",
                  title: "Verified trust",
                  body: "Every profile goes through KYC. Safety is the foundation of every match we suggest.",
                  tags: ["KYC verified"],
                },
              ] satisfies Feature[]).map((f) => (
                <div
                  key={f.title}
                  className="bg-surface-container-lowest p-8 rounded-[32px] shadow-card hover:shadow-card-hover transition-all flex flex-col items-start gap-6"
                >
                  <div className={`w-14 h-14 flex items-center justify-center rounded-2xl ${f.tone}`}>
                    <Icon name={f.icon} className="text-3xl" />
                  </div>
                  <div>
                    <h3 className="text-headline-md text-primary mb-3">{f.title}</h3>
                    <p className="text-body-md text-on-surface-variant mb-6">{f.body}</p>
                    <div className="flex flex-wrap gap-2">
                      {f.tags.map((t) => (
                        <span key={t} className="px-3 py-1 bg-surface-container-high rounded-full text-label-sm text-primary">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="py-24 px-5 md:px-margin-desktop">
          <div className="max-w-container-max mx-auto bg-primary rounded-[40px] p-12 md:p-20 relative overflow-hidden">
            <div className="relative z-10 grid md:grid-cols-2 gap-12 items-center">
              <div className="space-y-6">
                <h2 className="font-heading text-[32px] md:text-[48px] text-white leading-tight">
                  Start your journey with <span className="text-secondary-fixed">HostelLo</span> today.
                </h2>
                <p className="text-body-lg text-primary-fixed-dim">
                  Looking for a bed or looking to fill your hostel — we've got you covered.
                </p>
                <div className="flex flex-col sm:flex-row gap-4 pt-4">
                  <button
                    onClick={() => navigate("/welcome")}
                    className="bg-secondary-container text-white px-8 py-4 rounded-xl text-label-md shadow-[0_2px_0_0_#ac3509] hover:scale-105 transition-transform"
                  >
                    Get started
                  </button>
                </div>
              </div>
              <div className="hidden md:block">
                <div className="bg-white/10 backdrop-blur-xl border border-white/20 p-8 rounded-3xl space-y-6">
                  <div className="flex items-center justify-between">
                    <span className="text-label-md text-white">Trust factor</span>
                    <span className="text-primary-fixed font-bold">Excellent</span>
                  </div>
                  <div className="space-y-3">
                    {[94, 88, 96].map((w, i) => (
                      <div key={i} className="h-2 bg-white/10 rounded-full w-full">
                        <div
                          className={`h-full rounded-full ${["bg-secondary-fixed", "bg-tertiary-fixed", "bg-on-primary-container"][i]}`}
                          style={{ width: `${w}%` }}
                        />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
            <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-secondary-container/20 rounded-full blur-[100px]" />
            <div className="absolute -top-24 -left-24 w-96 h-96 bg-tertiary-container/20 rounded-full blur-[100px]" />
          </div>
        </section>

        <footer className="bg-surface-container-lowest py-16 px-5 md:px-margin-desktop border-t border-outline-variant">
          <div className="max-w-container-max mx-auto flex flex-col md:flex-row justify-between gap-8">
            <div className="space-y-3 max-w-sm">
              <span className="font-heading text-headline-md text-primary font-extrabold tracking-tight">HostelLo</span>
              <p className="text-body-md text-on-surface-variant">
                Defining modern student living in India. Professional, safe, community-driven.
              </p>
            </div>
            <p className="text-label-sm text-on-surface-variant self-end">© {2026} HostelLo</p>
          </div>
        </footer>
      </main>
    </div>
  );
}
