import { expect, test } from "@playwright/test"

const bookId = "00000000-0000-4000-8000-000000000010"
const ownerId = "00000000-0000-4000-8000-000000000001"
const book = {
  id: bookId,
  owner_id: ownerId,
  title: "Le Petit Prince",
  author: "Antoine de Saint-Exupéry",
  created_at: "2026-01-01T00:00:00Z",
}
const chapters = [1, 4, 8].map((position, index) => ({
  id: `00000000-0000-4000-8000-${String(index + 20).padStart(12, "0")}`,
  book_id: bookId,
  position,
  title: `Chapitre ${position}`,
  content: `Première ligne ${position}.\n\nDeuxième ligne.\n<script>unsafe()</script>`,
}))
const summary = ({
  id,
  book_id,
  title,
  position,
}: (typeof chapters)[number]) => ({ id, book_id, title, position })
const bookPath = `/books/${bookId}`
const chapterPath = (index: number) =>
  `${bookPath}/chapters/${chapters[index].id}`

test.use({ storageState: { cookies: [], origins: [] } })
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem("access_token", "test-token"),
  )
  await page.route("**/api/v1/users/me", (route) =>
    route.fulfill({
      json: {
        id: ownerId,
        email: "reader@example.com",
        full_name: "Reader",
        is_active: true,
        is_superuser: false,
      },
    }),
  )
  await page.route("**/api/v1/books/**", (route) => {
    expect(route.request().headers().authorization).toBe("Bearer test-token")
    const path = new URL(route.request().url()).pathname
    if (path === "/api/v1/books/")
      return route.fulfill({ json: { data: [book], count: 1 } })
    if (path === `/api/v1/books/${bookId}`) return route.fulfill({ json: book })
    if (path === `/api/v1/books/${bookId}/chapters`)
      return route.fulfill({
        json: {
          data: [chapters[2], chapters[0], chapters[1]].map(summary),
          count: 3,
        },
      })
    const chapter = chapters.find(
      (entry) => path === `/api/v1/books/${bookId}/chapters/${entry.id}`,
    )
    return chapter
      ? route.fulfill({ json: chapter })
      : route.fulfill({ status: 404, json: { detail: "Chapter not found" } })
  })
})

test("Book index and reader share ordered chapters and cached navigation", async ({
  page,
}) => {
  let indexRequests = 0
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.endsWith(`/${bookId}/chapters`))
      indexRequests++
  })
  await page.goto("/")
  await page.getByRole("link", { name: "Abrir libro" }).click()
  await expect(page.getByRole("heading", { name: book.title })).toBeVisible()
  await expect(page.getByText(book.author, { exact: true })).toBeVisible()
  await expect(
    page.getByRole("list", { name: "Capítulos" }).getByRole("link"),
  ).toHaveText(["1. Chapitre 1", "4. Chapitre 4", "8. Chapitre 8"])
  await page.getByRole("link", { name: "1. Chapitre 1", exact: true }).click()
  await expect(page).toHaveURL(chapterPath(0))
  const text = page.locator("article > div")
  await expect(text).toHaveText(chapters[0].content)
  await expect(text).toHaveCSS("white-space", "pre-wrap")
  await expect(page.locator("article script")).toHaveCount(0)
  await expect(
    page.getByRole("button", { name: "Anterior", exact: true }),
  ).toBeDisabled()
  await page.getByRole("link", { name: "Siguiente", exact: true }).click()
  await expect(
    page.getByRole("heading", { name: "Chapitre 4", exact: true }),
  ).toBeVisible()
  await page.getByRole("link", { name: "Siguiente", exact: true }).click()
  await expect(
    page.getByRole("heading", { name: "Chapitre 8", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole("button", { name: "Siguiente", exact: true }),
  ).toBeDisabled()
  await page.getByRole("link", { name: "Anterior", exact: true }).click()
  await expect(page).toHaveURL(chapterPath(1))
  await page.getByRole("link", { name: "Volver al libro", exact: true }).click()
  await expect(
    page.getByRole("heading", { name: "Índice de capítulos" }),
  ).toBeVisible()
  expect(indexRequests).toBe(1)
})

