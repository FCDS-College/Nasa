// Same-origin, read-only proxy to the Flame API. The browser never sees the
// bearer token: it is attached here, on the server.
const ALLOWED = /^(health|dashboard\/counts|search|(documents|experiments|evidence|analyses)(\/[A-Za-z0-9_-]+(\/artifacts\/(original|preprocessed|mask|overlay))?)?)$/;

export const dynamic = "force-dynamic";

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
