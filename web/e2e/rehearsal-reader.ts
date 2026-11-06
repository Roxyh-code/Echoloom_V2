import { expect, type Page } from "@playwright/test";
/** Read the already generated segment through the same controls as a user. */
export async function readCurrentSegment(page: Page) {
  const app = page.locator(".rehearsal-app");
  await expect(app).toHaveAttribute("data-working", "false");
  await expect(app).toHaveAttribute("data-generating", "false");
  for (let i = 0; i < 150; i++) {
    const next = page.getByRole("button", { name: "Next line", exact: true });
    if (!(await next.count())) return;
    await expect(next).toBeEnabled();
    await next.click();
    await expect(app).toHaveAttribute("data-working", "false");
  }
  throw new Error("Reader did not reach the end of the generated segment.");
}
