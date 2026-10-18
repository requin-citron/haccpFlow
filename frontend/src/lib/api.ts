import {
  sessionFromTokenPair,
  type Session,
  type TokenPairPayload,
} from "@/lib/auth-cookies";
import { getSession } from "@/lib/session";

const API_BASE_URL = (process.env.API_INTERNAL_URL ?? "http://localhost:8000").replace(/\/+$/, "");

const REQUEST_TIMEOUT_MS = 10_000;

/** Extracts can be long to generate: give them more room than an API call. */
const EXPORT_TIMEOUT_MS = 60_000;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly context: Record<string, unknown> | null;

  constructor(
    status: number,
    code: string,
    message: string,
    context: Record<string, unknown> | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.context = context;
  }
}

type BackendErrorPayload = {
  detail?: string;
  code?: string;
  context?: Record<string, unknown> | null;
};

async function fetchBackend(
  path: string,
  init: RequestInit,
  timeoutMs: number = REQUEST_TIMEOUT_MS,
): Promise<Response> {
  return fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    signal: AbortSignal.timeout(timeoutMs),
  });
}

async function toApiError(response: Response): Promise<ApiError> {
  let payload: BackendErrorPayload = {};
  try {
    payload = (await response.json()) as BackendErrorPayload;
  } catch {
    payload = {};
  }
  return new ApiError(
    response.status,
    payload.code ?? `http_${response.status}`,
    payload.detail ?? "Le serveur a renvoyé une erreur inattendue.",
    payload.context ?? null,
  );
}

export async function signIn(email: string, password: string): Promise<Session | null> {
  const response = await fetchBackend("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username: email, password }),
  });
  if (response.status === 401) {
    return null;
  }
  if (!response.ok) {
    throw await toApiError(response);
  }
  return sessionFromTokenPair((await response.json()) as TokenPairPayload);
}

export async function signOut(session: Session): Promise<void> {
  try {
    await fetchBackend("/api/v1/auth/logout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: session.refreshToken }),
    });
  } catch {
    // Signing out locally must succeed even if the API is unreachable.
  }
}

/**
 * Call the backend with the session stored in httpOnly cookies.
 *
 * Access-token rotation is handled once, in `proxy.ts`, before the request
 * reaches a Server Component, Server Action or Route Handler. Keeping the
 * refresh out of render code is deliberate: a Server Component cannot persist
 * the rotated cookies.
 */
async function authorizedFetch(
  path: string,
  init: RequestInit,
  timeoutMs: number,
): Promise<Response> {
  const session = await getSession();
  if (!session || !session.accessToken) {
    throw new ApiError(401, "unauthenticated", "Session absente.");
  }

  return fetchBackend(
    path,
    { ...init, headers: withAuth(init.headers, session) },
    timeoutMs,
  );
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs: number = REQUEST_TIMEOUT_MS,
): Promise<T> {
  const response = await authorizedFetch(path, init, timeoutMs);

  if (!response.ok) {
    throw await toApiError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

/** Same authentication, but the raw response: used to stream files through. */
export async function apiFetchRaw(path: string, init: RequestInit = {}): Promise<Response> {
  return authorizedFetch(path, init, EXPORT_TIMEOUT_MS);
}

function withAuth(headers: HeadersInit | undefined, session: Session): Headers {
  const merged = new Headers(headers);
  merged.set("Authorization", `Bearer ${session.accessToken}`);
  return merged;
}
