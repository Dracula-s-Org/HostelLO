import { HostelCard } from "../../components/HostelCard";
import { EmptyState, ErrorNote, Spinner } from "../../components/primitives";
import { api } from "../../lib/api";
import { useAsync } from "../../lib/useAsync";

// GET /api/residents/recommendations — ranked, hard-filtered hostels.
export function Recommendations() {
  const { data, loading, error } = useAsync(() => api.residents.recommendations(), []);

  return (
    <div className="space-y-stack-md">
      <div>
        <h1 className="text-headline-lg-mobile md:text-headline-lg text-primary">Hostels for you</h1>
        <p className="text-body-md text-on-surface-variant max-w-2xl">
          Ranked by price, location, and amenity fit against your profile.
        </p>
      </div>

      {loading && (
        <div className="flex justify-center py-stack-lg text-on-surface-variant">
          <Spinner className="text-3xl" />
        </div>
      )}
      {error && <ErrorNote message={error} />}
      {data && data.results.length === 0 && (
        <EmptyState icon="search_off" title="No hostels match yet." hint="Try widening your budget or location." />
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-gutter">
        {data?.results.map((rec) => (
          <HostelCard key={rec.hostel.id} hostel={rec.hostel} rooms={rec.rooms} score={rec.score} />
        ))}
      </div>
    </div>
  );
}
