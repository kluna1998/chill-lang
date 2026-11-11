import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { BooksService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

export function ImportBookDialog({ onImported }: { onImported: () => void }) {
  const [open, setOpen] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const mutation = useMutation({
    mutationFn: (selected: File) =>
      selected.name.toLowerCase().endsWith(".epub")
        ? BooksService.importEpubBook({ body: { file: selected } })
        : BooksService.importTxtBook({ body: { file: selected } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["books"] })
      onImported()
      showSuccessToast("Libro importado")
      setFile(null)
      setOpen(false)
    },
    onError: handleError.bind(showErrorToast),
  })
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (mutation.isPending) return
        setOpen(next)
        if (!next) {
          setFile(null)
          mutation.reset()
        }
      }}
    >
      <DialogTrigger asChild>
        <Button>Importar libro</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Importar libro</DialogTitle>
          <DialogDescription>
            EPUB sin DRM de hasta 20 MiB o TXT UTF-8 de hasta 5 MiB. Los TXT
            deben incluir TITLE: y capítulos con === CHAPTER: Nombre ===.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            if (!file) return
            const extension = file.name.toLowerCase().split(".").pop()
            if (extension !== "txt" && extension !== "epub") {
              showErrorToast("Selecciona un archivo .txt o .epub.")
              return
            }
            const maxMiB = extension === "epub" ? 20 : 5
            if (file.size > maxMiB * 1024 * 1024) {
              showErrorToast(`El archivo supera el límite de ${maxMiB} MiB.`)
              return
            }
            mutation.mutate(file)
          }}
        >
          <div className="grid gap-3 py-4">
            <Label htmlFor="book-file">Archivo del libro</Label>
            <Input
              id="book-file"
              type="file"
              accept=".txt,.epub,text/plain,application/epub+zip"
              required
              disabled={mutation.isPending}
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
            {file && (
              <>
                <p className="break-words text-sm">{file.name}</p>
                <p className="text-sm text-muted-foreground">
                  Formato:{" "}
                  {file.name.toLowerCase().endsWith(".epub")
                    ? "EPUB"
                    : file.name.toLowerCase().endsWith(".txt")
                      ? "TXT"
                      : "No admitido"}
                </p>
              </>
            )}
            {mutation.isPending && <p role="status">Importando libro…</p>}
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline" disabled={mutation.isPending}>
                Cancelar
              </Button>
            </DialogClose>
            <LoadingButton
              type="submit"
              disabled={!file}
              loading={mutation.isPending}
            >
              Importar
            </LoadingButton>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
