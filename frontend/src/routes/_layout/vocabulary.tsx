import { createFileRoute } from "@tanstack/react-router"
import { useState } from "react"
import type { VocabularyPublic } from "@/client"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  useDeleteVocabulary,
  useUpdateVocabulary,
  useVocabulary,
} from "@/hooks/useReadingState"
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
              {entry.original_text}
              {entry.contextual_translation !== null &&
                ` — ${entry.contextual_translation}`}
            </p>
            {entry.contextual_translation === null && (
              <p className="text-muted-foreground">Sin traducción</p>
            )}
            <p className="whitespace-pre-wrap text-muted-foreground">
              {entry.context}
            </p>
            <p className="text-sm">
              Guardado el {new Date(entry.created_at).toLocaleDateString("es")}
            </p>
            <TranslationEditor entry={entry} />
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

function TranslationEditor({ entry }: { entry: VocabularyPublic }) {
  const [editing, setEditing] = useState(false)
  const [translation, setTranslation] = useState(
    entry.contextual_translation ?? "",
  )
  const update = useUpdateVocabulary()
  if (!editing)
    return (
      <Button
        variant="outline"
        onClick={() => {
          setTranslation(entry.contextual_translation ?? "")
          update.reset()
          setEditing(true)
        }}
      >
        Editar traducción de {entry.original_text}
      </Button>
    )
  return (
    <form
      className="space-y-2"
      onSubmit={(event) => {
        event.preventDefault()
        update.mutate(
          { id: entry.id, contextual_translation: translation.trim() || null },
          { onSuccess: () => setEditing(false) },
        )
      }}
    >
      <label htmlFor={`translation-${entry.id}`} className="text-sm">
        Traducción de {entry.original_text} (opcional)
      </label>
      <Input
        id={`translation-${entry.id}`}
        maxLength={500}
        value={translation}
        disabled={update.isPending}
        onChange={(event) => setTranslation(event.target.value)}
      />
      <p className="text-sm text-muted-foreground">
        Deja el campo vacío para guardar sin traducción.
      </p>
      <Button type="submit" disabled={update.isPending}>
        Guardar traducción
      </Button>
      <Button
        type="button"
        variant="outline"
        disabled={update.isPending}
        onClick={() => setEditing(false)}
      >
        Cancelar
      </Button>
      {update.isError && (
        <p role="alert">{extractErrorMessage(update.error)}</p>
      )}
    </form>
  )
}
