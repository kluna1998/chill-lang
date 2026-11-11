import { Link } from "@tanstack/react-router"
import { AxiosError } from "axios"

import { Button } from "@/components/ui/button"
import { useChapter, useChapters } from "@/hooks/useBookQueries"

export function ChapterReader({
  bookId,
  chapterId,
}: {
  bookId: string
  chapterId: string
}) {
  const chapter = useChapter(bookId, chapterId)
  const index = useChapters(bookId)
  const current = index.data?.findIndex((entry) => entry.id === chapterId) ?? -1
  const previous = current > 0 ? index.data?.[current - 1] : undefined
  const next = current >= 0 ? index.data?.[current + 1] : undefined

  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-8">
      <Link
        to="/books/$bookId"
        params={{ bookId }}
        className="underline underline-offset-4"
      >
        Volver al libro
      </Link>
      {chapter.isPending ? (
        <p role="status">Cargando capítulo…</p>
      ) : chapter.isError ? (
        <div role="alert">
          <p>
            {chapter.error instanceof AxiosError &&
            chapter.error.response?.status === 404
              ? "Capítulo no encontrado."
              : "No se ha podido cargar el capítulo."}
          </p>
          <Button
            variant="outline"
            disabled={chapter.isFetching}
            onClick={() => chapter.refetch()}
          >
            Reintentar
          </Button>
        </div>
      ) : (
        chapter.data && (
          <>
            <article>
              <h1 className="mb-8 break-words text-3xl font-bold tracking-tight">
                {chapter.data.title}
              </h1>
              <div className="whitespace-pre-wrap break-words font-serif text-lg leading-relaxed">
                {chapter.data.content}
              </div>
            </article>
            {index.isError ? (
              <div role="alert">
                <p>No se ha podido cargar la navegación entre capítulos.</p>
                <Button
                  variant="outline"
                  disabled={index.isFetching}
                  onClick={() => index.refetch()}
                >
                  Reintentar índice
                </Button>
              </div>
            ) : (
              <nav
                aria-label="Navegación entre capítulos"
                className="flex justify-between gap-4"
              >
                {previous ? (
                  <Button variant="outline" asChild>
                    <Link
                      to="/books/$bookId/chapters/$chapterId"
                      params={{ bookId, chapterId: previous.id }}
                    >
                      Anterior
                    </Link>
                  </Button>
                ) : (
                  <Button variant="outline" disabled>
                    Anterior
                  </Button>
                )}
                {next ? (
                  <Button variant="outline" asChild>
                    <Link
                      to="/books/$bookId/chapters/$chapterId"
                      params={{ bookId, chapterId: next.id }}
                    >
                      Siguiente
                    </Link>
                  </Button>
                ) : (
                  <Button variant="outline" disabled>
                    Siguiente
                  </Button>
                )}
              </nav>
            )}
            {index.isPending && <p role="status">Cargando índice…</p>}
          </>
        )
      )}
    </div>
  )
}
