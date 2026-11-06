import { test, expect } from "@playwright/test";

test.beforeEach(async ({ request }) => {
  await request.post("http://127.0.0.1:8001/__test/reset");
});

test("mobile creator demo → directions → immutable saved version → alternative → facts → restore → export", async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 393, height: 852 });
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/creator");
  await expect(
    page.getByRole("heading", {
      name: /Create characters.*Discover their stories/,
    }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/creator-home.png",
    fullPage: true,
  });
  await page.locator(".cr-example").click();
  await expect(
    page.getByRole("heading", { name: "The Last Train", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Begin story →", exact: true })
    .click();
  await expect(
    page.getByText("23:02. Rain gathers on the platform.", { exact: false }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Show all", exact: true }).click();
  await expect(
    page.getByText("Were you going to tell me?", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Let Mira deflect", exact: false })
    .click();
  await page.getByRole("button", { name: "Show all", exact: true }).click();
  await page
    .getByRole("button", { name: "Save storyline", exact: false })
    .click();
  const panel = page.getByRole("dialog");
  await panel.getByLabel("Version name").fill("Before the departure");
  await panel
    .getByRole("button", { name: "Save version", exact: true })
    .click();
  await expect(panel).not.toBeVisible();
  await page
    .getByRole("button", { name: "Try another version", exact: false })
    .click();
  await panel.getByLabel("Name", { exact: true }).fill("The truth");
  await panel
    .getByLabel("What happens differently?")
    .fill("Let Mira admit the residency offer.");
  await panel.getByRole("button", { name: "Explore another version" }).click();
  await expect(panel).not.toBeVisible();
  await page.getByRole("button", { name: "Show all", exact: true }).click();
  await expect(
    page.getByText("I was offered a restoration residency.", { exact: false }),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/creator-reader.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Story notes", exact: true }).click();
  await page
    .getByRole("button", { name: "Add story fact", exact: false })
    .click();
  await panel
    .getByLabel("Story fact", { exact: true })
    .fill("Leo now knows about the residency.");
  await panel.getByLabel("Leo", { exact: true }).check();
  await panel
    .getByRole("button", { name: "Confirm fact", exact: true })
    .click();
  await expect(
    page.getByText("Leo now knows about the residency.", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await page.getByRole("button", { name: /Storylines.*possibilities/ }).click();
  await page
    .locator(".cr-line-card")
    .filter({ has: page.getByRole("heading", { name: "Main", exact: true }) })
    .getByRole("button", { name: "Use this storyline", exact: false })
    .click();
  await page.getByRole("button", { name: "Story notes", exact: true }).click();
  await expect(
    page.getByText("Leo now knows about the residency.", { exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "More options", exact: true }).click();
  await panel
    .getByRole("button", { name: "Saved versions", exact: true })
    .click();
  await page.getByRole("button", { name: "Preview", exact: true }).click();
  await expect(page.getByText("SAVED VERSION · READ ONLY")).toBeVisible();
  await page.reload();
  await expect(page.getByText("SAVED VERSION · READ ONLY")).toBeVisible();
  await expect(page.getByRole("button", { name: /Edit moment/ })).toHaveCount(
    0,
  );
  await page
    .getByRole("button", {
      name: "Continue from this saved version",
      exact: false,
    })
    .click();
  await page.getByRole("button", { name: "Export", exact: true }).click();
  await panel
    .getByRole("button", { name: "Prepare preview", exact: true })
    .click();
  await expect(panel.getByLabel("Export preview")).toContainText(
    "The Last Train",
  );
  const downloading = page.waitForEvent("download");
  await panel.getByRole("button", { name: "Download", exact: true }).click();
  expect((await downloading).suggestedFilename()).toBe("echoloom-story.md");
  const all = await (await request.get("/api/creator/works")).json();
  expect(all[0].document.checkpoints).toHaveLength(1);
  expect(Object.keys(all[0].document.lines)).toHaveLength(3);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});

test("one description creates profile and portrait → edit → play a role → exact authored line → refresh", async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 393, height: 852 });
  await page.goto("/creator");
  await page
    .getByRole("button", { name: "Create character", exact: false })
    .first()
    .click();
  const panel = page.getByRole("dialog");
  await panel
    .getByLabel("Who would you like to create?")
    .fill(
      "A silver-haired librarian with a quiet voice and a goal of keeping her bookshop open.",
    );
  await panel
    .getByRole("button", { name: "Create character", exact: false })
    .click();
  await expect(
    page.getByRole("heading", { name: "Evelyn", exact: true }),
  ).toBeVisible();
  await expect(page.getByAltText("Portrait of Evelyn")).toBeVisible();
  const characters = await (
    await request.get("/api/creator/characters")
  ).json();
  expect(characters).toHaveLength(1);
  expect(characters[0].current_image_id).toBeTruthy();
  await page
    .getByRole("button", { name: "Edit character", exact: true })
    .click();
  await panel.getByLabel("Name", { exact: true }).fill("Vera");
  await panel.getByLabel("What do they want?").fill("Keep the bookshop open.");
  await panel
    .getByRole("button", { name: "Save character", exact: true })
    .click();
  await expect(panel).not.toBeVisible();
  await page
    .getByRole("button", { name: "Start a story", exact: false })
    .click();
  await panel.getByLabel("Your name in the story").fill("Alex");
  await panel
    .getByLabel("What happens first?")
    .fill("We meet at the bookshop during a rainy evening.");
  await panel
    .getByRole("button", { name: "Begin story", exact: false })
    .click();
  await page.getByRole("button", { name: "Show all", exact: true }).click();
  await page.getByLabel("Contribution type").selectOption("dialogue");
  await page
    .getByLabel("Direct the scene or write a line")
    .fill("I came back because I wanted to hear your side.");
  await page
    .getByRole("button", { name: "Send direction", exact: true })
    .click();
  await page.getByRole("button", { name: "Show all", exact: true }).click();
  await expect(
    page.getByText("I came back because I wanted to hear your side.", {
      exact: true,
    }),
  ).toBeVisible();
  await page
    .getByLabel("Direct the scene or write a line")
    .fill("Keep this unfinished thought.");
  await page.reload();
  await expect(page.getByLabel("Direct the scene or write a line")).toHaveValue(
    "Keep this unfinished thought.",
  );
  await expect(
    page.getByText("I came back because I wanted to hear your side.", {
      exact: true,
    }),
  ).toBeVisible();
  const works = await (await request.get("/api/creator/works")).json();
  expect(Object.keys(works[0].document.nodes)).toHaveLength(2);
});

test("direct two characters preserves setup → new scene survives refresh → narrow layouts", async ({
  page,
  request,
}) => {
  const created = await (
    await request.post("/api/creator/characters", {
      data: {
        request_id: crypto.randomUUID(),
        description: "A reserved librarian who hopes to save her bookshop.",
      },
    })
  ).json();
  await page.setViewportSize({ width: 393, height: 852 });
  await page.goto(
    `/creator?screen=character&character=${created.character_id}`,
  );
  await page.getByRole("button", { name: /Start a story/ }).click();
  const panel = page.getByRole("dialog");
  await panel.getByLabel("How would you like to write?").selectOption("direct");
  await panel
    .getByLabel("What happens first?")
    .fill("Two old friends reunite at a bookshop before closing.");
  await panel
    .getByRole("button", { name: /Create a second character/ })
    .click();
  await panel
    .getByLabel("Who would you like to create?")
    .fill("An outgoing historian returning a borrowed book.");
  await panel.getByRole("button", { name: /Create character/ }).click();
  await expect(panel.getByLabel("What happens first?")).toHaveValue(
    "Two old friends reunite at a bookshop before closing.",
  );
  await expect(panel.getByLabel("First character")).toHaveValue(
    created.character_id,
  );
  await expect(panel.getByLabel("Second character")).not.toHaveValue(
    created.character_id,
  );
  await panel.getByRole("button", { name: /Begin story/ }).click();
  await page.getByRole("button", { name: "Show all", exact: true }).click();
  await page.getByRole("button", { name: /New scene/ }).click();
  await panel.getByLabel("Scene title").fill("The garden");
  await panel
    .getByLabel("What happens in this scene?")
    .fill("They walk into the garden to discuss saving the shop.");
  await panel.getByRole("button", { name: "Begin scene", exact: true }).click();
  await page.getByRole("button", { name: "Back", exact: true }).click();
  await page.getByRole("button", { name: /Scenes.*on this path/ }).click();
  await expect(
    page.getByRole("heading", { name: "The garden", exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "The garden", exact: true }),
  ).toBeVisible();
  for (const width of [360, 430]) {
    await page.setViewportSize({ width, height: 740 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
  }
  const works = await (await request.get("/api/creator/works")).json();
  const doc = works[0].document;
  expect(doc.mode).toBe("direct");
  expect(Object.keys(doc.scenes)).toHaveLength(2);
  expect(Object.keys(doc.nodes)).toHaveLength(2);
  expect(
    doc.casts[doc.lines[doc.active_line].cast_id].every(
      (m: { character_id: string }) => !!m.character_id,
    ),
  ).toBeTruthy();
});
