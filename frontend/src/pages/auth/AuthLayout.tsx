import type { ReactNode } from "react";
import { Link } from "react-router-dom";

// Centered single-column shell for the welcome / OTP / KYC screens.
export function AuthLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-surface flex flex-col">
      <header className="px-margin-mobile md:px-margin-desktop py-5">
        <Link to="/" className="font-heading text-headline-md text-primary font-extrabold tracking-tight">
          HostelLo
        </Link>
      </header>
      <main className="flex-1 flex items-center justify-center px-margin-mobile pb-16">
        <div className="w-full max-w-md">
          <div className="mb-stack-md">
            <h1 className="text-headline-lg-mobile text-primary">{title}</h1>
            {subtitle && <p className="text-body-md text-on-surface-variant mt-2">{subtitle}</p>}
          </div>
          {children}
        </div>
      </main>
    </div>
  );
}
