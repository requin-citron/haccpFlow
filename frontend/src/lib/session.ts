import { cookies } from "next/headers";

import {
  ACCESS_COOKIE,
  DEFAULT_REFRESH_MAX_AGE_SECONDS,
  REFRESH_COOKIE,
  accessTokenSecondsRemaining,
  baseCookieOptions,
  type Session,
} from "@/lib/auth-cookies";

export type { Session } from "@/lib/auth-cookies";

export async function getSession(): Promise<Session | null> {
  const store = await cookies();
  const accessToken = store.get(ACCESS_COOKIE)?.value ?? "";
  const refreshToken = store.get(REFRESH_COOKIE)?.value;
  if (!refreshToken) {
    return null;
  }
  return {
    accessToken,
    refreshToken,
    accessMaxAge: accessToken
      ? Math.max(60, accessTokenSecondsRemaining(accessToken) + 60)
      : 0,
    refreshMaxAge: DEFAULT_REFRESH_MAX_AGE_SECONDS,
  };
}

/**
 * Persist the session. Returns false when called during a render, where
 * writing cookies is not allowed (only Server Actions and Route Handlers can).
 */
export async function persistSession(session: Session): Promise<boolean> {
  try {
    const store = await cookies();
    store.set(ACCESS_COOKIE, session.accessToken, {
      ...baseCookieOptions(),
      maxAge: Math.max(60, session.accessMaxAge),
    });
    store.set(REFRESH_COOKIE, session.refreshToken, {
      ...baseCookieOptions(),
      maxAge: Math.max(60, session.refreshMaxAge),
    });
    return true;
  } catch {
    return false;
  }
}

export async function clearSession(): Promise<void> {
  try {
    const store = await cookies();
    store.delete(ACCESS_COOKIE);
    store.delete(REFRESH_COOKIE);
  } catch {
    // Nothing to do: the session is already gone from the caller's point of view.
  }
}
