import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  type ReadingProgressPublic,
  ReadingService,
  type VocabularyCreate,
  type VocabularyUpdate,
} from "@/client"
import useAuth from "./useAuth"

export function useVocabulary(skip = 0) {
  const { user } = useAuth()
  return useQuery({
    queryKey: ["vocabulary", user?.id, skip],
    queryFn: async () =>
      (await ReadingService.listVocabulary({ query: { skip, limit: 20 } }))
        .data,
    enabled: !!user,
    retry: false,
  })
}

export function useSaveVocabulary() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: VocabularyCreate) =>
      (await ReadingService.saveVocabulary({ body })).data,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["vocabulary"] }),
    retry: false,
  })
}

export function useDeleteVocabulary() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (id: string) =>
      ReadingService.deleteVocabulary({ path: { entry_id: id } }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["vocabulary"] }),
    retry: false,
  })
}

export function useUpdateVocabulary() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ id, ...body }: VocabularyUpdate & { id: string }) =>
      (await ReadingService.updateVocabulary({ path: { entry_id: id }, body }))
        .data,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["vocabulary"] }),
    retry: false,
  })
}

export function useReadingProgress(bookId: string) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const queryKey = ["progress", user?.id, bookId]
  return useQuery({
    queryKey,
    queryFn: async ({ signal }) => {
      const before = queryClient.getQueryData<ReadingProgressPublic | null>(
        queryKey,
      )
      const { data } = await ReadingService.getProgress({
        path: { book_id: bookId },
        signal,
      })
      const current = queryClient.getQueryData<ReadingProgressPublic | null>(
        queryKey,
      )
      // A GET started before a successful save cannot roll its cache back.
      return current &&
        current.version > (before?.version ?? 0) &&
        current.version > (data?.version ?? 0)
        ? current
        : data
    },
    enabled: !!user,
    retry: false,
    staleTime: 0,
    refetchOnWindowFocus: false,
  })
}
