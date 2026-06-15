import { EmptyState } from "../components/primitives";

// Temporary stand-in for screens not yet converted. Replaced as each vertical
// phase lands.
export function Placeholder({ title }: { title: string }) {
  return (
    <div>
      <h1 className="text-headline-lg-mobile md:text-headline-lg text-primary mb-stack-md">{title}</h1>
      <EmptyState icon="construction" title="This screen is coming next." hint="Wiring it to the API." />
    </div>
  );
}
