import { expect, type Page, test } from "@playwright/test"

const bookId = "00000000-0000-4000-8000-000000000010"
const chapterId = "00000000-0000-4000-8000-000000000020"
const nextId = "00000000-0000-4000-8000-000000000021"
const content =
  "😀 L’été, l’homme regarde Paris.\n\nUne autre phrase avec l’homme.\nLa fin."
const path = `/books/${bookId}/chapters/${chapterId}`

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
    const url = new URL(route.request().url())
    const entries = [chapterId, nextId].map((id, index) => ({
      id,
      book_id: bookId,
      title: `Chapitre ${index + 1}`,
      position: index + 1,
    }))
    if (url.pathname.endsWith("/chapters"))
      return route.fulfill({ json: { data: entries, count: 2 } })
    const index = url.pathname.endsWith(nextId) ? 1 : 0
    return route.fulfill({
      json: {
        ...entries[index],
        content: index === 0 ? content : "Le prochain chapitre.",
      },
    })
  })
})

async function selectOffsets(page: Page, start: number, end: number) {
  await page.getByTestId("chapter-content").evaluate(
    (root, offsets) => {
      const node = root.firstChild!
      const range = document.createRange()
      range.setStart(node, offsets.start)
      range.setEnd(node, offsets.end)
      const selected = document.getSelection()!
      selected.removeAllRanges()
      selected.addRange(range)
    },
    { start, end },
  )
}

test("Native selection captures the original accented phrase and cross-paragraph text", async ({
  page,
}) => {
  await page.goto(path)
  const root = page.getByTestId("chapter-content")
  await expect(root).toHaveText(content)
  const start = content.lastIndexOf("l’homme")
  await selectOffsets(page, start, start + "l’homme".length)
  await expect(page.getByTestId("selected-text")).toHaveText("l’homme")
  await expect(page.getByTestId("selection-context")).toHaveText(
    "Une autre phrase avec l’homme.\nLa fin.",
  )
  const from = content.indexOf("Paris")
  const to = content.indexOf("phrase") + "phrase".length
  await selectOffsets(page, from, to)
  await expect(page.getByTestId("selected-text")).toHaveText(
    content.slice(from, to),
  )
  await expect(root).toHaveText(content)
  await page.getByRole("button", { name: "Cerrar panel contextual" }).click()
  await expect(
    page.getByRole("complementary", { name: "Tu selección" }),
  ).toHaveCount(0)
  await selectOffsets(page, start, start + 7)
  await expect(page.getByTestId("selected-text")).toBeVisible()
  await page.keyboard.press("Escape")
  await expect(page.getByTestId("selected-text")).toHaveCount(0)
})

test("Selection extraction maps DOM offsets, not the first repeated word", async ({
  page,
}) => {
  await page.goto(path)
  await expect(page.getByTestId("chapter-content")).toBeVisible()
  const result = await page.evaluate(
    async ({ content, bookId, chapterId }) => {
      const { extractTextSelection } = await import(
        "/src/components/Reader/selection.ts"
      )
      const root = document.createElement("div")
      const first = document.createElement("span")
      const second = document.createElement("span")
      const split = content.indexOf("Une")
      first.textContent = content.slice(0, split)
      second.textContent = content.slice(split)
      root.append(first, second)
      document.body.append(root)
      const range = document.createRange()
      const start = content.lastIndexOf("l’homme")
      range.setStart(second.firstChild!, start - split)
      range.setEnd(second.firstChild!, start - split + 7)
      const native = document.getSelection()!
      native.removeAllRanges()
      native.addRange(range)
      const repeated = extractTextSelection(
        root,
        content,
        bookId,
        chapterId,
        native,
      )
      range.setStart(first.firstChild!, content.indexOf("Paris"))
      range.setEnd(second.firstChild!, 3)
      native.removeAllRanges()
      native.addRange(range)
      const across = extractTextSelection(
        root,
        content,
        bookId,
        chapterId,
        native,
      )
      native.removeAllRanges()
      root.remove()
      return { repeated, across }
    },
    { content, bookId, chapterId },
  )
  expect(result.repeated).toMatchObject({
    bookId,
    chapterId,
    text: "l’homme",
    startOffset: content.lastIndexOf("l’homme"),
    endOffset: content.lastIndexOf("l’homme") + 7,
    offsetUnit: "utf-16",
  })
  expect(
    content.slice(result.repeated!.startOffset, result.repeated!.endOffset),
  ).toBe(result.repeated!.text)
  expect(
    content.slice(
      result.repeated!.contextStartOffset,
      result.repeated!.contextEndOffset,
    ),
  ).toBe(result.repeated!.context)
  expect(result.across!.text).toBe(
    content.slice(content.indexOf("Paris"), content.indexOf("Une") + 3),
  )
})

