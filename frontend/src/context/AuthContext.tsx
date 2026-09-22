import React, { createContext, useContext, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { authApi } from "../api/auth";
import { workspacesApi } from "../api/workspaces";
import type {
  User,
  Workspace,
  WorkspaceMembership,
  GoogleStatus,
  MeResponse,
} from "../types";

export interface AuthContextValue {
  user: User | null;
  workspaces: WorkspaceMembership[];
  currentWorkspace: Workspace | null;
  currentRole: string | null;
  google: GoogleStatus | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: Error | null;
  switchWorkspace: (workspaceId: string) => Promise<void>;
  createWorkspace: (name: string) => Promise<Workspace>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();

  const {
    data: meData,
    isLoading,
    error,
    refetch,
  } = useQuery<MeResponse, Error>({
    queryKey: ["auth", "me"],
    queryFn: async () => {
      try {
        return await authApi.getMe();
      } catch (err: any) {
        if (err?.status === 401) {
          return null as unknown as MeResponse;
        }
        throw err;
      }
    },
    retry: false,
    staleTime: 1000 * 60 * 5,
  });

  const switchWorkspaceMutation = useMutation({
    mutationFn: (workspaceId: string) => workspacesApi.switch(workspaceId),
    onSuccess: async () => {
      await queryClient.invalidateQueries();
    },
  });

  const createWorkspaceMutation = useMutation({
    mutationFn: async (name: string) => {
      const newWorkspace = await workspacesApi.create(name);
      await workspacesApi.switch(newWorkspace.id);
      return newWorkspace;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries();
    },
  });

  const logoutMutation = useMutation({
    mutationFn: () => authApi.logout(),
    onSuccess: () => {
      queryClient.setQueryData(["auth", "me"], null);
      queryClient.clear();
    },
  });

  const isAuthenticated = Boolean(meData && meData.user);

  const value = useMemo<AuthContextValue>(
    () => ({
      user: meData?.user ?? null,
      workspaces: meData?.workspaces ?? [],
      currentWorkspace: meData?.current_workspace ?? null,
      currentRole: meData?.current_role ?? null,
      google: meData?.google ?? null,
      isLoading,
      isAuthenticated,
      error: error ?? null,
      switchWorkspace: async (workspaceId: string) => {
        await switchWorkspaceMutation.mutateAsync(workspaceId);
      },
      createWorkspace: async (name: string) => {
        return await createWorkspaceMutation.mutateAsync(name);
      },
      logout: async () => {
        await logoutMutation.mutateAsync();
      },
      refresh: async () => {
        await refetch();
      },
    }),
    [meData, isLoading, error, switchWorkspaceMutation, createWorkspaceMutation, logoutMutation, refetch]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
