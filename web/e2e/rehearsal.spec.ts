import { test, expect } from "@playwright/test";
import { readCurrentSegment } from "./rehearsal-reader";
test.beforeEach(async ({ request }) => {
  await request.post("http://127.0.0.1:8001/__test/reset");
});

test("English mobile rehearsal → takeover → event → branch → save result → next scene", async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/rehearsal");
  await expect(
    page.getByRole("heading", { name: /Let your characters/ }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/rehearsal-home.png",
    fullPage: true,
  });
  await page.locator(".rh-example").click();
  await page.getByRole("button", { name: /Start rehearsal/ }).click();
  await readCurrentSegment(page);
  await expect(
    page.getByText("I remembered how you take it.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Continue", exact: true }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Intervene", exact: true }).click();
  let panel = page.getByRole("dialog");
  await panel.getByRole("button", { name: /Play a character/ }).click();
  await panel.getByRole("button", { name: /Lin.*Play this role/ }).click();
  await page
    .getByRole("textbox", { name: "Your performance" })
    .fill("Some things, you do remember.");
  await page.getByRole("button", { name: "Send performance" }).click();
  await readCurrentSegment(page);
  await expect(
    page.getByText("Some things, you do remember.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Hand back role", exact: true }),
  ).toBeEnabled();
  await page
    .getByRole("button", { name: "Hand back role", exact: true })
    .click();
  await page.getByRole("button", { name: "Intervene", exact: true }).click();
  await panel.getByRole("button", { name: /Introduce an event/ }).click();
  await panel
    .getByLabel("What happens?", { exact: true })
    .fill("The departure announcement interrupts them.");
  await panel.getByRole("button", { name: /Add event/ }).click();
  await readCurrentSegment(page);
  await expect(
    page.getByRole("button", { name: "Continue", exact: true }),
  ).toBeEnabled();
  await page
    .getByRole("button", { name: "Other directions", exact: true })
    .click();
  await expect(
    panel.getByRole("heading", { name: "A partial confession" }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/rehearsal-directions.png",
    fullPage: true,
  });
  await panel.getByRole("button", { name: /A partial confession/ }).click();
  await readCurrentSegment(page);
  await expect(
    page.getByText(
      "I told them where you would be. I should have told you myself.",
      { exact: true },
    ),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/rehearsal-stage.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "More options", exact: true }).click();
  await panel.getByRole("button", { name: /Versions/, exact: true }).click();
  const versions = panel.locator(".rh-version-list article");
  await expect(versions).toHaveCount(2);
  await versions.first().locator("button").first().click();
  await expect(
    page.getByText(
      "I told them where you would be. I should have told you myself.",
      { exact: true },
    ),
  ).not.toBeVisible();
  await page.getByRole("button", { name: /Version 1/ }).click();
  await panel
    .locator(".rh-version-list article")
    .last()
    .locator("button")
    .first()
    .click();
  await page.getByRole("button", { name: "More options", exact: true }).click();
  await panel
    .getByRole("button", { name: "End scene & review", exact: false })
    .click();
  await expect(
    page.getByRole("heading", { name: /A scene worth/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Save this scene/ }).click();
  await expect(
    page.getByText("Saved as this scene’s result", { exact: false }).first(),
  ).toBeVisible();
  await page.getByRole("button", { name: "Export scene", exact: true }).click();
  await panel
    .getByRole("button", { name: "Preview export", exact: true })
    .click();
  await expect(panel.locator("pre")).toContainText("I told them");
  const download = page.waitForEvent("download");
  await panel.getByRole("button", { name: /Download TXT/ }).click();
  expect((await download).suggestedFilename()).toMatch(/\.txt$/);
  await panel.getByRole("button", { name: "Close panel" }).click();
  await page.getByRole("button", { name: /Rehearse the next scene/ }).click();
  await expect(
    page.getByText("Continuing from", { exact: false }),
  ).toBeVisible();
  const ss = await (await request.get("/api/rehearsal/scenes")).json();
  expect(ss).toHaveLength(2);
  expect(
    ss.find((s: any) => !!s.document.source).document.initial_state.world_facts,
  ).not.toHaveLength(0);
  expect(errors).toEqual([]);
});

