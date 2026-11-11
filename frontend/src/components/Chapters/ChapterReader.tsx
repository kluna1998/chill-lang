import { Link } from "@tanstack/react-router"
import { AxiosError } from "axios"
import { useCallback, useState } from "react"
import type { ChapterPublic } from "@/client"
import { ReadingContextPanel } from "@/components/Reader/ReadingContextPanel"
import {
  defaultReadingPreferences,
  ReadingPreferences,
  type ReadingPreferencesValue,
} from "@/components/Reader/ReadingPreferences"
import { SelectableText } from "@/components/Reader/SelectableText"
import type { TextSelectionContext } from "@/components/Reader/selection"

import { Button } from "@/components/ui/button"
import { useChapter, useChapters } from "@/hooks/useBookQueries"

export function ChapterReader({
  bookId,
  chapterId,
}: {
  bookId: string
  chapterId: string
}) {
  const [preferences, setPreferences] = useState(defaultReadingPreferences)
  const chapter = useChapter(bookId, chapterId)
  const index = useChapters(bookId)
  const current = index.data?.findIndex((entry) => entry.id === chapterId) ?? -1
  const previous = current > 0 ? index.data?.[current - 1] : undefined
  const next = current >= 0 ? index.data?.[current + 1] : undefined

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8">
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
            <ReadingPreferences value={preferences} onChange={setPreferences} />
            <InteractiveChapter
              key={`${bookId}:${chapterId}`}
              chapter={chapter.data}
              bookId={bookId}
              preferences={preferences}
            />
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

function InteractiveChapter({
  chapter,
  bookId,
  preferences,
}: {
  chapter: ChapterPublic
  bookId: string
  preferences: ReadingPreferencesValue
}) {
  const [selection, setSelection] = useState<TextSelectionContext | null>(null)
  const close = useCallback(() => {
    setSelection(null)
    document.getSelection()?.removeAllRanges()
  }, [])
  return (
    <div
      className={
        selection
          ? "grid items-start gap-6 pb-[36vh] xl:grid-cols-[minmax(0,42rem)_18rem] xl:pb-0"
          : "mx-auto w-full max-w-2xl"
      }
    >
      <article className="min-w-0">
        <h1 className="mb-8 break-words text-3xl font-bold tracking-tight">
          {chapter.title}
        </h1>
        <SelectableText
          content={chapter.content}
          bookId={bookId}
          chapterId={chapter.id}
          onSelect={setSelection}
          style={{
            fontSize: `${preferences.fontSize}px`,
            lineHeight: preferences.lineHeight,
            fontFamily: preferences.fontFamily,
          }}
        />
      </article>
      {selection && (
        <ReadingContextPanel selection={selection} onClose={close} />
      )}
    </div>
  )
}
