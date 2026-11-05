import { test, expect } from "@playwright/test";

test.beforeEach(async ({ request }) => {
  await request.post("http://127.0.0.1:8001/__test/reset");
});

test("create → edit → chat → refine → portrait edit → restore → return", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/characters");
  await expect(
    page.getByRole("heading", {
      name: "Your favorite character. By your side.",
    }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/companion-home.png",
    fullPage: true,
  });
  await expect(
    page.getByRole("heading", { name: "Who will your first character be?" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Start creating →" }).click();
  await page
    .getByLabel("Who would you like to meet?")
    .fill(
      "A silver-haired, blue-eyed librarian: reserved, intelligent and caring, living in a mountain town with a slightly sarcastic tone.",
    );
  await page.getByRole("button", { name: "Create my character →" }).click();
  await expect(page).toHaveURL(/\/characters\/[\w-]+\/edit/);
  const editUrl = page.url();
  await page.getByLabel("Name", { exact: true }).fill("Vera");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("✓ Saved · Profile v2")).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Name", { exact: true })).toHaveValue("Vera");
  await page.getByRole("link", { name: "Start chat ↗" }).click();
  await page
    .getByLabel("Message", { exact: true })
    .fill("What are you reading?");
  await page.getByRole("button", { name: "Send ↑" }).click();
  await expect(
    page.getByText(
      "A book about dying stars. Surprisingly cheerful material, isn't it?",
      {
        exact: true,
      },
    ),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByText("What are you reading?", { exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Edit character ↗" }).click();
  await page
    .getByLabel("What would you like to change?")
    .fill("Make her more distant, but still caring toward friends");
  await page.getByRole("button", { name: "✧ Preview AI changes" }).click();
  await expect(
    page.getByRole("heading", { name: "Change preview" }),
  ).toBeVisible();
  await expect(page.getByText("✓ Saved · Profile v2")).toBeVisible();
  await page.getByRole("button", { name: "Accept changes" }).click();
  await expect(page.getByText("✓ Saved · Profile v3")).toBeVisible();
  await expect(page.getByLabel("Backstory")).toHaveValue(
    "Works at a library in a mountain town.",
  );
  await expect(page.getByLabel("Hair", { exact: true })).toHaveValue(
    "Long silver hair",
  );
  await page.getByRole("button", { name: "✧ Generate portrait" }).click();
  await expect(page.getByAltText("Portrait version 1")).toBeVisible();
  await page.getByRole("button", { name: "Use this version" }).click();
  await expect(page.getByText("In use", { exact: true })).toBeVisible();
  await page
    .getByLabel("Edit current portrait")
    .fill("Change the hair to blue");
  await page
    .getByRole("button", { name: "Edit portrait", exact: true })
    .click();
  await expect(page.getByAltText("Portrait version 2")).toBeVisible();
  await page.getByRole("button", { name: "Use this version" }).click();
  await expect(
    page.locator(".image-version.selected").getByAltText("Portrait version 2"),
  ).toBeVisible();
  await page
    .locator(".image-version")
    .filter({ has: page.getByAltText("Portrait version 1") })
    .getByRole("button", { name: "Use this version" })
    .click();
  await expect(
    page.locator(".image-version.selected").getByAltText("Portrait version 1"),
  ).toBeVisible();
  page.once("dialog", (dialog) => dialog.accept());
  await page
    .locator(".version-list>div")
    .filter({ hasText: "v2 · Manual edit" })
    .getByRole("button", { name: "Restore", exact: true })
    .click();
  await expect(page.getByText("✓ Saved · Profile v4")).toBeVisible();
  await page.getByRole("link", { name: "Start chat ↗" }).click();
  await expect(
    page.getByText("What are you reading?", { exact: true }),
  ).toBeVisible();
  await page.getByLabel("Message", { exact: true }).fill("Let's keep talking");
  await page.getByRole("button", { name: "Send ↑" }).click();
  await expect(page.locator(".message.assistant")).toHaveCount(2);
  await page.goto("/characters");
  await expect(page.getByRole("heading", { name: "Vera" })).toBeVisible();
  await page.getByRole("link", { name: "Continue chat" }).click();
  await expect(
    page.getByText("Let's keep talking", { exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/chat-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "test-results/chat-mobile.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.goto(editUrl);
  await expect(page.getByLabel("Name", { exact: true })).toHaveValue("Vera");
  expect(errors).toEqual([]);
});

test("failed chat retry preserves one user turn", async ({ page, request }) => {
  const response = await request.post("/api/characters/generate", {
    data: { description: "Test character" },
  });
  const character = await response.json();
  await page.goto(`/characters/${character.id}/chat`);
  await page.getByLabel("Message", { exact: true }).fill("Retry test");
  let intercepted = false;
  await page.route("**/api/conversations/*/messages", async (route) => {
    if (route.request().method() === "POST" && !intercepted) {
      intercepted = true;
      // Let the backend commit the turn, then simulate a lost response.
      await route.fetch();
      await route.fulfill({
        status: 502,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Simulated lost network response" }),
      });
    } else await route.continue();
  });
  await page.getByRole("button", { name: "Send ↑" }).click();
  await expect(page.locator(".error[role=alert]")).toContainText(
    "Simulated lost network response",
  );
  await page.getByRole("button", { name: "Retry this message" }).click();
  await expect(page.locator(".message.user")).toHaveCount(1);
  await expect(page.locator(".message.assistant")).toHaveCount(1);
  await expect(page.getByLabel("Message", { exact: true })).toHaveValue("");
});

test("portrait selection cannot bypass a stale profile conflict", async ({
  page,
  request,
}) => {
  const created = await request.post("/api/characters/generate", {
    data: { description: "Profile conflict test character" },
  });
  const character = await created.json();
  const base = `/api/characters/${character.id}`;
  await request.post(`${base}/images/generate`, { data: {} });
  await page.goto(`/characters/${character.id}/edit`);
  await page
    .getByLabel("Name", { exact: true })
    .fill("Unsaved name in this page");
  const otherPage = await request.patch(base, {
    data: {
      profile: { ...character.profile, name: "Name saved in another page" },
      expected_version: 1,
    },
  });
  expect(otherPage.ok()).toBeTruthy();
  await page.getByRole("button", { name: "Use this version" }).click();
  await expect(page.getByText("In use", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.locator(".error[role=alert]")).toContainText(
    "The character was updated in another page",
  );
  const saved = await (await request.get(base)).json();
  expect(saved.profile.name).toBe("Name saved in another page");
  expect(saved.current_image_id).not.toBeNull();
});
