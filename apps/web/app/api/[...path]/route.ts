// Same-origin, read-only proxy to the Flame API. The browser never sees the
// bearer token: it is attached here, on the server.
const ALLOWED = /^(health|dashboard\/counts|search|(documents|experiments|evidence|analyses)(\/[A-Za-z0-9_-]+(\/artifacts\/(original|preprocessed|mask|overlay))?)?)$/;

export const dynamic = "force-dynamic";

// The only write-shaped call the dashboard may make: it asks a question, it changes nothing.
// It uses the read token, so this service never holds the write token. The AURA model can take
// a while, hence the longer timeout than the GETs below.
export async function POST(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  if (path.join("/") !== "chat") {
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
