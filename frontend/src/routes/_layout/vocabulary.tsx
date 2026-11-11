import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { useDeleteVocabulary, useVocabulary } from "@/hooks/useReadingState"
import { extractErrorMessage } from "@/utils"

export const Route = createFileRoute("/_layout/vocabulary")({
  component: VocabularyPage,
  head: () => ({ meta: [{ title: "Mi vocabulario - Chill-Lang" }] }),
})

function VocabularyPage() {
  const [skip, setSkip] = useState(0)
  const vocabulary = useVocabulary(skip)
  const remove = useDeleteVocabulary()
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Mi vocabulario</h1>
      {vocabulary.isPending && <p role="status">Cargando vocabulario…</p>}
      {vocabulary.isError && (
        <div role="alert">
          <p>{extractErrorMessage(vocabulary.error)}</p>
          <Button onClick={() => vocabulary.refetch()}>Reintentar</Button>
        </div>
      )}
      {remove.isError && (
        <p role="alert">{extractErrorMessage(remove.error)}</p>
      )}
      {vocabulary.data?.count === 0 && <p>Todavía no has guardado palabras.</p>}
      <ul className="space-y-4">
        {vocabulary.data?.data.map((entry) => (
          <li
            key={entry.id}
            className="space-y-2 rounded border p-4 break-words"
          >
            <p className="font-semibold">
              {entry.original_text} — {entry.contextual_translation}
            </p>
            <p className="whitespace-pre-wrap text-muted-foreground">
              {entry.context}
            </p>
            <p className="text-sm">
              Guardado el {new Date(entry.created_at).toLocaleDateString("es")}
            </p>
            <Button
              variant="outline"
              disabled={remove.isPending}
              onClick={() =>
                remove.mutate(entry.id, {
                  onSuccess: () => {
                    if (vocabulary.data?.data.length === 1 && skip > 0)
                      setSkip(skip - 20)
                  },
                })
              }
            >
              Eliminar {entry.original_text}
            </Button>
          </li>
        ))}
      </ul>
      {!!vocabulary.data?.count && (
        <nav
          aria-label="Paginación del vocabulario"
          className="flex items-center gap-4"
        >
          <Button
            variant="outline"
            disabled={skip === 0}
            onClick={() => setSkip(skip - 20)}
          >
            Anterior
          </Button>
          <p>
            {skip + 1}–{Math.min(skip + 20, vocabulary.data.count)} de{" "}
            {vocabulary.data.count}
          </p>
          <Button
            variant="outline"
            disabled={skip + 20 >= vocabulary.data.count}
            onClick={() => setSkip(skip + 20)}
          >
            Siguiente
          </Button>
        </nav>
      )}
    </div>
  )
}
