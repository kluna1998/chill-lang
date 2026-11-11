import { createFileRoute, Link } from "@tanstack/react-router"
import { AxiosError } from "axios"

import { ChapterList } from "@/components/Chapters/ChapterList"
import { Button } from "@/components/ui/button"
import { useBook } from "@/hooks/useBookQueries"

export const Route = createFileRoute("/_layout/books/$bookId/")({
  component: BookDetail,
  head: () => ({ meta: [{ title: "Libro - Chill-Lang" }] }),
})

function BookDetail() {
  const { bookId } = Route.useParams()
  const {
    data: book,
    error,
    isPending,
    isError,
    isFetching,
    refetch,
  } = useBook(bookId)
  return (
    <div className="flex flex-col gap-6">
      <Link to="/" className="underline underline-offset-4">
        Volver a mi biblioteca
      </Link>
      {isPending ? (
        <p role="status">Cargando libro…</p>
      ) : isError ? (
        <div role="alert">
          <p>
            {error instanceof AxiosError && error.response?.status === 404
              ? "Libro no encontrado."
              : "No se ha podido cargar el libro."}
          </p>
          <Button
            variant="outline"
            disabled={isFetching}
            onClick={() => refetch()}
          >
            Reintentar
          </Button>
        </div>
      ) : (
        book && (
          <>
            <header>
              <h1 className="break-words text-2xl font-bold tracking-tight">
                {book.title}
              </h1>
              <p className="break-words text-muted-foreground">
                {book.author || "Sin autor"}
              </p>
            </header>
            <ChapterList bookId={bookId} />
          </>
        )
      )}
    </div>
  )
}
