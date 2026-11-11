import { expect, test } from "@playwright/test"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test.use({ storageState: { cookies: [], origins: [] } })

test("Real TXT import, NLP, vocabulary and progress with only AI generation simulated", async ({
  page,
}) => {
  const email = randomEmail()
  const password = randomPassword()
  await createUser({ email, password })
  await logInUser(page, email, password)
  let aiCalls = 0
  // The provider is simulated; every other request reaches the real API/database.
  await page.route("**/api/v1/books/*/chapters/*/explain", (route) => {
    aiCalls++
    return route.fulfill({
      json: {
        selected_text: "maison",
        explanation: {
          contextual_translation: "casa",
          meaning_explanation: null,
          grammar_explanation: null,
          sentence_translation: null,
          uncertainty_note: null,
        },
      },
    })
  })
  await page.getByRole("button", { name: "Importar libro" }).click()
  const dialog = page.getByRole("dialog")
  await dialog.getByLabel("Archivo del libro").setInputFiles({
    name: "integration.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(
      `TITLE: Intégration\n\n=== CHAPTER: Premier ===\n${"😀 La maison est grande.\n\n".repeat(250)}`,
    ),
  })
  await dialog.getByRole("button", { name: "Importar", exact: true }).click()
  await expect(dialog).not.toBeVisible()
  await page.getByRole("link", { name: "Abrir libro" }).click()
  await page.getByRole("link", { name: "1. Premier", exact: true }).click()
  const content = page.getByTestId("chapter-content")
  await expect(content).toContainText("😀 La maison est grande.")
  await content.evaluate((root) => {
    const start = root.textContent!.indexOf("maison")
    const range = document.createRange()
    range.setStart(root.firstChild!, start)
    range.setEnd(root.firstChild!, start + 6)
    document.getSelection()!.removeAllRanges()
    document.getSelection()!.addRange(range)
  })
  await expect(page.getByTestId("selected-text")).toHaveText("maison")
  await page.getByRole("button", { name: "Analizar selección" }).click()
  await expect(page.getByText("Lema: maison", { exact: true })).toBeVisible()
  const vocabularySave = page.waitForResponse(
    (response) =>
      response.url().endsWith("/vocabulary/") &&
      response.request().method() === "POST",
  )
  await page.getByRole("button", { name: "Guardar palabra" }).click()
  const saved = await vocabularySave
  expect(saved.status()).toBe(200)
  expect((await saved.json()).contextual_translation).toBeNull()
  expect(aiCalls).toBe(0)
  await expect(
    page.getByRole("button", { name: "Palabra guardada" }),
  ).toBeDisabled()
  await page.getByRole("button", { name: "Explicar con IA" }).click()
  await expect(page.getByTestId("contextual-translation")).toHaveText("casa")
  const translationUpdate = page.waitForResponse(
    (response) =>
      response.url().includes("/vocabulary/") &&
      response.request().method() === "PATCH",
  )
  await page
    .getByRole("button", { name: "Actualizar traducción", exact: true })
    .click()
  const updated = await translationUpdate
  expect(updated.status()).toBe(200)
  expect((await updated.json()).contextual_translation).toBe("casa")
  await expect(
    page.getByRole("button", { name: "Palabra guardada" }),
  ).toBeDisabled()
  expect(aiCalls).toBe(1)
  await page.getByRole("button", { name: "Cerrar panel contextual" }).click()
  const progressSave = page.waitForResponse(
    (response) =>
      response.url().endsWith("/progress") &&
      response.request().method() === "PUT",
  )
  await page.mouse.wheel(0, 900)
  const progress = await progressSave
  expect(progress.status()).toBe(200)
  expect((await progress.json()).position).toBeGreaterThan(0)
  await page.reload()
  await expect
    .poll(() => page.evaluate(() => window.scrollY))
    .toBeGreaterThan(400)
  await page.getByRole("link", { name: "Mi vocabulario", exact: true }).click()
  await expect(page.getByText("maison — casa", { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "Eliminar maison" }).click()
  await expect(
    page.getByText("Todavía no has guardado palabras."),
  ).toBeVisible()
})
