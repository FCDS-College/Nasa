import { NextRequest, NextResponse } from "next/server";

const BACKEND_BASE =
  process.env.API_BACKEND_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://127.0.0.1:8000";

const SERVER_API_TOKEN =
  process.env.API_READ_TOKEN ||
  process.env.API_BEARER_TOKEN ||
  "";

async function proxyRequest(request: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const resolvedParams = await params;
  const pathSegments = resolvedParams.path || [];
  const targetPath = `/api/${pathSegments.join("/")}`;
  const targetUrl = new URL(targetPath, BACKEND_BASE);

  // Forward query parameters
  request.nextUrl.searchParams.forEach((value, key) => {
    targetUrl.searchParams.append(key, value);
  });

  const requestId =
    request.headers.get("x-request-id") ||
    `req_proxy_${Date.now()}_${Math.random().toString(36).substring(2, 8)}`;

  // Forward request headers
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    const lower = key.toLowerCase();
    if (!["host", "connection", "content-length"].includes(lower)) {
      headers.set(key, value);
    }
  });

  // Inject server-side bearer token if configured and not already provided
  if (SERVER_API_TOKEN && !headers.has("authorization")) {
    headers.set("authorization", `Bearer ${SERVER_API_TOKEN}`);
  }

  headers.set("x-request-id", requestId);

  try {
    const method = request.method;
    let body: BodyInit | undefined = undefined;

    if (method !== "GET" && method !== "HEAD") {
      const contentType = request.headers.get("content-type") || "";
      if (contentType.includes("multipart/form-data")) {
        body = await request.arrayBuffer();
      } else {
        body = await request.text();
      }
    }

    const response = await fetch(targetUrl.toString(), {
      method,
      headers,
      body,
      redirect: "manual",
      cache: "no-store",
    });

    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      const lower = key.toLowerCase();
      if (!["transfer-encoding", "content-encoding"].includes(lower)) {
        responseHeaders.set(key, value);
      }
    });

    const responseBody = await response.arrayBuffer();
    return new NextResponse(responseBody, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch {
    // Graceful proxy failure conforming to docs/api/FRONTEND_API_CONTRACT.md §2.1
    return NextResponse.json(
      {
        error: {
          code: "DATABASE_UNAVAILABLE",
          message: "API backend service is currently unreachable.",
          request_id: requestId,
          retryable: true,
          details: {
            target: targetUrl.pathname,
          },
        },
      },
      {
        status: 503,
        headers: {
          "x-request-id": requestId,
          "retry-after": "5",
        },
      }
    );
  }
}

export const GET = proxyRequest;
export const POST = proxyRequest;
export const PUT = proxyRequest;
export const PATCH = proxyRequest;
export const DELETE = proxyRequest;
