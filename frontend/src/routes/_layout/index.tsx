import { createFileRoute } from "@tanstack/react-router"

export const Route = createFileRoute("/_layout/")({
  component: Library,
  head: () => ({ meta: [{ title: "Mi biblioteca - Chill-Lang" }] }),
})

function Library() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-bold tracking-tight">Mi biblioteca</h1>
      <div className="rounded-lg border p-8 text-center">
        <h2 className="text-lg font-semibold">Todavía no tienes libros</h2>
        <p className="mt-2 text-muted-foreground">
          Pronto podrás importar libros en francés y empezar a leer.
        </p>
      </div>
    </div>
  )
}
