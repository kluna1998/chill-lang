import { useEffect } from "react"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  useAnalyzeSelection,
  useExplainSelection,
} from "@/hooks/useBookQueries"
import { useSaveVocabulary } from "@/hooks/useReadingState"
import { extractErrorMessage } from "@/utils"
import type { TextSelectionContext } from "./selection"

export function ReadingContextPanel({
  selection,
  onClose,
}: {
  selection: TextSelectionContext
  onClose: () => void
}) {
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !event.defaultPrevented) onClose()
    }
    document.addEventListener("keydown", closeOnEscape)
    return () => document.removeEventListener("keydown", closeOnEscape)
  }, [onClose])
  return (
    <aside
      aria-labelledby="reading-context-title"
      className="fixed inset-x-4 bottom-4 z-20 max-h-[32vh] overflow-auto rounded-lg border bg-background p-4 shadow-lg xl:sticky xl:inset-auto xl:top-20 xl:z-auto xl:max-h-[75vh] xl:self-start xl:shadow-none"
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 id="reading-context-title" className="font-semibold">
          Tu selección
        </h2>
        <Button
          variant="ghost"
          size="sm"
          onClick={onClose}
          aria-label="Cerrar panel contextual"
        >
          Cerrar
        </Button>
      </div>
      <p
        className="whitespace-pre-wrap break-words font-medium"
        data-testid="selected-text"
      >
        {selection.text}
      </p>
      <h3 className="mt-4 text-sm font-semibold">Contexto original</h3>
      <p
        className="mt-1 whitespace-pre-wrap break-words text-sm text-muted-foreground"
        data-testid="selection-context"
      >
        {selection.context}
      </p>
      <SelectionExplainer
        key={`ai:${selection.bookId}:${selection.chapterId}:${selection.startOffset}:${selection.endOffset}`}
        selection={selection}
      />
      <SelectionAnalyzer
        key={`${selection.bookId}:${selection.chapterId}:${selection.startOffset}:${selection.endOffset}`}
        selection={selection}
      />
    </aside>
  )
}

function SelectionAnalyzer({ selection }: { selection: TextSelectionContext }) {
  const analysis = useAnalyzeSelection()
  return (
    <section className="mt-4 border-t pt-4" aria-label="Análisis lingüístico">
      <LoadingButton
        loading={analysis.isPending}
        onClick={() => analysis.mutate(selection)}
      >
        Analizar selección
      </LoadingButton>
      {analysis.isPending && (
        <p role="status" className="mt-2 text-sm">
          Analizando selección…
        </p>
      )}
      {analysis.isError && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {extractErrorMessage(analysis.error)}
        </p>
      )}
      {analysis.data && analysis.data.selected_text !== selection.text && (
        <p role="alert" className="mt-2 text-sm">
          El texto del capítulo ha cambiado. Vuelve a abrirlo antes de analizar.
        </p>
      )}
      {analysis.data && analysis.data.selected_text === selection.text && (
        <div className="mt-4 space-y-4">
          <h3 className="text-sm font-semibold">Contexto analizado</h3>
          <p className="whitespace-pre-wrap break-words text-sm">
            {analysis.data.context}
          </p>
          {analysis.data.context_truncated && (
            <p className="text-sm text-muted-foreground">
              Contexto limitado: la oración puede estar incompleta.
            </p>
          )}
          {!analysis.data.selection_covers_full_tokens && (
            <p className="text-sm text-muted-foreground">
              La selección contiene parte de una palabra; se muestran los tokens
              que la solapan.
            </p>
          )}
          <ul className="space-y-4" aria-label="Tokens analizados">
            {analysis.data.tokens.map((token) => (
              <li
                key={token.start_offset}
                className="break-words rounded border p-3 text-sm"
              >
                <p className="font-semibold">{token.text}</p>
                <p>Lema: {token.lemma ?? "No disponible"}</p>
                <p>Categoría (POS): {token.pos ?? "No disponible"}</p>
                <p>
                  Morfología:{" "}
                  {token.morphology === null
                    ? "No disponible"
                    : Object.entries(token.morphology)
                        .map(
                          ([name, values]) => `${name}: ${values.join(", ")}`,
                        )
                        .join(" · ") || "Sin rasgos asignados"}
                </p>
                <p>Dependencia: {token.dependency ?? "No disponible"}</p>
                {token.head_text !== null && (
                  <p>Núcleo sintáctico: {token.head_text}</p>
                )}
              </li>
            ))}
          </ul>
          <p className="text-xs text-muted-foreground">
            Predicciones del modelo: pueden contener errores. No incluyen
            traducción.
          </p>
        </div>
      )}
    </section>
  )
}

function SelectionExplainer({
  selection,
}: {
  selection: TextSelectionContext
}) {
  const result = useExplainSelection()
  const save = useSaveVocabulary()
  const explanation = result.data?.explanation
  const matches = result.data?.selected_text === selection.text
  return (
    <section className="mt-4 border-t pt-4" aria-label="Explicación con IA">
      <LoadingButton
        loading={result.isPending}
        onClick={() => result.mutate(selection)}
      >
        Explicar con IA
      </LoadingButton>
      {result.isPending && (
        <p role="status" className="mt-2 text-sm">
          Preparando explicación…
        </p>
      )}
      {result.isError && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {extractErrorMessage(result.error)}
        </p>
      )}
      {result.data && !matches && (
        <p role="alert" className="mt-2 text-sm">
          El texto del capítulo ha cambiado. Vuelve a abrirlo antes de explicar.
        </p>
      )}
      {explanation && matches && (
        <div className="mt-4 space-y-3 break-words text-sm">
          <h3 className="font-semibold">Traducción contextual</h3>
          <p
            className="text-base font-semibold"
            data-testid="contextual-translation"
          >
            {explanation.contextual_translation}
          </p>
          {explanation.meaning_explanation !== null && (
            <p>{explanation.meaning_explanation}</p>
          )}
          {explanation.grammar_explanation !== null && (
            <div>
              <h3 className="font-semibold">Gramática</h3>
              <p>{explanation.grammar_explanation}</p>
            </div>
          )}
          {explanation.sentence_translation !== null && (
            <div>
              <h3 className="font-semibold">Traducción de la oración</h3>
              <p>{explanation.sentence_translation}</p>
            </div>
          )}
          {explanation.uncertainty_note !== null && (
            <p className="rounded border p-2">{explanation.uncertainty_note}</p>
          )}
          <p className="text-xs text-muted-foreground">
            Explicación generada por IA; puede contener errores.
          </p>
          <LoadingButton
            loading={save.isPending}
            disabled={save.isSuccess}
            onClick={() =>
              save.mutate({
                chapter_id: selection.chapterId,
                original_text: selection.text,
                contextual_translation: explanation.contextual_translation,
                context: selection.context,
                start_offset: selection.startOffset,
                end_offset: selection.endOffset,
                context_start_offset: selection.contextStartOffset,
                context_end_offset: selection.contextEndOffset,
                offset_unit: "utf-16",
              })
            }
          >
            {save.isSuccess ? "Palabra guardada" : "Guardar palabra"}
          </LoadingButton>
          {save.isError && (
            <p role="alert">{extractErrorMessage(save.error)}</p>
          )}
        </div>
      )}
    </section>
  )
}
