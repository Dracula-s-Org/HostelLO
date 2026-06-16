// Pendo analytics — integrated the CSP-safe way.
//
// This loader ships *inside* the app bundle (served from 'self'), so it complies
// with our strict `script-src 'self'` CSP. The Pendo agent it injects loads from
// cdn.pendo.io, which is allowlisted in app/main.py. The visitor is anonymous
// (no phone/PII) to preserve the DPDP posture; role is attached as a
// non-identifying segmentation tag once known.

const PENDO_API_KEY = "958db75f-e9f8-4b4f-a20d-df6650c01d27";

declare global {
  interface Window {
    pendo?: any;
  }
}

let started = false;

/** Inject + initialize the Pendo agent once, at app entry. */
export function initPendo(): void {
  if (started) return;
  started = true;

  // Standard Pendo loader stub: queues calls until the agent script resolves.
  const w = window as unknown as { pendo: any };
  const o = (w.pendo = w.pendo || {});
  o._q = o._q || [];
  const verbs = ["initialize", "identify", "updateOptions", "pageLoad", "track", "trackAgent"];
  for (const m of verbs) {
    o[m] =
      o[m] ||
      function (...args: unknown[]) {
        const entry = [m, ...args];
        if (m === verbs[0]) o._q.unshift(entry);
        else o._q.push(entry);
      };
  }

  const script = document.createElement("script");
  script.async = true;
  script.src = `https://cdn.pendo.io/agent/static/${PENDO_API_KEY}/pendo.js`;
  const first = document.getElementsByTagName("script")[0];
  first.parentNode?.insertBefore(script, first);

  o.initialize({ visitor: { id: "" } });
}

/** Fire a custom Pendo track event. Never throws into app flow. */
export function pendoTrack(event: string, props?: Record<string, unknown>): void {
  try {
    const p = (window as unknown as { pendo?: any }).pendo;
    if (p && typeof p.track === "function") p.track(event, props);
  } catch {
    /* analytics must never break the app */
  }
}

/** Tag the (anonymous) visitor with a non-identifying role for segmentation. */
export function setPendoRole(role: string | null): void {
  if (!role) return;
  try {
    const p = (window as unknown as { pendo?: any }).pendo;
    if (p && typeof p.updateOptions === "function") p.updateOptions({ visitor: { role } });
  } catch {
    /* ignore */
  }
}
