"use client";

import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { User, AuthStatus, LoginPayload, RegisterPayload } from "@/types/auth";
import { apiClient } from "@/lib/api-client";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => Promise<User>;
  setupInitialAdmin: (payload: RegisterPayload) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const status = await apiClient<AuthStatus>("/api/v1/auth/status");
      if (status.authenticated && status.user) {
        setUser(status.user);
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (payload: LoginPayload): Promise<User> => {
    const loggedUser = await apiClient<User>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setUser(loggedUser);
    return loggedUser;
  };

  const setupInitialAdmin = async (payload: RegisterPayload): Promise<User> => {
    const adminUser = await apiClient<User>("/api/v1/auth/setup", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setUser(adminUser);
    return adminUser;
  };

  const logout = async (): Promise<void> => {
    try {
      await apiClient<{ success: boolean; message: string }>("/api/v1/auth/logout", {
        method: "POST",
      });
    } finally {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: !!user,
        login,
        setupInitialAdmin,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
