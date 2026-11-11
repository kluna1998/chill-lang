/** Offsets are half-open JavaScript UTF-16 code-unit positions in original content. */
export interface TextSelectionContext {
  bookId: string
  chapterId: string
  text: string
  context: string
  startOffset: number
  endOffset: number
  contextStartOffset: number
  contextEndOffset: number
  offsetUnit: "utf-16"
}

export function getContextBounds(content: string, start: number, end: number) {
  let from = Math.max(0, start - 160)
  let to = Math.min(content.length, end + 160)
  const paragraphStart = content.lastIndexOf("\n\n", Math.max(0, start - 2))
  const paragraphEnd = content.indexOf("\n\n", end)
  if (paragraphStart >= from && paragraphStart + 2 <= start)
    from = paragraphStart + 2
  if (paragraphEnd >= end && paragraphEnd < to) to = paragraphEnd
  // Do not split surrogate pairs at the boundaries of the contextual window.
  if (
    from > 0 &&
    /[\uDC00-\uDFFF]/.test(content[from]) &&
    /[\uD800-\uDBFF]/.test(content[from - 1])
  )
    from--
  if (
    to < content.length &&
    /[\uD800-\uDBFF]/.test(content[to - 1]) &&
    /[\uDC00-\uDFFF]/.test(content[to])
  )
    to++
  return { from, to }
}

export function extractTextSelection(
  root: HTMLElement,
  content: string,
  bookId: string,
  chapterId: string,
  selection: Selection | null,
): TextSelectionContext | null {
  if (
    selection?.rangeCount !== 1 ||
    selection.isCollapsed ||
    root.textContent !== content
  )
    return null
  const range = selection.getRangeAt(0)
  if (
    !root.contains(range.startContainer) ||
    !root.contains(range.endContainer)
  )
    return null
  try {
    const prefix = root.ownerDocument.createRange()
    prefix.selectNodeContents(root)
    prefix.setEnd(range.startContainer, range.startOffset)
    const start = prefix.toString().length
    prefix.setEnd(range.endContainer, range.endOffset)
    const end = prefix.toString().length
    const text = content.slice(start, end)
    if (end <= start || !text.trim() || text !== range.toString()) return null
    const { from, to } = getContextBounds(content, start, end)
    return {
      bookId,
      chapterId,
      text,
      startOffset: start,
      endOffset: end,
      context: content.slice(from, to),
      contextStartOffset: from,
      contextEndOffset: to,
      offsetUnit: "utf-16",
    }
  } catch {
    // A detached or changing DOM range must not produce guessed offsets.
    return null
  }
}
