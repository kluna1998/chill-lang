import { useEffect } from "react"

import { Button } from "@/components/ui/button"
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
      <p className="mt-4 text-sm text-muted-foreground">
        Las explicaciones lingüísticas estarán disponibles en una fase
        posterior.
      </p>
    </aside>
  )
}
