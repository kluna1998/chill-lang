import { createHash } from "node:crypto"
import { expect, type Page, test } from "@playwright/test"

const bookId = "00000000-0000-4000-8000-000000000010"
const chapterId = "00000000-0000-4000-8000-000000000020"
const nextId = "00000000-0000-4000-8000-000000000021"
const text = "😀 La maison est grande.\n\n".repeat(250)
const chapterPath = `/books/${bookId}/chapters/${chapterId}`
const hash = createHash("sha256").update(text).digest("hex")
const stored = {
  book_id: bookId,
  chapter_id: chapterId,
  position: 3000,
  content_hash: hash,
  version: 4,
  offset_unit: "utf-16",
  updated_at: "2026-01-01T00:00:00Z",
}
const translation = {
  selected_text: "maison",
  explanation: {
    contextual_translation: "casa",
    meaning_explanation: null,
    grammar_explanation: null,
    sentence_translation: null,
    uncertainty_note: null,
  },
}

test.use({ storageState: { cookies: [], origins: [] } })
test.beforeEach(async ({ page }) => {
  await page.addInitScript(() =>
    localStorage.setItem("access_token", "test-token"),
  )
  await page.route("**/api/v1/users/me", (route) =>
    route.fulfill({
      json: {
        id: "reader",
        email: "reader@example.com",
        is_active: true,
        is_superuser: false,
      },
    }),
  )
  await page.route("**/api/v1/books/**", (route) => {
    const path = new URL(route.request().url()).pathname
    const entries = [chapterId, nextId].map((id, index) => ({
      id,
      book_id: bookId,
      title: `Chapitre ${index + 1}`,
      position: index + 1,
    }))
    if (path.endsWith("/progress"))
      return route.fulfill({
        json:
          route.request().method() === "GET"
            ? null
            : { ...stored, ...route.request().postDataJSON(), version: 1 },
      })
    if (path.endsWith("/chapters"))
      return route.fulfill({ json: { data: entries, count: 2 } })
    if (path.endsWith(bookId))
      return route.fulfill({
        json: { id: bookId, title: "Mon livre", author: "Auteur" },
      })
    return route.fulfill({
      json: { ...entries[path.endsWith(nextId) ? 1 : 0], content: text },
    })
  })
})

async function selectMaison(page: Page) {
  await page.getByTestId("chapter-content").evaluate((root) => {
    const range = document.createRange()
    range.setStart(root.firstChild!, 6)
    range.setEnd(root.firstChild!, 12)
    document.getSelection()!.removeAllRanges()
    document.getSelection()!.addRange(range)
  })
  await expect(page.getByTestId("selected-text")).toHaveText("maison")
}

