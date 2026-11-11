import { useMutation, useQuery } from "@tanstack/react-query"
import { AxiosError } from "axios"

import { BooksService, type ChapterSummary } from "@/client"
import useAuth from "./useAuth"

// Do not retry unavailable private resources or invalid UUIDs.
const retry = (failureCount: number, error: Error) =>
  !(
    error instanceof AxiosError &&
    [401, 403, 404, 422].includes(error.response?.status ?? 0)
  ) && failureCount < 3

export function useBook(bookId: string) {
  const { user } = useAuth()
  return useQuery({
    queryKey: ["books", user?.id, "detail", bookId],
    queryFn: async () =>
      (await BooksService.getBook({ path: { book_id: bookId } })).data,
    enabled: !!user,
    retry,
  })
}

export function useChapters(bookId: string) {
  const { user } = useAuth()
  return useQuery({
    queryKey: ["books", user?.id, bookId, "chapters"],
    queryFn: async () => {
      const chapters: ChapterSummary[] = []
      let skip = 0
      while (true) {
        const { data: page } = await BooksService.readChapters({
          path: { book_id: bookId },
          query: { skip, limit: 100 },
        })
        chapters.push(...page.data)
        skip += page.data.length
        if (skip >= page.count || page.data.length === 0) break
      }
      return chapters.sort(
        (a, b) => a.position - b.position || a.id.localeCompare(b.id),
      )
    },
    enabled: !!user,
    staleTime: 60_000,
    retry,
  })
}

export function useChapter(bookId: string, chapterId: string) {
  const { user } = useAuth()
  return useQuery({
    queryKey: ["books", user?.id, bookId, "chapters", chapterId],
    queryFn: async () =>
      (
        await BooksService.getChapter({
          path: { book_id: bookId, chapter_id: chapterId },
        })
      ).data,
    enabled: !!user,
    retry,
  })
}

export function useAnalyzeSelection() {
  return useMutation({
    mutationFn: async ({
      bookId,
      chapterId,
      startOffset,
      endOffset,
    }: {
      bookId: string
      chapterId: string
      startOffset: number
      endOffset: number
    }) =>
      (
        await BooksService.analyzeChapterSelection({
          path: { book_id: bookId, chapter_id: chapterId },
          body: {
            start_offset: startOffset,
            end_offset: endOffset,
            offset_unit: "utf-16",
          },
        })
      ).data,
  })
}
