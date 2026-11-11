import { Link } from "@tanstack/react-router"

import { Button } from "@/components/ui/button"
import { useChapters } from "@/hooks/useBookQueries"

export function ChapterList({ bookId }: { bookId: string }) {
  const { data, isPending, isError, isFetching, refetch } = useChapters(bookId)
  return (
    <section
      aria-labelledby="chapter-index-title"
      className="flex flex-col gap-4"
    >
      <h2 id="chapter-index-title" className="text-xl font-semibold">
        Índice de capítulos
      </h2>
      {isPending ? (
        <p role="status">Cargando capítulos…</p>
      ) : isError ? (
        <div role="alert">
          <p>No se ha podido cargar el índice de capítulos.</p>
          <Button
            variant="outline"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            Reintentar
          </Button>
        </div>
      ) : data?.length === 0 ? (
        <p>Este libro todavía no tiene capítulos.</p>
      ) : (
        <ol className="flex flex-col gap-3" aria-label="Capítulos">
          {data?.map((chapter) => (
            <li key={chapter.id}>
              <Link
                to="/books/$bookId/chapters/$chapterId"
                params={{ bookId, chapterId: chapter.id }}
                className="break-words underline underline-offset-4"
              >
                {chapter.position}. {chapter.title}
              </Link>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
