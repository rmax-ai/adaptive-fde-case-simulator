import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getAvailableActions, executeAction } from "../api/client";
import type { ActionParams } from "../types";

export function useActions(sessionId: string | null) {
  const queryClient = useQueryClient();

  const actionsQuery = useQuery({
    queryKey: ["actions", sessionId],
    queryFn: () => getAvailableActions(sessionId!),
    enabled: sessionId !== null,
  });

  const executeMutation = useMutation({
    mutationFn: ({
      actionType,
      params,
    }: {
      actionType: string;
      params: ActionParams;
    }) => executeAction(sessionId!, actionType, params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sessionState", sessionId] });
      queryClient.invalidateQueries({ queryKey: ["actions", sessionId] });
      queryClient.invalidateQueries({ queryKey: ["events", sessionId] });
      queryClient.invalidateQueries({ queryKey: ["artifacts", sessionId] });
    },
  });

  return {
    actions: actionsQuery.data ?? [],
    isLoading: actionsQuery.isLoading,
    error: actionsQuery.error,
    execute: executeMutation.mutate,
    isExecuting: executeMutation.isPending,
    executionError: executeMutation.error,
  };
}
