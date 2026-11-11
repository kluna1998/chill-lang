import { createFileRoute } from "@tanstack/react-router"

import { ChapterReader } from "@/components/Chapters/ChapterReader"

export const Route = createFileRoute(
  "/_layout/books/$bookId/chapters/$chapterId",
)({
  component: ReadingPage,
  head: () => ({ meta: [{ title: "Lectura - Chill-Lang" }] }),
})

function ReadingPage() {
  const { bookId, chapterId } = Route.useParams()
  return <ChapterReader bookId={bookId} chapterId={chapterId} />
}
