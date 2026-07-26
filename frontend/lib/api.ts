const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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

export function askTutor(courseId: string, question: string): Promise<{ answer: string }> {
  return request<{ answer: string }>(`/api/courses/${courseId}/ask/`, {
    method: "POST",
    body: { question },
  });
}