test("Chapter URL works directly and after reload", async ({ page }) => {
  await page.goto(chapterPath(1))
  await expect(
    page.getByRole("heading", { name: "Chapitre 4", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole("link", { name: "Anterior", exact: true }),
  ).toHaveAttribute("href", chapterPath(0))
  await expect(
    page.getByRole("link", { name: "Siguiente", exact: true }),
  ).toHaveAttribute("href", chapterPath(2))
  await page.reload()
  await expect(
    page.getByRole("heading", { name: "Chapitre 4", exact: true }),
  ).toBeVisible()
})

test("Empty book shows an empty index", async ({ page }) => {
  await page.route(`**/api/v1/books/${bookId}/chapters?*`, (route) =>
    route.fulfill({ json: { data: [], count: 0 } }),
  )
  await page.goto(bookPath)
  await expect(
    page.getByText("Este libro todavía no tiene capítulos."),
  ).toBeVisible()
  await expect(page.getByRole("list", { name: "Capítulos" })).toHaveCount(0)
})

test("Private or missing book shows a 404 state", async ({ page }) => {
  await page.route(`**/api/v1/books/${bookId}`, (route) =>
    route.fulfill({ status: 404, json: { detail: "Book not found" } }),
  )
  await page.goto(bookPath)
  await expect(page.getByRole("alert")).toContainText("Libro no encontrado.")
  await expect(page.getByRole("heading", { name: book.title })).toHaveCount(0)
  await expect(page.getByRole("list", { name: "Capítulos" })).toHaveCount(0)
})

test("Missing chapter does not display the previous chapter content", async ({
  page,
}) => {
  await page.route(
    `**/api/v1/books/${bookId}/chapters/${chapters[1].id}`,
    (route) =>
      route.fulfill({ status: 404, json: { detail: "Chapter not found" } }),
  )
  await page.goto(chapterPath(0))
  await expect(page.locator("article")).toBeVisible()
  await page.getByRole("link", { name: "Siguiente", exact: true }).click()
  await expect(page.getByRole("alert")).toContainText("Capítulo no encontrado.")
  await expect(page.locator("article")).toHaveCount(0)
  await expect(
    page.getByRole("link", { name: "Volver al libro" }),
  ).toBeVisible()
})

test("Index and navigation include chapters beyond the first API page", async ({
  page,
}) => {
  const entries = Array.from({ length: 101 }, (_, index) => ({
    id: `00000000-0000-4000-8000-${String(index + 100).padStart(12, "0")}`,
    book_id: bookId,
    position: index + 1,
    title: `Chapter ${index + 1}`,
    content: "Text",
  }))
  await page.route(`**/api/v1/books/${bookId}/chapters?*`, (route) => {
    const query = new URL(route.request().url()).searchParams
    expect(query.get("limit")).toBe("100")
    const skip = Number(query.get("skip"))
    return route.fulfill({
      json: { data: entries.slice(skip, skip + 100).map(summary), count: 101 },
    })
  })
  await page.route(
    `**/api/v1/books/${bookId}/chapters/${entries[100].id}`,
    (route) => route.fulfill({ json: entries[100] }),
  )
  await page.goto(bookPath)
  await expect(
    page.getByRole("list", { name: "Capítulos" }).getByRole("link"),
  ).toHaveCount(101)
  await page
    .getByRole("link", { name: "101. Chapter 101", exact: true })
    .click()
  await expect(
    page.getByRole("heading", { name: "Chapter 101", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole("link", { name: "Anterior", exact: true }),
  ).toHaveAttribute("href", `${bookPath}/chapters/${entries[99].id}`)
  await expect(
    page.getByRole("button", { name: "Siguiente", exact: true }),
  ).toBeDisabled()
})

test("Index errors preserve reading and allow retry", async ({ page }) => {
  let fail = true
  await page.route(`**/api/v1/books/${bookId}/chapters?*`, (route) =>
    fail
      ? route.fulfill({ status: 500, json: { detail: "Unavailable" } })
      : route.fulfill({
          json: { data: chapters.map(summary), count: chapters.length },
        }),
  )
  await page.goto(chapterPath(0))
  await expect(page.locator("article")).toBeVisible()
  await expect(page.getByRole("alert")).toContainText(
    "No se ha podido cargar la navegación",
    { timeout: 15000 },
  )
  fail = false
  await page.getByRole("button", { name: "Reintentar índice" }).click()
  await expect(
    page.getByRole("link", { name: "Siguiente", exact: true }),
  ).toBeVisible()
})

test("Book and chapter routes remain protected", async ({ page }) => {
  await page.addInitScript(() => localStorage.removeItem("access_token"))
  await page.goto(bookPath)
  await expect(page).toHaveURL("/login")
  await page.goto(chapterPath(0))
  await expect(page).toHaveURL("/login")
})
