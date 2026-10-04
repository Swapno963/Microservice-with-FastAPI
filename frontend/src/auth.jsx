import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";

const ACCESS_KEY = "shopverse_access";
const REFRESH_KEY = "shopverse_refresh";

const AuthContext = createContext(null);

function formatError(body) {
  const detail = body?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg || item?.message || "Invalid value")
      .join(" ");
  }
  return "Something went wrong. Please try again.";
}

export function readClaims(token) {
  if (!token) return null;
  try {
    const segment = token.split(".")[1];
    const json = JSON.parse(atob(segment.replace(/-/g, "+").replace(/_/g, "/")));
    return {
      sub: json.sub ? String(json.sub) : null,
      isAdmin: Boolean(json.is_admin),
    };
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem(ACCESS_KEY));
  const [refreshToken, setRefreshToken] = useState(() => localStorage.getItem(REFRESH_KEY));
  const [authOpen, setAuthOpen] = useState(false);
  const [notice, setNotice] = useState("");
  const accessRef = useRef(accessToken);
  const refreshRef = useRef(refreshToken);
  const refreshFlight = useRef(null);

  function saveTokens(tokens) {
    accessRef.current = tokens.access_token;
    refreshRef.current = tokens.refresh_token;
    localStorage.setItem(ACCESS_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
    setAccessToken(tokens.access_token);
    setRefreshToken(tokens.refresh_token);
  }

  function signOut(message) {
    accessRef.current = null;
    refreshRef.current = null;
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    setAccessToken(null);
    setRefreshToken(null);
    if (message) showNotice(message);
  }

  function showNotice(message) {
    setNotice(message);
    window.setTimeout(() => {
      setNotice((current) => (current === message ? "" : current));
    }, 5000);
  }

  async function refreshSession() {
    if (!refreshRef.current) return false;
    if (!refreshFlight.current) {
      refreshFlight.current = (async () => {
        const response = await fetch("/api/v1/auth/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshRef.current }),
        });
        if (!response.ok) return false;
        saveTokens(await response.json());
        return true;
      })().finally(() => {
        refreshFlight.current = null;
      });
    }
    return refreshFlight.current;
  }

  const requestRef = useRef(null);
  requestRef.current = async (path, options = {}, allowRefresh = true) => {
    const headers = { ...(options.headers || {}) };
    if (accessRef.current) headers.Authorization = `Bearer ${accessRef.current}`;

    let body = options.body;
    if (body && !(body instanceof URLSearchParams) && typeof body !== "string") {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(body);
    }

    const response = await fetch(path, { method: options.method || "GET", headers, body });
    if (
      response.status === 401 &&
      allowRefresh &&
      refreshRef.current &&
      !path.endsWith("/auth/login") &&
      !path.endsWith("/auth/refresh")
    ) {
      const refreshed = await refreshSession();
      if (refreshed) return requestRef.current(path, options, false);
      signOut("Your session expired. Sign in again.");
      throw new Error("Your session expired. Sign in again.");
    }

    if (response.status === 204) return null;
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(formatError(payload));
    return payload;
  };
  const api = useCallback((path, options, allowRefresh) => requestRef.current(path, options, allowRefresh), []);

  async function login(email, password) {
    const tokens = await api(
      "/api/v1/auth/login",
      {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ username: email, password }),
      },
      false,
    );
    saveTokens(tokens);
  }

  async function register(payload) {
    await api("/api/v1/auth/register", { method: "POST", body: payload }, false);
    await login(payload.email, payload.password);
  }

  const claims = useMemo(() => readClaims(accessToken), [accessToken]);

  const value = {
    accessToken,
    refreshToken,
    claims,
    isSignedIn: Boolean(accessToken),
    isAdmin: Boolean(claims?.isAdmin),
    authOpen,
    openAuth: () => setAuthOpen(true),
    closeAuth: () => setAuthOpen(false),
    notice,
    showNotice,
    api,
    login,
    register,
    signOut,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
