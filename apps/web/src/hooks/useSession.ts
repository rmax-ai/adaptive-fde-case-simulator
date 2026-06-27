import { useQuery } from "@tanstack/react-query";
import { getState, getSession } from "../api/client";

export function useSession(sessionId: string | null) {
  const sessionQuery = useQuery({
    queryKey: ["session", sessionId],
    queryFn: () => getSession(sessionId!),
    enabled: sessionId !== null,
  });

  const stateQuery = useQuery({
    queryKey: ["sessionState", sessionId],
    queryFn: () => getState(sessionId!),
    enabled: sessionId !== null,
  });

  return {
    session: sessionQuery.data ?? null,
    state: stateQuery.data ?? null,
    isLoading: sessionQuery.isLoading || stateQuery.isLoading,
    error: sessionQuery.error ?? stateQuery.error,
    refetch: () => {
      sessionQuery.refetch();
      stateQuery.refetch();
    },
  };
}
