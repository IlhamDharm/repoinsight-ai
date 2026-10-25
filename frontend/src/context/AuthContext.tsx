import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { api } from "../api/client";
import { removeToken, setToken } from "../api/client";
import type { TokenResponse, User } from "../types/api";

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(() =>
    localStorage.getItem("repoinsight_token"),
  );
  const [isLoading, setIsLoading] = useState(true);
  const authDisabled = import.meta.env.VITE_AUTH_ENABLED !== "true";

  const fetchCurrentUser = useCallback(async () => {
    try {
      const profile = await api.get<User>("/api/v1/auth/me");
      setUser(profile);
    } catch {
      setUser(null);
      setTokenState(null);
      removeToken();
    }
  }, []);

  useEffect(() => {
    if (authDisabled) {
      setUser({ id: 0, email: "demo@localhost", is_active: true });
      setIsLoading(false);
    } else if (token) {
      fetchCurrentUser().finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, [authDisabled, token, fetchCurrentUser]);

  const login = useCallback(async (email: string, password: string) => {
    const data = await api.post<TokenResponse>("/api/v1/auth/login", {
      email,
      password,
    });
    setToken(data.access_token);
    setTokenState(data.access_token);
    const profile = await api.get<User>("/api/v1/auth/me");
    setUser(profile);
  }, []);

  const logout = useCallback(() => {
    removeToken();
    setTokenState(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        login,
        logout,
        isAuthenticated: !!user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
