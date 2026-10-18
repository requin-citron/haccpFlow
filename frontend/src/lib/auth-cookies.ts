export const ACCESS_COOKIE = "haccp_access_token";
export const REFRESH_COOKIE = "haccp_refresh_token";

export const DEFAULT_REFRESH_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

// Keep the access cookie a little longer than the JWT so the proxy can see
// that it expired and rotate it, instead of losing the refresh opportunity.
const ACCESS_COOKIE_GRACE_SECONDS = 60;

export type TokenPairPayload = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  refresh_expires_in?: number;
};

export type Session = {
  accessToken: string;
  refreshToken: string;
  accessMaxAge: number;
  refreshMaxAge: number;
};

export function sessionFromTokenPair(payload: TokenPairPayload): Session {
  return {
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token,
    accessMaxAge: Math.max(60, payload.expires_in + ACCESS_COOKIE_GRACE_SECONDS),
    refreshMaxAge: Math.max(
      60,
      payload.refresh_expires_in ?? DEFAULT_REFRESH_MAX_AGE_SECONDS,
    ),
  };
}

function jwtExpiresAt(token: string | undefined): number | null {
  if (!token) {
    return null;
  }
  const encodedPayload = token.split(".")[1];
  if (!encodedPayload) {
    return null;
  }
  try {
    const normalized = encodedPayload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
    const payload = JSON.parse(atob(padded)) as { exp?: unknown };
    return typeof payload.exp === "number" ? payload.exp : null;
  } catch {
    return null;
  }
}

export function accessTokenNeedsRefresh(
  token: string | undefined,
  now: number = Date.now(),
): boolean {
  const expiresAt = jwtExpiresAt(token);
  return expiresAt === null || expiresAt <= Math.floor(now / 1000) + 30;
}

export function accessTokenSecondsRemaining(
  token: string | undefined,
  now: number = Date.now(),
): number {
  const expiresAt = jwtExpiresAt(token);
  return expiresAt === null ? 0 : Math.max(0, expiresAt - Math.floor(now / 1000));
}

export function baseCookieOptions() {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure:
      process.env.SESSION_COOKIE_SECURE === "true" ||
      process.env.NODE_ENV === "production",
    path: "/",
  };
}
