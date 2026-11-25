import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, tokenStore } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // On first load: if a token is saved, ask the server who we are
  useEffect(() => {
    if (!tokenStore.get()) {
      setLoading(false);
      return;
    }
    api("/auth/me")
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false));
  }, []);

  const authenticate = useCallback(async (mode, email, password) => {
    const data = await api(`/auth/${mode}`, { method: "POST", body: { email, password } });
    tokenStore.set(data.access_token);
    setUser(data.user);
  }, []);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login: (e, p) => authenticate("login", e, p),
        signup: (e, p) => authenticate("signup", e, p),
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
