import { expect, test } from "@playwright/test"

test.use({ storageState: { cookies: [], origins: [] } })

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem("access_token", "test-token"),
  )
  await page.route("**/api/v1/users/me", (route) =>
    route.fulfill({
      json: {
        id: "00000000-0000-4000-8000-000000000001",
        email: "reader@example.com",
        full_name: "Reader",
        is_active: true,
        is_superuser: false,
      },
    }),
  )
  await page.route("**/api/v1/books/**", (route) =>
    route.fulfill({ json: { data: [], count: 0 } }),
  )
})

test("Library shows the empty state without demo navigation", async ({
  page,
}) => {
  await page.goto("/")
  await expect(page).toHaveTitle("Mi biblioteca - Chill-Lang")
  await expect(
    page.getByRole("heading", { name: "Mi biblioteca", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole("heading", { name: "Todavía no tienes libros" }),
  ).toBeVisible()
  await expect(
    page.getByText(
      "Añade un libro con su título y autor para empezar tu biblioteca.",
    ),
  ).toBeVisible()
  await expect(
    page.getByRole("link", { name: "Items", exact: true }),
  ).toHaveCount(0)
  await expect(
    page.getByRole("link", { name: "Dashboard", exact: true }),
  ).toHaveCount(0)
})

test("Old Items URL redirects to the library", async ({ page }) => {
  await page.goto("/items")
  await expect(page).toHaveURL("/")
  await expect(
    page.getByRole("heading", { name: "Mi biblioteca", exact: true }),
  ).toBeVisible()
})

test("Account remains accessible from the user menu", async ({ page }) => {
  await page.goto("/")
  await page.getByTestId("user-menu").click()
  await page.getByRole("menuitem", { name: "Mi cuenta" }).click()
  await expect(page).toHaveURL("/settings")
  await expect(page.getByRole("tab", { name: "My profile" })).toBeVisible()
})

test("Books can be created, edited and deleted through the API", async ({
  page,
}) => {
  const ownerId = "00000000-0000-4000-8000-000000000001"
  const bookId = "00000000-0000-4000-8000-000000000002"
  let book: {
    id: string
    owner_id: string
    title: string
    author: string | null
    created_at: string
  } | null = null
  await page.route("**/api/v1/books/**", async (route) => {
    const request = route.request()
    expect(request.headers().authorization).toBe("Bearer test-token")
    const url = new URL(request.url())
    if (request.method() === "GET") {
      expect(url.searchParams.get("skip")).toBe("0")
      expect(url.searchParams.get("limit")).toBe("20")
      return route.fulfill({
        json: { data: book ? [book] : [], count: book ? 1 : 0 },
      })
    }
    if (request.method() === "POST") {
      expect(url.pathname).toBe("/api/v1/books/")
      expect(request.postDataJSON()).toEqual({
        title: "Le Petit Prince",
        author: "Antoine de Saint-Exupéry",
      })
      book = {
        ...request.postDataJSON(),
        id: bookId,
        owner_id: ownerId,
        created_at: new Date().toISOString(),
      }
      return route.fulfill({ status: 201, json: book })
    }
    expect(url.pathname).toBe(`/api/v1/books/${bookId}`)
    if (request.method() === "PATCH") {
      expect(request.postDataJSON()).toEqual({
        title: "Titre modifié",
        author: null,
      })
      book = { ...book!, ...request.postDataJSON() }
      return route.fulfill({ json: book })
    }
    expect(request.method()).toBe("DELETE")
    book = null
    return route.fulfill({ json: { message: "Book deleted successfully" } })
  })
  await page.goto("/")
  await page.getByRole("button", { name: "Añadir libro" }).click()
  let dialog = page.getByRole("dialog")
  await dialog.getByLabel("Título", { exact: true }).fill("Le Petit Prince")
  await dialog.getByLabel("Autor (opcional)").fill("Antoine de Saint-Exupéry")
  await dialog.getByRole("button", { name: "Guardar" }).click()
  await expect(
    page.getByRole("heading", { name: "Le Petit Prince" }),
  ).toBeVisible()
  await page.getByRole("button", { name: "Editar libro" }).click()
  dialog = page.getByRole("dialog")
  await expect(dialog.getByLabel("Título", { exact: true })).toHaveValue(
    "Le Petit Prince",
  )
  await dialog.getByLabel("Título", { exact: true }).fill("Titre modifié")
  await dialog.getByLabel("Autor (opcional)").fill("")
  await dialog.getByRole("button", { name: "Guardar" }).click()
  await expect(
    page.getByRole("heading", { name: "Titre modifié" }),
  ).toBeVisible()
  await expect(page.getByText("Sin autor", { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "Eliminar libro" }).click()
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Cancelar" })
    .click()
  await expect(
    page.getByRole("heading", { name: "Titre modifié" }),
  ).toBeVisible()
  await page.getByRole("button", { name: "Eliminar libro" }).click()
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Eliminar", exact: true })
    .click()
  await expect(
    page.getByRole("heading", { name: "Todavía no tienes libros" }),
  ).toBeVisible()
})

test("A failed creation keeps the form open and preserves the input", async ({
  page,
}) => {
  await page.route("**/api/v1/books/", (route) =>
    route.fulfill({ status: 422, json: { detail: "Título no válido" } }),
  )
  await page.goto("/")
  await page.getByRole("button", { name: "Añadir libro" }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel("Título", { exact: true }).fill("Livre")
  await dialog.getByRole("button", { name: "Guardar" }).click()
  await expect(
    page.getByText("Título no válido", { exact: true }),
  ).toBeVisible()
  await expect(dialog.getByLabel("Título", { exact: true })).toHaveValue(
    "Livre",
  )
})

test("Library pagination requests the next page", async ({ page }) => {
  await page.route("**/api/v1/books/**", (route) => {
    const skip = Number(new URL(route.request().url()).searchParams.get("skip"))
    return route.fulfill({
      json: {
        count: 21,
        data: [
          {
            id: `book-${skip}`,
            title: skip === 0 ? "First page" : "Second page",
            author: null,
            owner_id: "owner",
            created_at: new Date().toISOString(),
          },
        ],
      },
    })
  })
  await page.goto("/")
  await expect(page.getByRole("heading", { name: "First page" })).toBeVisible()
  await expect(page.getByRole("button", { name: "Anterior" })).toBeDisabled()
  await page.getByRole("button", { name: "Siguiente" }).click()
  await expect(page.getByRole("heading", { name: "Second page" })).toBeVisible()
  await expect(page.getByRole("button", { name: "Siguiente" })).toBeDisabled()
  await page.getByRole("button", { name: "Anterior" }).click()
  await expect(page.getByRole("heading", { name: "First page" })).toBeVisible()
})

test("Library errors can be retried", async ({ page }) => {
  let fail = true
  await page.route("**/api/v1/books/**", (route) =>
    fail
      ? route.fulfill({ status: 500, json: { detail: "Unavailable" } })
      : route.fulfill({ json: { data: [], count: 0 } }),
  )
  await page.goto("/")
  await expect(
    page.getByRole("status").filter({ hasText: "Cargando libros" }),
  ).toBeVisible()
  await expect(page.getByRole("alert")).toContainText(
    "No se ha podido cargar tu biblioteca.",
    { timeout: 15000 },
  )
  await expect(
    page.getByRole("heading", { name: "Todavía no tienes libros" }),
  ).toHaveCount(0)
  fail = false
  await page.getByRole("button", { name: "Reintentar" }).click()
  await expect(
    page.getByRole("heading", { name: "Todavía no tienes libros" }),
  ).toBeVisible()
})
