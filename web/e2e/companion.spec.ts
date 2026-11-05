import { test, expect } from "@playwright/test";

test.beforeEach(async ({ request }) => {
  await request.post("http://127.0.0.1:8001/__test/reset");
});

test("local account → mock Google consent → check-ins → switch → disconnect", async ({
  page,
  request,
}) => {
  const created = await request.post("/api/characters/generate", {
    data: {
      description:
        "A thoughtful astronomer with a warm and understated manner.",
    },
  });
  const character = await created.json();
  const second = await (
    await request.post("/api/characters/generate", {
      data: { description: "A gentle musician with a quiet sense of humor." },
    })
  ).json();
  await page.goto(`/characters/${character.id}/chat`);
  await expect(
    page.getByRole("button", { name: "Connect calendar" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Do something together" }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/companion-desktop.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Connect calendar" }).click();
  await page.getByLabel("Local username").fill("demo-owner");
  await page.getByLabel("Local password").fill("demo-password-123");
  await page.getByRole("button", { name: "Create local account" }).click();
  await expect(
    page.getByRole("button", { name: "Connect Google Calendar" }),
  ).toBeEnabled();
  await page.screenshot({ path: "test-results/companion-connect-dialog.png" });
  // Fake Google consent is rendered by the test, not shipped in the app.
  await page.route("https://accounts.google.com/**", async (route) => {
    const state = new URL(route.request().url()).searchParams.get("state");
    await route.fulfill({
      contentType: "text/html",
      body: `<h1>Test-only Google consent</h1><a href="http://127.0.0.1:3001/api/integrations/google-calendar/callback?state=${state}&code=test-code">Allow read-only calendar</a>`,
    });
  });
  await page
    .getByRole("button", { name: "Connect Google Calendar", exact: true })
    .click();
  await page.getByRole("link", { name: "Allow read-only calendar" }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  // No scheduler advance: the connection starts the conversation immediately.
  await expect(page.locator(".companion-message-label")).toHaveCount(1);
  await expect(page.getByText(/You have Physics exam coming up/)).toBeVisible();
  for (let attempt = 0; attempt < 2; attempt++) {
    await page.getByRole("button", { name: "My calendar" }).click();
    await page.getByRole("button", { name: "Sync now" }).click();
    await expect(page.getByRole("dialog")).not.toBeVisible();
    await expect(page.locator(".companion-message-label")).toHaveCount(2);
  }

  await page
    .getByLabel("Message", { exact: true })
    .fill("Keep my draft while check-ins arrive");
  await request.post("http://127.0.0.1:8001/__test/advance/30");
  await expect(page.locator(".companion-message-label")).toHaveCount(3, {
    timeout: 15000,
  });
  await expect(page.getByLabel("Message", { exact: true })).toHaveValue(
    "Keep my draft while check-ins arrive",
  );
  await request.post("http://127.0.0.1:8001/__test/advance/150");
  await expect(page.locator(".companion-message-label")).toHaveCount(4, {
    timeout: 15000,
  });
  await page.goto(`/characters/${second.id}/chat`);
  await page.getByRole("button", { name: "Use my calendar" }).click();
  await page.getByRole("button", { name: /Make .* my companion/ }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.getByRole("button", { name: "My calendar" }).click();
  await expect(
    page.getByRole("button", { name: "Pause check-ins", exact: true }),
  ).toBeVisible();
  await page.getByText("Disconnect Google Calendar", { exact: true }).click();
  await page
    .getByRole("button", { name: "Disconnect calendar", exact: true })
    .click();
  await expect(
    page.getByText("Calendar disconnected.", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close Life Companion" }).click();
  await page.goto(`/characters/${character.id}/chat`);
  await expect(page.locator(".companion-message-label")).toHaveCount(4);
});

test("mobile companion discovery and cancelled authorization leave chat usable", async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await request.post("/api/account/register", {
    data: { username: "mobile-owner", password: "mobile-password-123" },
  });
  const char = await (
    await request.post("/api/characters/generate", {
      data: {
        description: "A calm librarian who enjoys reading on rainy days.",
      },
    })
  ).json();
  await page.context().addCookies((await request.storageState()).cookies);
  await page.goto(`/characters/${char.id}/chat`);
  await expect(
    page.getByRole("button", { name: "Connect calendar" }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/companion-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Connect calendar" }).click();
  await page.route("https://accounts.google.com/**", async (route) => {
    const state = new URL(route.request().url()).searchParams.get("state");
    await route.fulfill({
      contentType: "text/html",
      body: `<h1>Test-only consent</h1><a href="http://127.0.0.1:3001/api/integrations/google-calendar/callback?state=${state}&error=access_denied">Cancel</a>`,
    });
  });
  await page
    .getByRole("button", { name: "Connect Google Calendar", exact: true })
    .click();
  await page.getByRole("link", { name: "Cancel" }).click();
  await expect(
    page.getByText("Connection cancelled.", { exact: false }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(
    page.getByRole("button", { name: "Connect calendar" }),
  ).toBeFocused();
  await page.getByLabel("Message", { exact: true }).fill("Hello");
  await page.getByRole("button", { name: "Send ↑" }).click();
  await expect(page.locator(".message.assistant")).toHaveCount(1);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
});
