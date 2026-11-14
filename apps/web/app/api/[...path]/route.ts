import { createHash, timingSafeEqual } from "node:crypto";

// Same-origin proxy to the Flame API. The browser never sees a bearer token: each is attached
// here, on the server. Everything is read-only except `POST chat` (read token) and
// `POST analyses` (passcode-gated upload, see uploadAnalysis below).
const ALLOWED = /^(health|dashboard\/counts|search|(documents|experiments|evidence|analyses)(\/[A-Za-z0-9_-]+(\/artifacts\/(original|preprocessed|mask|overlay))?)?|investigations(\/FF-[A-Z0-9-]{2,41})?|insights(\/(flex-outcome|suppression-advice))?|graph\/entities(\/[0-9A-HJKMNP-TV-Z]{26})?|scenarios\/[a-z0-9_]{3,40}\/history)$/;

export const dynamic = "force-dynamic";

// Two POSTs only. `chat` asks a question and changes nothing, so it uses the read token; the AURA
// model can take a while, hence the longer timeout than the GETs below. `analyses` uploads an
// image or video for CV analysis and is handled by uploadAnalysis.
export async function POST(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  const joined = path.join("/");
  if (joined === "analyses") return uploadAnalysis(request);
  if (joined !== "chat") {
    return Response.json({ error: { code: "NOT_FOUND" } }, { status: 404 });
  }
  const origin = process.env.FLAME_API_ORIGIN;
  if (!origin) {
    return Response.json({ error: { code: "API_NOT_CONFIGURED" } }, { status: 503 });
  }
  const body = await request.text();
  if (body.length > 4096) {
    return Response.json({ error: { code: "VALIDATION_ERROR", message: "Request is too large." } }, { status: 400 });
  }

  const headers: Record<string, string> = { Accept: "application/json", "Content-Type": "application/json" };
  const token = process.env.FLAME_READ_API_TOKEN;
  if (token) headers.Authorization = `Bearer ${token}`;

  try {
    const upstream = await fetch(`${origin}/api/chat`, {
      method: "POST",
      headers,
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(130_000),
    });
    const out = new Headers();
    for (const name of ["content-type", "retry-after"]) {
      const value = upstream.headers.get(name);
      if (value) out.set(name, value);
    }
    return new Response(upstream.body, { status: upstream.status, headers: out });
  } catch {
    return Response.json(
      { error: { code: "UPSTREAM_UNAVAILABLE", message: "The Flame API could not be reached.", retryable: true } },
      { status: 502 },
    );
  }
}

export async function GET(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  const joined = path.join("/");
  const origin = process.env.FLAME_API_ORIGIN;
  if (!ALLOWED.test(joined)) {
    return Response.json({ error: { code: "NOT_FOUND" } }, { status: 404 });
  }
  if (!origin) {
    return Response.json({ error: { code: "API_NOT_CONFIGURED" } }, { status: 503 });
  }

  const headers: Record<string, string> = { Accept: "application/json, image/*" };
  const token = process.env.FLAME_READ_API_TOKEN;
  if (token) headers.Authorization = `Bearer ${token}`;

  try {
    const upstream = await fetch(`${origin}/api/${joined}${new URL(request.url).search}`, {
      headers,
      cache: "no-store",
      signal: AbortSignal.timeout(20_000),
    });
    const out = new Headers();
    for (const name of ["content-type", "cache-control", "retry-after"]) {
      const value = upstream.headers.get(name);
      if (value) out.set(name, value);
    }
    return new Response(upstream.body, { status: upstream.status, headers: out });
  } catch {
    return Response.json({ error: { code: "UPSTREAM_UNAVAILABLE" } }, { status: 502 });
  }
}

// --- Uploads -------------------------------------------------------------------------------------
// The dashboard has no login, so uploading needs a shared passcode (FLAME_WEB_UPLOAD_PASSCODE) sent
// in the X-Flame-Upload-Passcode header. The upload is then forwarded with FLAME_WEB_UPLOAD_KEY: an
// `api_client` key with only the `write` scope (python -m flame_api.clients create flame-web-uploads
// --scopes write), never the deprecated FLAME_WRITE_API_TOKEN, which is also an admin credential.
// Only POST /api/analyses is reachable with it; the API still validates type, size and pixels, and
// rate-limits writes per key. With either variable unset, uploads are off (503 UPLOADS_DISABLED).

// The API's own caps are 10 MB per image and 200 MB per video; this only refuses bodies that cannot
// pass them before streaming them on (multipart framing adds a little, hence the margin).
const MAX_UPLOAD_BODY_BYTES = 201 * 1024 * 1024;

// Wrong passcodes per client address, so the passcode cannot be guessed at line speed. Per process
// (one flame-web replica); a restart clears it, which is acceptable for a shared passcode.
const FAILED_WINDOW_MS = 10 * 60 * 1000;
const MAX_FAILED_PER_WINDOW = 10;
const failedAttempts = new Map<string, { count: number; since: number }>();

