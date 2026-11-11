import { expect, test } from "@playwright/test"

test("Library shows the empty state without demo navigation", async ({ page }) => {
  await page.goto("/")
  await expect(page).toHaveTitle("Mi biblioteca - Chill-Lang")
  await expect(
    page.getByRole("heading", { name: "Mi biblioteca", exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole("heading", { name: "Todavía no tienes libros" }),
  ).toBeVisible()
  await expect(
    page.getByText("Pronto podrás importar libros en francés y empezar a leer."),
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
