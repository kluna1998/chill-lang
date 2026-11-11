import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"

import { type BookPublic, BooksService } from "@/client"
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
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

export function DeleteBook({
  book,
  onDeleted,
}: {
  book: BookPublic
  onDeleted: () => void
}) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const mutation = useMutation({
    mutationFn: () => BooksService.deleteBook({ path: { book_id: book.id } }),
    onSuccess: () => {
      showSuccessToast("Libro eliminado")
      setOpen(false)
      onDeleted()
      queryClient.invalidateQueries({ queryKey: ["books"] })
    },
    onError: handleError.bind(showErrorToast),
  })
  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!mutation.isPending) setOpen(nextOpen)
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline">Eliminar libro</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Eliminar libro</DialogTitle>
          <DialogDescription>
            Se eliminará «{book.title}» de tu biblioteca. Esta acción no se
            puede deshacer.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline" disabled={mutation.isPending}>
              Cancelar
            </Button>
          </DialogClose>
          <LoadingButton
            variant="destructive"
            loading={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            Eliminar
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
