import { expect, test } from "@playwright/test";

/**
 * Happy-path: login → list pending → open detail → claim → edit span →
 * approve → item disappears from the list.
 *
 * Needs a running backend (localhost:8000) with at least one pending
 * obrigacao and a user whose credentials are exposed as:
 *   E2E_USERNAME, E2E_PASSWORD
 *
 * Also needs the frontend dev server (pnpm dev) on E2E_FRONTEND_URL
 * (default http://localhost:3000) with NEXT_PUBLIC_API_URL pointing at
 * the backend. This test mutates real data (approves one obrigacao) —
 * do NOT run against shared environments.
 */
test("review an obrigacao end-to-end", async ({ page }) => {
  const username = process.env.E2E_USERNAME;
  const password = process.env.E2E_PASSWORD;
  test.skip(
    !username || !password,
    "E2E_USERNAME / E2E_PASSWORD not set — skipping review e2e.",
  );

  // Login.
  await page.goto("/login");
  await page.getByLabel("Usuário").fill(username!);
  await page.getByLabel("Senha").fill(password!);
  await page.getByRole("button", { name: "Entrar" }).click();

  // List page.
  await page.waitForURL("**/reviews");
  await expect(page.getByText("Itens pendentes")).toBeVisible();

  // Grab the first "Revisar" link and the id embedded in its href.
  const firstReview = page.getByRole("link", { name: "Revisar" }).first();
  await expect(firstReview).toBeVisible();
  const href = await firstReview.getAttribute("href");
  expect(href).toMatch(/\/reviews\/(obrigacao|recomendacao)\/\d+/);
  const [, kind, idStr] = href!.match(
    /\/reviews\/(obrigacao|recomendacao)\/(\d+)/,
  )!;
  const id = Number(idStr);

  await firstReview.click();

  // Detail page mounts → claim is auto-issued.
  await expect(page.getByText(/Reservado por você/)).toBeVisible();

  // Select text inside the span editor so descricao picks up the new span.
  const editor = page.getByTestId("span-editor");
  await editor.evaluate((node) => {
    const text = node.firstChild as Text;
    const range = document.createRange();
    range.setStart(text, 0);
    range.setEnd(text, Math.min(40, text.textContent?.length ?? 0));
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.addRange(range);
    node.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
  });

  await page.getByTestId("approve-button").click();

  // Back to list, item no longer present.
  await page.waitForURL("**/reviews");
  await expect(
    page.getByRole("link", { name: "Revisar" }).filter({
      hasText: new RegExp(`/${kind}/${id}`),
    }),
  ).toHaveCount(0);
});
