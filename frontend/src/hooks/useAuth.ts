import { useCallback, useEffect, useState } from "react";
import type { User } from "../types";
import { clearToken, fetchMe, getToken, login, register, setToken } from "../services/api";

type AuthState = "loading" | "unauthenticated" | "authenticated";

export function useAuth() {
  const [state, setState] = useState<AuthState>("loading");
  const [user, setUser] = useState<User | null>(null);

  // On mount, validate existing token
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setState("unauthenticated");
      return;
    }
    fetchMe()
      .then((data) => {
        setUser(data);
        setState("authenticated");
      })
      .catch(() => {
        clearToken();
        setState("unauthenticated");
      });
  }, []);

  const handleLogin = useCallback(async (username: string, password: string) => {
    const data = await login(username, password);
    setToken(data.access_token);
    setUser(data.user);
    setState("authenticated");
    return data.user as User;
  }, []);

  const handleRegister = useCallback(async (username: string, password: string) => {
    const data = await register(username, password);
    setToken(data.access_token);
    setUser(data.user);
    setState("authenticated");
    return data.user as User;
  }, []);

  const handleLogout = useCallback(() => {
    clearToken();
    setUser(null);
    setState("unauthenticated");
  }, []);

  const markOnboarded = useCallback(() => {
    setUser((prev) => prev ? { ...prev, onboarded: true } : prev);
  }, []);

  return { state, user, handleLogin, handleRegister, handleLogout, markOnboarded };
}