test("Saving reuses the translation, appears in vocabulary and can be deleted", async ({
  page,
}) => {
  let aiCalls = 0
  let entry: Record<string, unknown> | null = null
  await page.route("**/chapters/*/explain", (route) => {
    aiCalls++
    return route.fulfill({ json: translation })
  })
  await page.route("**/api/v1/vocabulary/**", (route) => {
    expect(route.request().headers().authorization).toBe("Bearer test-token")
    if (route.request().method() === "POST") {
      const body = route.request().postDataJSON()
      expect(body).toMatchObject({
        original_text: "maison",
        contextual_translation: "casa",
        chapter_id: chapterId,
        start_offset: 6,
        end_offset: 12,
        offset_unit: "utf-16",
      })
      entry = {
        ...body,
        id: "saved",
        book_id: bookId,
        context: "😀 La maison est grande.",
        created_at: "2026-01-01T00:00:00Z",
      }
      return route.fulfill({ json: entry })
    }
    if (route.request().method() === "DELETE") {
      entry = null
      return route.fulfill({ json: { message: "Deleted" } })
    }
    return route.fulfill({
      json: { data: entry ? [entry] : [], count: entry ? 1 : 0 },
    })
  })
  await page.goto(chapterPath)
  await selectMaison(page)
  await expect(
    page.getByRole("button", { name: "Guardar palabra" }),
  ).toBeEnabled()
  await page.getByRole("button", { name: "Explicar con IA" }).click()
  await expect(page.getByTestId("contextual-translation")).toHaveText("casa")
  await page.getByRole("button", { name: "Guardar palabra" }).click()
  await expect(
    page.getByRole("button", { name: "Palabra guardada" }),
  ).toBeDisabled()
  expect(aiCalls).toBe(1)
  await page.getByRole("link", { name: "Mi vocabulario", exact: true }).click()
  await expect(page.getByText("maison — casa", { exact: true })).toBeVisible()
  await expect(
    page.getByText("😀 La maison est grande.", { exact: true }),
  ).toBeVisible()
  await page.reload()
  await expect(page.getByText("maison — casa", { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "Eliminar maison" }).click()
  await expect(
    page.getByText("Todavía no has guardado palabras."),
  ).toBeVisible()
})

test("Vocabulary save errors can retry without another generation", async ({
  page,
}) => {
  let aiCalls = 0
  let saves = 0
  await page.route("**/chapters/*/explain", (route) => {
    aiCalls++
    return route.fulfill({ json: translation })
  })
  await page.route("**/api/v1/vocabulary/", (route) => {
    saves++
    return route.fulfill(
      saves === 1
        ? { status: 503, json: { detail: "Temporalmente no disponible" } }
        : { json: { id: "saved", contextual_translation: "casa" } },
    )
  })
  await page.goto(chapterPath)
  await selectMaison(page)
  await page.getByRole("button", { name: "Explicar con IA" }).click()
  await expect(page.getByTestId("contextual-translation")).toHaveText("casa")
  await page.getByRole("button", { name: "Guardar palabra" }).click()
  await expect(page.getByRole("alert")).toHaveText(
    "Temporalmente no disponible",
  )
  await page.getByRole("button", { name: "Guardar palabra" }).click()
  await expect(
    page.getByRole("button", { name: "Palabra guardada" }),
  ).toBeDisabled()
  expect(aiCalls).toBe(1)
  expect(saves).toBe(2)
})

for (const aiState of ["not requested", "pending", "disabled", "failed"]) {
  test(`Saving without translation works when AI is ${aiState}`, async ({
    page,
  }) => {
    let aiCalls = 0
    let saves = 0
    let release!: () => void
    const gate = new Promise<void>((resolve) => {
      release = resolve
    })
    await page.route("**/chapters/*/explain", async (route) => {
      aiCalls++
      if (aiState === "pending") await gate
      return route.fulfill({
        status: aiState === "disabled" ? 503 : 502,
        json: { detail: "IA no disponible" },
      })
    })
    await page.route("**/api/v1/vocabulary/", (route) => {
      saves++
      const body = route.request().postDataJSON()
      expect(body).toMatchObject({
        original_text: "maison",
        contextual_translation: null,
        chapter_id: chapterId,
        start_offset: 6,
        end_offset: 12,
        offset_unit: "utf-16",
      })
      expect(body.context).toContain("maison")
      return route.fulfill({ json: { ...body, id: "saved" } })
    })
    await page.goto(chapterPath)
    await selectMaison(page)
    await expect(
      page.getByRole("button", { name: "Guardar palabra" }),
    ).toBeEnabled()
    if (aiState !== "not requested") {
      await page.getByRole("button", { name: "Explicar con IA" }).click()
      if (aiState === "pending")
        await expect(page.getByText("Preparando explicación…")).toBeVisible()
      else await expect(page.getByRole("alert")).toHaveText("IA no disponible")
    }
    await page.getByRole("button", { name: "Guardar palabra" }).click()
    await expect(
      page.getByRole("button", { name: "Palabra guardada" }),
    ).toBeDisabled()
    expect(saves).toBe(1)
    expect(aiCalls).toBe(aiState === "not requested" ? 0 : 1)
    release()
    if (aiState === "pending")
      await expect(page.getByRole("alert")).toHaveText("IA no disponible")
  })
}

test("A later AI translation updates the saved entry without a second POST or generation", async ({
  page,
}) => {
  let aiCalls = 0
  let saves = 0
  let updates = 0
  await page.route("**/chapters/*/explain", (route) => {
    aiCalls++
    return route.fulfill({ json: translation })
  })
  await page.route("**/api/v1/vocabulary/**", (route) => {
    if (route.request().method() === "POST") {
      saves++
      expect(route.request().postDataJSON().contextual_translation).toBeNull()
      return route.fulfill({
        json: { ...route.request().postDataJSON(), id: "saved" },
      })
    }
    updates++
    expect(route.request().method()).toBe("PATCH")
    expect(route.request().url()).toMatch(/\/vocabulary\/saved$/)
    expect(route.request().postDataJSON()).toEqual({
      contextual_translation: "casa",
    })
    return route.fulfill({
      json: { id: "saved", contextual_translation: "casa" },
    })
  })
  await page.goto(chapterPath)
  await selectMaison(page)
  await page.getByRole("button", { name: "Guardar palabra" }).click()
  await expect(
    page.getByRole("button", { name: "Palabra guardada" }),
  ).toBeDisabled()
  await page.getByRole("button", { name: "Explicar con IA" }).click()
  await page
    .getByRole("button", { name: "Actualizar traducción", exact: true })
    .click()
  await expect(
    page.getByRole("button", { name: "Palabra guardada" }),
  ).toBeDisabled()
  expect(saves).toBe(1)
  expect(updates).toBe(1)
  expect(aiCalls).toBe(1)
})

test("Vocabulary allows manual translation editing, retries and clearing without AI", async ({
  page,
}) => {
  let entry = {
    id: "saved",
    original_text: "maison",
    contextual_translation: null as string | null,
    context: "La maison est grande.",
    created_at: "2026-01-01T00:00:00Z",
  }
  let updates = 0
  let aiCalls = 0
  await page.route("**/chapters/*/explain", (route) => {
    aiCalls++
    return route.abort()
  })
  await page.route("**/api/v1/vocabulary/**", (route) => {
    if (route.request().method() === "PATCH") {
      updates++
      if (updates === 1)
        return route.fulfill({
          status: 503,
          json: { detail: "No se ha podido actualizar" },
        })
      entry = { ...entry, ...route.request().postDataJSON() }
      return route.fulfill({ json: entry })
    }
    return route.fulfill({ json: { data: [entry], count: 1 } })
  })
  await page.goto("/vocabulary")
  await expect(page.getByText("Sin traducción", { exact: true })).toBeVisible()
  await page
    .getByRole("button", { name: "Editar traducción de maison" })
    .click()
  await page.getByLabel("Traducción de maison (opcional)").fill("casa")
  await page
    .getByRole("button", { name: "Guardar traducción", exact: true })
    .click()
  await expect(page.getByRole("alert")).toHaveText("No se ha podido actualizar")
  await expect(page.getByLabel("Traducción de maison (opcional)")).toHaveValue(
    "casa",
  )
  await page
    .getByRole("button", { name: "Guardar traducción", exact: true })
    .click()
  await expect(page.getByText("maison — casa", { exact: true })).toBeVisible()
  await page.reload()
  await expect(page.getByText("maison — casa", { exact: true })).toBeVisible()
  await page
    .getByRole("button", { name: "Editar traducción de maison" })
    .click()
  await page.getByLabel("Traducción de maison (opcional)").fill("")
  await page
    .getByRole("button", { name: "Guardar traducción", exact: true })
    .click()
  await expect(page.getByText("Sin traducción", { exact: true })).toBeVisible()
  expect(entry.contextual_translation).toBeNull()
  expect(aiCalls).toBe(0)
})

test("Progress waits for recovery, restores after reload and debounces scrolling", async ({
  page,
}) => {
  let saved = { ...stored }
  const writes: Array<Record<string, unknown>> = []
  let release!: () => void
  const gate = new Promise<void>((resolve) => {
    release = resolve
  })
  let delayed = true
  await page.route("**/books/*/progress", async (route) => {
    if (route.request().method() === "GET") {
      if (delayed) await gate
      return route.fulfill({ json: saved })
    }
    const body = route.request().postDataJSON()
    writes.push(body)
    expect(body.expected_version).toBe(saved.version)
    saved = { ...saved, ...body, version: saved.version + 1 }
    return route.fulfill({ json: saved })
  })
  await page.goto(chapterPath)
  await expect(page.getByText("Recuperando progreso…")).toBeVisible()
  await page.mouse.wheel(0, 600)
  expect(writes).toHaveLength(0)
  delayed = false
  release()
  await expect(page.getByText("Recuperando progreso…")).toHaveCount(0)
  await expect
    .poll(() => page.evaluate(() => window.scrollY))
    .toBeGreaterThan(1000)
  await page.waitForTimeout(1000)
  expect(writes).toHaveLength(0)
  await page.mouse.wheel(0, 200)
  await page.mouse.wheel(0, 200)
  await page.mouse.wheel(0, 200)
  expect(writes).toHaveLength(0)
  await expect.poll(() => writes.length).toBe(1)
  expect(Number(writes[0].position)).toBeGreaterThan(stored.position)
  expect(writes[0].content_hash).toBe(hash)
  const position = saved.position
  await page.reload()
  await expect
    .poll(() => page.evaluate(() => window.scrollY))
    .toBeGreaterThan(1000)
  await page.waitForTimeout(1000)
  expect(writes).toHaveLength(1)
  expect(saved.position).toBe(position)
})

test("A conflict stops saves rather than overwriting another reading session", async ({
  page,
}) => {
  let writes = 0
  await page.route("**/books/*/progress", (route) => {
    if (route.request().method() === "GET")
      return route.fulfill({ json: stored })
    writes++
    return route.fulfill({
      status: 409,
      json: {
        detail:
          "El progreso se actualizó desde otra lectura. Recarga para continuar.",
      },
    })
  })
  await page.goto(chapterPath)
  await expect
    .poll(() => page.evaluate(() => window.scrollY))
    .toBeGreaterThan(1000)
  await page.mouse.wheel(0, 400)
  await expect(page.getByRole("alert")).toContainText("Recarga para continuar")
  await page.mouse.wheel(0, 400)
  await page.waitForTimeout(1000)
  expect(writes).toBe(1)
})

test("Changed chapter content preserves the previous progress", async ({
  page,
}) => {
  let writes = 0
  await page.route("**/books/*/progress", (route) => {
    if (route.request().method() === "PUT") writes++
    return route.fulfill({ json: { ...stored, content_hash: "0".repeat(64) } })
  })
  await page.goto(chapterPath)
  await expect(page.getByRole("alert")).toContainText("El capítulo ha cambiado")
  await page.mouse.wheel(0, 500)
  await page.waitForTimeout(1000)
  expect(writes).toBe(0)
})

test("Book detail continues in the last chapter without writing an initial zero", async ({
  page,
}) => {
  let writes = 0
  await page.route("**/books/*/progress", (route) => {
    if (route.request().method() === "PUT") writes++
    return route.fulfill({ json: { ...stored, chapter_id: nextId } })
  })
  await page.goto(`/books/${bookId}`)
  await page.getByRole("link", { name: "Continuar leyendo" }).click()
  await expect(page).toHaveURL(`/books/${bookId}/chapters/${nextId}`)
  await expect
    .poll(() => page.evaluate(() => window.scrollY))
    .toBeGreaterThan(1000)
  expect(writes).toBe(0)
})

test("Vocabulary pagination requests the next page", async ({ page }) => {
  await page.route("**/api/v1/vocabulary/**", (route) => {
    const skip = Number(new URL(route.request().url()).searchParams.get("skip"))
    const data = Array.from({ length: skip === 0 ? 20 : 1 }, (_, index) => ({
      id: `${skip + index}`,
      original_text: `mot ${skip + index}`,
      contextual_translation: "palabra",
      context: "Contexte",
      created_at: "2026-01-01T00:00:00Z",
    }))
    return route.fulfill({ json: { data, count: 21 } })
  })
  await page.goto("/vocabulary")
  await expect(page.getByText("mot 0 — palabra", { exact: true })).toBeVisible()
  await page.getByRole("button", { name: "Siguiente", exact: true }).click()
  await expect(
    page.getByText("mot 20 — palabra", { exact: true }),
  ).toBeVisible()
  await expect(
    page.getByRole("button", { name: "Siguiente", exact: true }),
  ).toBeDisabled()
})

test("Short chapters save a deliberate reading interaction without an initial write", async ({
  page,
}) => {
  const writes: Array<Record<string, unknown>> = []
  const shortText = "La maison."
  await page.route(`**/api/v1/books/*/chapters/${chapterId}`, (route) =>
    route.fulfill({
      json: {
        id: chapterId,
        book_id: bookId,
        title: "Court",
        position: 1,
        content: shortText,
      },
    }),
  )
  await page.route("**/books/*/progress", (route) => {
    if (route.request().method() === "GET") return route.fulfill({ json: null })
    const body = route.request().postDataJSON()
    writes.push(body)
    return route.fulfill({ json: { ...stored, ...body, version: 1 } })
  })
  await page.goto(chapterPath)
  await expect(page.getByText("Recuperando progreso…")).toHaveCount(0)
  await expect(page.getByTestId("chapter-content")).toHaveText(shortText)
  await page.waitForTimeout(1000)
  expect(writes).toHaveLength(0)
  await page.getByTestId("chapter-content").click()
  await expect.poll(() => writes.length).toBe(1)
  expect(writes[0]).toMatchObject({
    chapter_id: chapterId,
    position: 0,
    expected_version: 0,
  })
})

test("A late write from the previous chapter cannot replace newer progress", async ({
  page,
}) => {
  let release!: () => void
  const gate = new Promise<void>((resolve) => {
    release = resolve
  })
  let writes = 0
  let reads = 0
  const newer = { ...stored, chapter_id: nextId, version: 6 }
  await page.route("**/books/*/progress", async (route) => {
    if (route.request().method() === "GET") {
      reads++
      // Keep the book-detail refetch pending so its cached link can be checked.
      if (reads >= 3) return
      return route.fulfill({ json: reads === 1 ? stored : newer })
    }
    writes++
    await gate
    return route.fulfill({
      json: { ...stored, ...route.request().postDataJSON(), version: 5 },
    })
  })
  await page.goto(chapterPath)
  await expect
    .poll(() => page.evaluate(() => window.scrollY))
    .toBeGreaterThan(1000)
  await page.mouse.wheel(0, 300)
  await expect.poll(() => writes).toBe(1)
  await page.getByRole("link", { name: "Siguiente", exact: true }).click()
  await expect(page).toHaveURL(`/books/${bookId}/chapters/${nextId}`)
  await expect.poll(() => reads).toBe(2)
  await expect
    .poll(() => page.evaluate(() => window.scrollY))
    .toBeGreaterThan(1000)
  release()
  await page.waitForTimeout(200)
  await page.getByRole("link", { name: "Volver al libro", exact: true }).click()
  await expect(
    page.getByRole("link", { name: "Continuar leyendo" }),
  ).toHaveAttribute("href", `/books/${bookId}/chapters/${nextId}`)
})

test("Logging out removes personal cached data before another account logs in", async ({
  page,
}) => {
  let secondUser = false
  await page.route("**/api/v1/users/me", (route) =>
    route.fulfill({
      json: {
        id: secondUser ? "second" : "reader",
        email: secondUser ? "second@example.com" : "reader@example.com",
        is_active: true,
        is_superuser: false,
      },
    }),
  )
  await page.route("**/api/v1/vocabulary/**", async (route) => {
    if (secondUser) {
      await new Promise((resolve) => setTimeout(resolve, 300))
      return route.fulfill({ json: { data: [], count: 0 } })
    }
    return route.fulfill({
      json: {
        data: [
          {
            id: "private",
            original_text: "mot privé",
            contextual_translation: "privada",
            context: "Privé",
            created_at: "2026-01-01T00:00:00Z",
          },
        ],
        count: 1,
      },
    })
  })
  await page.route("**/api/v1/books/?*", (route) =>
    route.fulfill({ json: { data: [], count: 0 } }),
  )
  await page.route("**/api/v1/login/access-token", (route) =>
    route.fulfill({
      json: { access_token: "second-token", token_type: "bearer" },
    }),
  )
  await page.goto("/vocabulary")
  await expect(
    page.getByText("mot privé — privada", { exact: true }),
  ).toBeVisible()
  await page.getByTestId("user-menu").click()
  await page.getByRole("menuitem", { name: "Log Out" }).click()
  await expect(page).toHaveURL("/login")
  secondUser = true
  await page.getByTestId("email-input").fill("second@example.com")
  await page.getByTestId("password-input").fill("password-test")
  await page.getByRole("button", { name: "Log In", exact: true }).click()
  await expect(page).toHaveURL("/")
  await page.getByRole("link", { name: "Mi vocabulario", exact: true }).click()
  await expect(
    page.getByText("mot privé — privada", { exact: true }),
  ).toHaveCount(0)
  await expect(
    page.getByText("Todavía no has guardado palabras."),
  ).toBeVisible()
  await expect(page.getByTestId("user-menu")).toContainText(
    "second@example.com",
  )
})