test("in-scene creation includes portraits, preserves cast and setup at 320px", async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await page.goto("/rehearsal");
  await page
    .getByRole("button", { name: "Rehearse a scene", exact: false })
    .click();
  const panel = page.getByRole("dialog");
  for (const [name, description] of [
    ["Lena", "A quiet restorer who wants an honest answer."],
    ["Rowan", "An old friend hiding why he left the city."],
  ]) {
    await page
      .getByRole("button", { name: "Create", exact: false })
      .filter({ hasText: /Create/ })
      .first()
      .click();
    await page.getByLabel("Describe your character").fill(description);
    await page
      .getByRole("button", { name: /^Create character/ })
      .last()
      .click();
    await expect(page.getByAltText("Portrait of Evelyn")).toBeVisible();
    await page
      .getByRole("button", { name: "Edit character", exact: true })
      .click();
    await panel.getByLabel("Name", { exact: true }).fill(name);
    await panel
      .getByRole("button", { name: "Save character", exact: true })
      .click();
    await page.getByRole("button", { name: /Use in this scene/ }).click();
    await expect(
      page.getByRole("heading", { name: /Who is in/ }),
    ).toBeVisible();
  }
  await page.getByRole("button", { name: /Next: set the scene/ }).click();
  await page
    .getByLabel("What situation are they in?", { exact: false })
    .fill("They meet at a station on the evening before the gallery opens.");
  await expect(page.locator(".rh-sync").last()).toHaveText(
    "Saved automatically",
  );
  await page.reload();
  await expect(
    page.getByLabel("What situation are they in?", { exact: false }),
  ).toHaveValue(
    "They meet at a station on the evening before the gallery opens.",
  );
  await page.getByRole("button", { name: /Start rehearsal/ }).click();
  await readCurrentSegment(page);
  await expect(
    page.getByText("I hoped we would have a moment to talk.", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  const cc = await (await request.get("/api/rehearsal/characters")).json();
  expect(cc).toHaveLength(2);
  expect(cc.every((c: any) => !!c.current_image_id)).toBeTruthy();
});

test("permission denial never falls back to cached scene text", async ({
  page,
  request,
}) => {
  const created = await (
    await request.post("/api/rehearsal/scenes", {
      data: {
        operation_id: crypto.randomUUID(),
        demo: true,
        setup: { premise: "A private scene with a confidential premise." },
      },
    })
  ).json();
  await page.goto(`/rehearsal?view=stage&scene=${created.id}`);
  await expect(
    page.getByText("A private scene with a confidential premise.", {
      exact: true,
    }),
  ).toBeVisible();
  await page.route(`**/api/rehearsal/scenes/${created.id}`, (route) =>
    route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Scene not found." }),
    }),
  );
  await page.reload();
  await expect(page.locator(".rh-alert[role=alert]")).toContainText(
    "Scene not found.",
  );
  await expect(
    page.getByText("A private scene with a confidential premise.", {
      exact: true,
    }),
  ).not.toBeVisible();
});

test("one sentence at a time → refresh keeps position → intervene without unseen future", async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/rehearsal");
  await page.locator(".rh-example").click();
  await page.getByRole("button", { name: /Start rehearsal/ }).click();
  await expect(page.locator(".rehearsal-app")).toHaveAttribute(
    "data-generating",
    "false",
  );
  await expect(
    page.getByText("Rain softens the station lights.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Two cups of coffee wait on the bench.", { exact: false }),
  ).not.toBeVisible();
  await expect(
    page.getByText("I remembered how you take it.", { exact: true }),
  ).not.toBeVisible();
  const initial = await (await request.get("/api/rehearsal/scenes")).json();
  const sid = initial[0].id;
  const original = initial[0].document.active_version;
  const originalHead = initial[0].document.versions[original].head;
  const originalNodes = Object.keys(initial[0].document.nodes).length;
  await page.getByRole("button", { name: "Next line", exact: true }).click();
  await expect(
    page.getByText(
      "Rain softens the station lights. Two cups of coffee wait on the bench.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    page.getByText("I remembered how you take it.", { exact: true }),
  ).not.toBeVisible();
  await page.reload();
  await expect(
    page.getByText(
      "Rain softens the station lights. Two cups of coffee wait on the bench.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    page.getByText("I remembered how you take it.", { exact: true }),
  ).not.toBeVisible();
  const read = await (await request.get(`/api/rehearsal/scenes/${sid}`)).json();
  expect(Object.keys(read.document.nodes)).toHaveLength(originalNodes);
  expect(read.document.versions[original].head).toBe(originalHead);
  await page.getByRole("button", { name: "Intervene", exact: true }).click();
  const panel = page.getByRole("dialog");
  await panel.getByRole("button", { name: /Play a character/ }).click();
  await panel.getByRole("button", { name: /Lin.*Play this role/ }).click();
  const changed = await (
    await request.get(`/api/rehearsal/scenes/${sid}`)
  ).json();
  expect(changed.document.active_version).not.toBe(original);
  const head =
    changed.document.nodes[
      changed.document.versions[changed.document.active_version].head
    ];
  expect(head.blocks.map((b: any) => b.text).join("")).toBe(
    "Rain softens the station lights. Two cups of coffee wait on the bench.",
  );
  expect(changed.document.versions[original].head).toBe(originalHead);
  await page.screenshot({
    path: "test-results/rehearsal-paced-reading.png",
    fullPage: true,
  });
});