function clientAddress(request: Request): string {
  // Only values the edge proxy writes: X-Real-IP (set by Railway's edge), else the LAST
  // X-Forwarded-For entry (the one the proxy appended). The first X-Forwarded-For entry is whatever
  // the client sent, so keying on it would let a guesser rotate addresses past the lockout.
  // No global cap on purpose: anyone could trip it to block every uploader, and the passcode is
  // meant to be high-entropy (16+ random characters) so the per-address cap is rate-limiting only.
  const real = request.headers.get("x-real-ip")?.trim();
  if (real) return real;
  const forwarded = request.headers.get("x-forwarded-for")?.split(",") ?? [];
  return forwarded[forwarded.length - 1]?.trim() || "unknown";
}

function lockedOut(address: string, now: number): boolean {
  const entry = failedAttempts.get(address);
  if (!entry || now - entry.since > FAILED_WINDOW_MS) return false;
  return entry.count >= MAX_FAILED_PER_WINDOW;
}

function recordFailure(address: string, now: number): void {
  const entry = failedAttempts.get(address);
  if (!entry || now - entry.since > FAILED_WINDOW_MS) {
    failedAttempts.set(address, { count: 1, since: now });
  } else {
    entry.count += 1;
  }
  if (failedAttempts.size > 10_000) {
    for (const [key, value] of failedAttempts) {
      if (now - value.since > FAILED_WINDOW_MS) failedAttempts.delete(key);
    }
  }
}

function passcodeMatches(given: string, expected: string): boolean {
  // Compare fixed-length digests so neither the length nor the content leaks through timing.
  const a = createHash("sha256").update(given).digest();
  const b = createHash("sha256").update(expected).digest();
  return timingSafeEqual(a, b);
}

function uploadError(status: number, code: string, message: string, extra: Record<string, string> = {}) {
  return Response.json({ error: { code, message, retryable: status === 429 || status >= 500 } }, { status, headers: extra });
}

async function uploadAnalysis(request: Request): Promise<Response> {
  const origin = process.env.FLAME_API_ORIGIN;
  const key = process.env.FLAME_WEB_UPLOAD_KEY;
  const passcode = process.env.FLAME_WEB_UPLOAD_PASSCODE;
  if (!origin) return uploadError(503, "API_NOT_CONFIGURED", "The Flame API is not configured.");
  if (!key || !passcode) return uploadError(503, "UPLOADS_DISABLED", "Uploads are not enabled on this dashboard.");

  const now = Date.now();
  const address = clientAddress(request);
  if (lockedOut(address, now)) {
    return uploadError(429, "TOO_MANY_ATTEMPTS", "Too many wrong passcodes. Try again in 10 minutes.", { "Retry-After": "600" });
  }
  if (!passcodeMatches(request.headers.get("x-flame-upload-passcode") ?? "", passcode)) {
    recordFailure(address, now);
    return uploadError(401, "UPLOAD_PASSCODE_INVALID", "The upload passcode is not correct.");
  }

  const contentType = request.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().startsWith("multipart/form-data")) {
    return uploadError(415, "UNSUPPORTED_MEDIA_TYPE", "Send the file as multipart/form-data.");
  }
  const length = Number(request.headers.get("content-length"));
  if (!Number.isFinite(length) || length <= 0) {
    return uploadError(411, "LENGTH_REQUIRED", "The upload must declare its size.");
  }
  if (length > MAX_UPLOAD_BODY_BYTES) {
    return uploadError(413, "PAYLOAD_TOO_LARGE", "The file is larger than the upload limit (10 MB image, 200 MB video).");
  }
  if (!request.body) return uploadError(400, "VALIDATION_ERROR", "The upload is empty.");

  const headers: Record<string, string> = {
    Accept: "application/json",
    Authorization: `Bearer ${key}`,
    "Content-Type": contentType,
    "Content-Length": String(length),
  };
  const idempotency = request.headers.get("idempotency-key");
  if (idempotency && /^[A-Za-z0-9_-]{8,128}$/.test(idempotency)) headers["Idempotency-Key"] = idempotency;

  try {
    // Streamed, not buffered: a 200 MB video never sits in this process's memory.
    const upstream = await fetch(`${origin}/api/analyses`, {
      method: "POST",
      headers,
      body: request.body,
      duplex: "half",
      cache: "no-store",
      signal: AbortSignal.timeout(300_000),
    } as RequestInit & { duplex: "half" });
    const out = new Headers();
    for (const name of ["content-type", "location", "retry-after"]) {
      const value = upstream.headers.get(name);
      if (value) out.set(name, value);
    }
    return new Response(upstream.body, { status: upstream.status, headers: out });
  } catch {
    return uploadError(502, "UPSTREAM_UNAVAILABLE", "The Flame API could not be reached.");
  }
}
