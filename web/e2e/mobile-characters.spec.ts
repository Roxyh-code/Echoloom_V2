import { test, expect } from "@playwright/test";
test.beforeEach(async ({ request }) => {
  await request.post("http://127.0.0.1:8001/__test/reset");
});

test("mobile character entry → profile + portrait → edit → refine → portrait versions → rehearsal", async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/characters");
  await expect(page).toHaveURL(/rehearsal\?view=characters/);
  await expect(
    page.getByRole("heading", { name: /Every story.*starts with someone/ }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/mobile-character-library.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Create character", exact: true })
    .click();
  await page
    .getByLabel("Describe your character")
    .fill(
      "A quiet astronomer with silver hair and a dry wit, determined to save her observatory.",
    );
  await page
    .getByRole("button", { name: /^Create character/ })
    .last()
    .click();
  await expect(page.getByAltText("Portrait of Evelyn")).toBeVisible();
  const cc = await (await request.get("/api/creator/characters")).json();
  expect(cc).toHaveLength(1);
  expect(cc[0].current_image_id).toBeTruthy();
  await page.screenshot({
    path: "test-results/mobile-character-detail.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Edit character", exact: true })
    .click();
  const panel = page.getByRole("dialog");
  await panel.getByLabel("Name", { exact: true }).fill("Vera");
  await panel.getByLabel("What do they want?").fill("Save her observatory.");
  await panel
    .getByRole("button", { name: "Save character", exact: true })
    .click();
  await expect(panel).not.toBeVisible();
  await page
    .getByRole("button", { name: "Refine with AI", exact: true })
    .click();
  await panel
    .getByLabel("What should change?")
    .fill("Make her more distant without changing her appearance.");
  await panel
    .getByRole("button", { name: "Preview changes", exact: true })
    .click();
  await expect(
    panel.getByRole("button", { name: "Apply these changes" }),
  ).toBeVisible();
  await panel.getByRole("button", { name: "Apply these changes" }).click();
  await expect(panel).not.toBeVisible();
  await page.getByRole("button", { name: /Edit portrait/ }).click();
  await panel
    .getByLabel("What should change in the portrait?")
    .fill("Give her auburn hair. Keep the rest.");
  await panel
    .getByRole("button", { name: "Edit portrait", exact: true })
    .click();
  await expect(
    panel.getByRole("button", { name: "Use this portrait" }),
  ).toHaveCount(1);
  await panel.getByRole("button", { name: "Use this portrait" }).click();
  await expect(
    panel.getByRole("button", { name: "Selected", exact: true }),
  ).toHaveCount(1);
  await panel.getByRole("button", { name: "Close panel" }).click();
  await page.getByRole("button", { name: /Rehearse with Vera/ }).click();
  await expect(page.getByRole("heading", { name: /Who is in/ })).toBeVisible();
  await expect(page.locator(".rh-cast-slot").first()).toContainText("Vera");
  expect(page.url()).toContain("/rehearsal");
  expect(errors).toEqual([]);
});

test("portrait failure retains character; retry only the portrait", async ({
  page,
  request,
}) => {
  await request.post("http://127.0.0.1:8001/__test/image-failure/true");
  await page.goto("/characters/new");
  await expect(page).toHaveURL(/rehearsal\?view=characters&create=1/);
  await page
    .getByLabel("Describe your character")
    .fill("An observant librarian with silver hair and a soft voice.");
  await page
    .getByRole("button", { name: /^Create character/ })
    .last()
    .click();
  await expect(
    page.getByRole("button", { name: "Retry portrait", exact: true }),
  ).toBeVisible();
  let cc = await (await request.get("/api/creator/characters")).json();
  expect(cc).toHaveLength(1);
  expect(cc[0].profile_version).toBe(1);
  expect(cc[0].current_image_id).toBeNull();
  await request.post("http://127.0.0.1:8001/__test/image-failure/false");
  await page
    .getByRole("button", { name: "Retry portrait", exact: true })
    .click();
  await expect(
    page
      .getByRole("dialog")
      .getByRole("button", { name: "Selected", exact: true }),
  ).toBeVisible();
  cc = await (await request.get("/api/creator/characters")).json();
  expect(cc).toHaveLength(1);
  expect(cc[0].profile_version).toBe(1);
  expect(cc[0].current_image_id).toBeTruthy();
});

test("lost creation response recovers both profile and portrait after refresh", async ({
  page,
  request,
}) => {
  await page.goto("/characters/new");
  await page
    .getByLabel("Describe your character")
    .fill(
      "A quiet astronomer with silver hair and a deeply independent spirit.",
    );
  await page.route("**/api/creator/characters", async (route) => {
    if (route.request().method() !== "POST") {
      await route.continue();
      return;
    }
    await route.fetch();
    await route.abort("failed");
  });
  await page
    .getByRole("button", { name: /^Create character/ })
    .last()
    .click();
  await expect
    .poll(
      async () =>
        (await (await request.get("/api/creator/characters")).json()).length,
    )
    .toBe(1);
  await page.reload();
  await expect(page.getByAltText("Portrait of Evelyn")).toBeVisible();
  const cs = await (await request.get("/api/creator/characters")).json();
  expect(cs).toHaveLength(1);
  expect(cs[0].current_image_id).toBeTruthy();
  const portraits = await (
    await request.get(`/api/characters/${cs[0].id}/images`)
  ).json();
  expect(portraits).toHaveLength(1);
});
