import { cookies } from "next/headers";

export const ACCESS_COOKIE = "haccp_access_token";
export const REFRESH_COOKIE = "haccp_refresh_token";

const ACCESS_MAX_AGE_SECONDS = 60 * 60;
const REFRESH_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

export type Session = {
  accessToken: string;
  refreshToken: string;
};

function baseCookieOptions() {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    // Enable it when the app is served over HTTPS.
    secure: process.env.SESSION_COOKIE_SECURE === "true",
    path: "/",
  };
}

export async function getSession(): Promise<Session | null> {
  const store = await cookies();
  const accessToken = store.get(ACCESS_COOKIE)?.value;
  const refreshToken = store.get(REFRESH_COOKIE)?.value;
  if (!accessToken || !refreshToken) {
    return null;
  }
  return { accessToken, refreshToken };
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
      maxAge: ACCESS_MAX_AGE_SECONDS,
    });
    store.set(REFRESH_COOKIE, session.refreshToken, {
      ...baseCookieOptions(),
      maxAge: REFRESH_MAX_AGE_SECONDS,
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
