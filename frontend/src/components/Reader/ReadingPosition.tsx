import { useQueryClient } from "@tanstack/react-query"
import { type RefObject, useEffect, useState } from "react"
import { type ReadingProgressPublic, ReadingService } from "@/client"
import useAuth from "@/hooks/useAuth"
import { useReadingProgress } from "@/hooks/useReadingState"
import { extractErrorMessage } from "@/utils"

export function ReadingPosition(props: {
  root: RefObject<HTMLDivElement | null>
  content: string
  bookId: string
  chapterId: string
}) {
  const progress = useReadingProgress(props.bookId)
  if (progress.isError)
    return (
      <p role="alert">
        No se ha podido recuperar el progreso.{" "}
        <button
          type="button"
          className="underline"
          onClick={() => progress.refetch()}
        >
          Reintentar
        </button>
      </p>
    )
  // Wait for a fresh response, never initialize from a stale cache entry.
  if (!progress.isFetchedAfterMount || !progress.isSuccess)
    return <p role="status">Recuperando progreso…</p>
  return <PositionTracker {...props} initial={progress.data} />
}

function PositionTracker({
  root,
  content,
  bookId,
  chapterId,
  initial,
}: {
  root: RefObject<HTMLDivElement | null>
  content: string
  bookId: string
  chapterId: string
  initial: ReadingProgressPublic | null
}) {
  const [snapshot] = useState(initial)
  const [message, setMessage] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const ownerId = user?.id
  useEffect(() => {
    let disposed = false
    let ready = false
    let blocked = false
    let userMoved = false
    let sending = false
    let pending: number | null = null
    let version = snapshot?.version ?? 0
    let hash = ""
    let lastPosition =
      snapshot?.chapter_id === chapterId ? snapshot.position : -1
    let timer: ReturnType<typeof setTimeout> | undefined
    const node = root.current?.firstChild
    if (!node) return
    const boundary = (position: number) =>
      position > 0 && /[\uDC00-\uDFFF]/.test(content[position] ?? "")
        ? position - 1
        : position
    const rectAt = (position: number) => {
      const range = document.createRange()
      range.setStart(node, position)
      range.setEnd(node, Math.min(content.length, position + 1))
      return range.getBoundingClientRect()
    }
    const visiblePosition = () => {
      let low = 0
      let high = content.length - 1
      while (low < high) {
        const middle = Math.floor((low + high) / 2)
        if (rectAt(middle).bottom < 100) low = middle + 1
        else high = middle
      }
      return boundary(low)
    }
    const flush = async () => {
      if (!ready || blocked || sending || pending === null) return
      const position = pending
      pending = null
      sending = true
      try {
        const { data } = await ReadingService.saveProgress({
          path: { book_id: bookId },
          body: {
            chapter_id: chapterId,
            position,
            content_hash: hash,
            expected_version: version,
            offset_unit: "utf-16",
          },
        })
        version = data.version
        lastPosition = position
        // A response from a departed chapter must not replace a newer cache entry.
        queryClient.setQueryData<ReadingProgressPublic | null>(
          ["progress", ownerId, bookId],
          (old) => (!old || old.version <= data.version ? data : old),
        )
      } catch (error) {
        blocked = true
        if (!disposed)
          setMessage(
            `No se ha guardado el progreso. ${extractErrorMessage(error instanceof Error ? error : new Error("Error de conexión"))}`,
          )
      } finally {
        sending = false
        if (pending !== null) void flush()
      }
    }
    const capture = () => {
      if (!ready || blocked || !userMoved) return
      const position = visiblePosition()
      if (position === lastPosition && pending === null) return
      pending = position
      clearTimeout(timer)
      timer = setTimeout(() => {
        userMoved = false
        void flush()
      }, 900)
    }
    const markUserMovement = (event: Event) => {
      if (
        event instanceof PointerEvent &&
        !root.current?.contains(event.target as Node) &&
        event.target !== document.documentElement
      )
        return
      if (
        event instanceof KeyboardEvent &&
        ![
          "ArrowDown",
          "ArrowUp",
          "PageDown",
          "PageUp",
          "Home",
          "End",
          " ",
        ].includes(event.key)
      )
        return
      if (ready) {
        userMoved = true
        // Also records deliberate interaction in short chapters that cannot scroll.
        requestAnimationFrame(capture)
      }
    }
    const onHidden = () => {
      if (document.visibilityState === "hidden") {
        clearTimeout(timer)
        void flush()
      }
    }
    const start = async () => {
      hash = Array.from(
        new Uint8Array(
          await crypto.subtle.digest(
            "SHA-256",
            new TextEncoder().encode(content),
          ),
        ),
        (byte) => byte.toString(16).padStart(2, "0"),
      ).join("")
      await document.fonts.ready
      if (disposed) return
      if (snapshot?.chapter_id === chapterId) {
        if (
          snapshot.content_hash !== hash ||
          snapshot.position > content.length ||
          boundary(snapshot.position) !== snapshot.position
        ) {
          blocked = true
          setMessage(
            "El capítulo ha cambiado. Se conserva el progreso anterior; no se restaurará una posición incorrecta.",
          )
        } else if (snapshot.position > 0) {
          window.scrollBy({
            top: rectAt(snapshot.position).top - 100,
            behavior: "instant",
          })
        }
      }
      requestAnimationFrame(() => {
        if (!disposed) ready = true
      })
    }
    void start().catch(() => {
      if (!disposed)
        setMessage("No se ha podido preparar el guardado del progreso.")
    })
    window.addEventListener("scroll", capture, { passive: true })
    window.addEventListener("wheel", markUserMovement, { passive: true })
    window.addEventListener("touchmove", markUserMovement, { passive: true })
    window.addEventListener("pointerdown", markUserMovement, { passive: true })
    window.addEventListener("keydown", markUserMovement)
    document.addEventListener("visibilitychange", onHidden)
    return () => {
      disposed = true
      clearTimeout(timer)
      void flush()
      window.removeEventListener("scroll", capture)
      window.removeEventListener("wheel", markUserMovement)
      window.removeEventListener("touchmove", markUserMovement)
      window.removeEventListener("pointerdown", markUserMovement)
      window.removeEventListener("keydown", markUserMovement)
      document.removeEventListener("visibilitychange", onHidden)
    }
  }, [root, content, bookId, chapterId, snapshot, ownerId, queryClient])
  return message ? <p role="alert">{message}</p> : null
}
