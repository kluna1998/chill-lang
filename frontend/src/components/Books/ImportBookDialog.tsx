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
      BooksService.importTxtBook({ body: { file: selected } }),
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
        <Button>Importar TXT</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Importar TXT</DialogTitle>
          <DialogDescription>
            Archivo UTF-8 de hasta 5 MiB. Incluye TITLE:, AUTHOR: opcional y
            capítulos con === CHAPTER: Nombre ===.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(event) => {
            event.preventDefault()
            if (!file) return
            if (!file.name.toLowerCase().endsWith(".txt")) {
              showErrorToast("Selecciona un archivo .txt.")
              return
            }
            if (file.size > 5 * 1024 * 1024) {
              showErrorToast("El archivo supera el límite de 5 MiB.")
              return
            }
            mutation.mutate(file)
          }}
        >
          <div className="grid gap-3 py-4">
            <Label htmlFor="book-txt">Archivo TXT</Label>
            <Input
              id="book-txt"
              type="file"
              accept=".txt,text/plain"
              required
              disabled={mutation.isPending}
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
            {file && <p className="break-words text-sm">{file.name}</p>}
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
