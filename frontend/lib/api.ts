const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const TUTOR_API_BASE = process.env.NEXT_PUBLIC_TUTOR_API_BASE_URL ?? "http://localhost:8001";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface User {
  email: string;
  full_name: string;
}

export interface CourseResult {
  id: number;
  title: string;
  description: string;
}

export interface SearchResponse {
  results: CourseResult[];
  degraded: boolean;
}

export interface OrgEmployee {
  email: string;
  full_name: string;
  course: string;
  lessons_completed: number;
  certificate_earned: boolean;
}

export interface OrgDashboard {
  organization: string;
  seat_usage: { total_seats: number; seats_used: number };
  employees: OrgEmployee[];
}

// Django rotates the CSRF token on login, so the cached value is invalidated
// after auth state changes and refreshed on demand.
let csrfToken: string | null = null;
let csrfInFlight: Promise<string> | null = null;

async function fetchCsrfToken(): Promise<string> {
  const res = await fetch(`${API_BASE}/api/auth/csrf/`, {
    credentials: "include",
  });
  if (!res.ok) {
    throw new ApiError(res.status, "Could not initialize CSRF protection.");
  }
  const data = (await res.json()) as { csrfToken: string };
  csrfToken = data.csrfToken;
  return data.csrfToken;
}

export function ensureCsrfToken(): Promise<string> {
  if (csrfToken) return Promise.resolve(csrfToken);
  if (!csrfInFlight) {
    csrfInFlight = fetchCsrfToken().finally(() => {
      csrfInFlight = null;
    });
  }
  return csrfInFlight;
}

function invalidateCsrfToken(): void {
  csrfToken = null;
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
}

async function request<T>(path: string, options: RequestOptions = {}, retried = false): Promise<T> {
  const { method = "GET", body, signal } = options;
  const headers: Record<string, string> = {};

  if (method !== "GET") {
    headers["X-CSRFToken"] = await ensureCsrfToken();
  }
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    credentials: "include",
    signal,
    ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
  });

  let data: unknown = null;
  try {
    data = await res.json();
  } catch {
    // Non-JSON response (e.g. Django's HTML CSRF failure page) — leave null.
  }

  if (!res.ok) {
    // A 403 with a non-JSON body on a mutating request is Django's CSRF
    // rejection (a real API 403 always returns JSON). Refresh the token once.
    if (res.status === 403 && data === null && method !== "GET" && !retried) {
      invalidateCsrfToken();
      return request<T>(path, options, true);
    }
    const message =
      data !== null && typeof data === "object" && "error" in data
        ? String((data as { error: unknown }).error)
        : `Request failed with status ${res.status}.`;
    throw new ApiError(res.status, message);
  }

  return data as T;
}

export async function login(email: string, password: string): Promise<User> {
  const user = await request<User>("/api/auth/login/", {
    method: "POST",
    body: { email, password },
  });
  invalidateCsrfToken(); // Django rotated the token on login.
  return user;
}

export async function logout(): Promise<void> {
  await request<{ success: boolean }>("/api/auth/logout/", { method: "POST" });
  invalidateCsrfToken();
}

export function me(): Promise<User> {
  return request<User>("/api/auth/me/");
}

// NOTE: no trailing slash — the backend route is `courses/search`.
export function searchCourses(query: string, signal?: AbortSignal): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query });
  return request<SearchResponse>(`/api/courses/search?${params.toString()}`, { signal });
}

export interface TutorToken {
  token: string;
  expires_in_seconds: number;
}

// Tokens expire in 5 minutes — fetch a fresh one per question, never cache.
export function getTutorToken(courseId: string): Promise<TutorToken> {
  return request<TutorToken>(`/api/courses/${courseId}/tutor-token/`);
}

/**
 * Streams the tutor's answer from the FastAPI service (different origin than
 * Django). Native EventSource only supports GET without custom headers, so
 * the SSE stream is read manually via fetch + ReadableStream.
 *
 * Calls onChunk for every `data: <text>` event until `data: [DONE]`.
 */
export async function streamTutorChat(
  courseId: string,
  token: string,
  question: string,
  onChunk: (text: string) => void,
): Promise<void> {
  const res = await fetch(`${TUTOR_API_BASE}/courses/${courseId}/chat`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  if (!res.ok) {
    // FastAPI errors use {"detail": ...}; Django-style {"error": ...} is
    // handled too so both services map onto the same ApiError shape.
    let message = `Request failed with status ${res.status}.`;
    try {
      const data = (await res.json()) as { detail?: unknown; error?: unknown };
      if (typeof data.detail === "string") message = data.detail;
      else if (typeof data.error === "string") message = data.error;
    } catch {
      // Non-JSON error body — keep the fallback message.
    }
    throw new ApiError(res.status, message);
  }

  if (!res.body) {
    throw new ApiError(200, "The tutor service returned an empty stream.");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  for (;;) {
    const { done, value } = await reader.read();
    if (done) return;
    buffer += decoder.decode(value, { stream: true });

    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const rawEvent = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      for (const line of rawEvent.split("\n")) {
        if (!line.startsWith("data:")) continue;
        // Strip exactly the "data: " prefix — any further leading whitespace
        // belongs to the payload (word spacing between chunks).
        const payload = line.startsWith("data: ") ? line.slice(6) : line.slice(5);
        if (payload === "[DONE]") return;
        onChunk(payload);
      }
    }
  }
}

export function getOrgDashboard(orgId: string): Promise<OrgDashboard> {
  return request<OrgDashboard>(`/api/orgs/${orgId}/dashboard/`);
}

// The compliance report is a direct CSV download (Content-Disposition:
// attachment) — a plain same-site anchor navigation carries the session
// cookie, so no fetch/blob dance is needed.
export function complianceReportUrl(orgId: string): string {
  return `${API_BASE}/api/orgs/${orgId}/compliance-report/`;
}
