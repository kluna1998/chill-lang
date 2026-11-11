import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { useState } from "react"

import { BooksService } from "@/client"
import { BookForm } from "@/components/Books/BookForm"
import { DeleteBook } from "@/components/Books/DeleteBook"
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/")({
  component: Library,
  head: () => ({ meta: [{ title: "Mi biblioteca - Chill-Lang" }] }),
})

const pageSize = 20

function Library() {
  const [page, setPage] = useState(0)
  const { user } = useAuth()
  const { data, isPending, isError, isFetching, refetch } = useQuery({
    queryKey: ["books", user?.id, page],
    queryFn: async () =>
      (
        await BooksService.readBooks({
          query: { skip: page * pageSize, limit: pageSize },
        })
      ).data,
    enabled: !!user,
  })

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold tracking-tight">Mi biblioteca</h1>
        <BookForm />
      </div>
      {isPending ? (
        <p role="status">Cargando libros…</p>
      ) : isError ? (
        <div role="alert" className="rounded-lg border p-8 text-center">
          <p>No se ha podido cargar tu biblioteca.</p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => refetch()}
            disabled={isFetching}
          >
            Reintentar
          </Button>
        </div>
      ) : (
        data &&
        (data.count === 0 ? (
          <div className="rounded-lg border p-8 text-center">
            <h2 className="text-lg font-semibold">Todavía no tienes libros</h2>
            <p className="mt-2 text-muted-foreground">
              Añade un libro con su título y autor para empezar tu biblioteca.
            </p>
          </div>
        ) : (
          <>
            <ul className="flex flex-col gap-4" aria-label="Libros">
              {data.data.map((book) => (
                <li
                  key={book.id}
                  className="flex flex-wrap items-center justify-between gap-4 rounded-lg border p-4"
                >
                  <div className="min-w-0">
                    <h2 className="break-words text-lg font-semibold">
                      {book.title}
                    </h2>
                    <p className="break-words text-muted-foreground">
                      {book.author || "Sin autor"}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button variant="outline" asChild>
                      <Link to="/books/$bookId" params={{ bookId: book.id }}>
                        Abrir libro
                      </Link>
                    </Button>
                    <BookForm book={book} />
                    <DeleteBook
                      book={book}
                      onDeleted={() => {
                        if (data.data.length === 1 && page > 0)
                          setPage(page - 1)
                      }}
                    />
                  </div>
                </li>
              ))}
            </ul>
            {data.data.length === 0 && <p>No hay libros en esta página.</p>}
            <nav
              aria-label="Paginación de libros"
              className="flex flex-wrap items-center justify-between gap-4"
            >
              <Button
                variant="outline"
                disabled={page === 0 || isFetching}
                onClick={() => setPage(page - 1)}
              >
                Anterior
              </Button>
              <p role="status">
                Página {page + 1} · {data.count} libros
              </p>
              <Button
                variant="outline"
                disabled={(page + 1) * pageSize >= data.count || isFetching}
                onClick={() => setPage(page + 1)}
              >
                Siguiente
              </Button>
            </nav>
          </>
        ))
      )}
    </div>
  )
}
