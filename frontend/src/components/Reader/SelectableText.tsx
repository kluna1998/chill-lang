import type { CSSProperties } from "react"
import { useEffect, useRef } from "react"
import { ReadingPosition } from "./ReadingPosition"
import { extractTextSelection, type TextSelectionContext } from "./selection"

export function SelectableText({
  content,
  bookId,
  chapterId,
  onSelect,
  style,
}: {
  content: string
  bookId: string
  chapterId: string
  onSelect: (selection: TextSelectionContext) => void
  style?: CSSProperties
}) {
  const root = useRef<HTMLDivElement>(null)
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>
    const capture = () => {
      clearTimeout(timer)
      timer = setTimeout(() => {
        if (!root.current) return
        const selected = extractTextSelection(
          root.current,
          content,
          bookId,
          chapterId,
          document.getSelection(),
        )
        if (selected) onSelect(selected)
      }, 180)
    }
    document.addEventListener("selectionchange", capture)
    return () => {
      clearTimeout(timer)
      document.removeEventListener("selectionchange", capture)
    }
  }, [content, bookId, chapterId, onSelect])

  return (
    <>
      <ReadingPosition
        root={root}
        content={content}
        bookId={bookId}
        chapterId={chapterId}
      />
      <div
        ref={root}
        data-testid="chapter-content"
        className="whitespace-pre-wrap break-words select-text"
        style={style}
      >
        {content}
      </div>
    </>
  )
}