test("Empty, collapsed, external and mismatched selections are rejected", async ({
  page,
}) => {
  await page.goto(path)
  await expect(page.getByTestId("chapter-content")).toBeVisible()
  const results = await page.evaluate(async () => {
    const { extractTextSelection } = await import(
      "/src/components/Reader/selection.ts"
    )
    const root = document.createElement("div")
    root.textContent = "abc"
    const outside = document.createElement("span")
    outside.textContent = "elsewhere"
    document.body.append(root, outside)
    const selection = document.getSelection()!
    selection.removeAllRanges()
    const noRange = extractTextSelection(root, "abc", "b", "c", selection)
    const range = document.createRange()
    range.selectNodeContents(outside)
    selection.addRange(range)
    const external = extractTextSelection(root, "abc", "b", "c", selection)
    range.setStart(root.firstChild!, 1)
    range.setEnd(outside.firstChild!, 3)
    selection.removeAllRanges()
    selection.addRange(range)
    const crossingOutside = extractTextSelection(
      root,
      "abc",
      "b",
      "c",
      selection,
    )
    range.selectNodeContents(root)
    selection.removeAllRanges()
    selection.addRange(range)
    const mismatch = extractTextSelection(root, "xyz", "b", "c", selection)
    range.collapse(true)
    selection.removeAllRanges()
    selection.addRange(range)
    const collapsed = extractTextSelection(root, "abc", "b", "c", selection)
    root.textContent = "   "
    range.selectNodeContents(root)
    selection.removeAllRanges()
    selection.addRange(range)
    const whitespace = extractTextSelection(root, "   ", "b", "c", selection)
    root.textContent = ""
    const empty = extractTextSelection(root, "", "b", "c", selection)
    selection.removeAllRanges()
    root.remove()
    outside.remove()
    return [
      noRange,
      external,
      crossingOutside,
      mismatch,
      collapsed,
      whitespace,
      empty,
    ]
  })
  expect(results).toEqual(Array(7).fill(null))
  await expect(page.getByTestId("selected-text")).toHaveCount(0)
})

test("Context bounds are literal source slices and do not split emoji", async ({
  page,
}) => {
  await page.goto(path)
  const result = await page.evaluate(async () => {
    const { getContextBounds } = await import(
      "/src/components/Reader/selection.ts"
    )
    const value = `A😀${"x".repeat(159)}word${"y".repeat(159)}😀Z`
    const start = value.indexOf("word")
    const bounds = getContextBounds(value, start, start + 4)
    return { value, ...bounds }
  })
  expect(result.value.slice(result.from, result.to)).toBe(
    `😀${"x".repeat(159)}word${"y".repeat(159)}😀`,
  )
})

test("Changing chapters discards context, including when returning to cached content", async ({
  page,
}) => {
  await page.goto(path)
  await selectOffsets(page, 3, 8)
  await expect(page.getByTestId("selected-text")).toBeVisible()
  await page.getByRole("link", { name: "Siguiente", exact: true }).click()
  await expect(
    page.getByRole("heading", { name: "Chapitre 2", exact: true }),
  ).toBeVisible()
  await expect(page.getByTestId("selected-text")).toHaveCount(0)
  await page.getByRole("link", { name: "Anterior", exact: true }).click()
  await expect(page.getByTestId("chapter-content")).toHaveText(content)
  await expect(page.getByTestId("selected-text")).toHaveCount(0)
})

test("Reading preferences change presentation without changing text or persisting on reload", async ({
  page,
}) => {
  await page.goto(path)
  await page.getByText("Ajustes de lectura", { exact: true }).click()
  await page.getByRole("combobox", { name: "Tamaño de letra" }).click()
  await page.getByRole("option", { name: "24 px", exact: true }).click()
  await page.getByRole("combobox", { name: "Interlineado" }).click()
  await page.getByRole("option", { name: "2.1", exact: true }).click()
  await page.getByRole("combobox", { name: "Tipografía" }).click()
  await page.getByRole("option", { name: "Sans-serif", exact: true }).click()
  const root = page.getByTestId("chapter-content")
  await expect(root).toHaveCSS("font-size", "24px")
  await expect(root).toHaveCSS("line-height", "50.4px")
  await expect(root).toHaveCSS("font-family", "sans-serif")
  await expect(root).toHaveText(content)
  await page.getByRole("link", { name: "Siguiente", exact: true }).click()
  await expect(root).toHaveText("Le prochain chapitre.")
  await expect(root).toHaveCSS("font-size", "24px")
  await page.reload()
  await expect(root).toHaveCSS("font-size", "18px")
})

test("Mobile context panel is dismissible and does not cause horizontal overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(path)
  await selectOffsets(page, 3, 8)
  await expect(
    page.getByRole("complementary", { name: "Tu selección" }),
  ).toBeVisible()
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true)
  await page.getByRole("button", { name: "Cerrar panel contextual" }).click()
  await expect(page.getByTestId("chapter-content")).toHaveText(content)
})

test("Mouse selection and keyboard extension update the contextual panel", async ({
  page,
}) => {
  await page.goto(path)
  const start = content.indexOf("l’homme")
  const end = start + 7
  const box = await page.getByTestId("chapter-content").evaluate(
    (root, offsets) => {
      const range = document.createRange()
      range.setStart(root.firstChild!, offsets.start)
      range.setEnd(root.firstChild!, offsets.end)
      const rect = range.getBoundingClientRect()
      return {
        left: rect.left,
        right: rect.right,
        y: rect.top + rect.height / 2,
      }
    },
    { start, end },
  )
  await page.mouse.move(box.left + 0.2, box.y)
  await page.mouse.down()
  await page.mouse.move(box.right - 0.2, box.y, { steps: 12 })
  await page.mouse.up()
  await expect(page.getByTestId("selected-text")).toHaveText("l’homme")
  await page.keyboard.press("Shift+ArrowRight")
  await expect
    .poll(() => page.getByTestId("selected-text").textContent())
    .toBe("l’homme ")
})
