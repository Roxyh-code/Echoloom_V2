import { test, expect } from "@playwright/test";

// The configured server is test-only and uses an ephemeral database.
test.afterEach(async ({ request }) => {
  const characters = await (await request.get("/api/characters")).json();
  for (const character of characters)
    await request.delete(`/api/characters/${character.id}`);
});

test("chat invitation → scene → choice → interruption → rewrite → undo → return and revisit", async ({
  page,
  request,
}) => {
  const created = await request.post("/api/characters/generate", {
    data: {
      description: "A reserved librarian with a precise, dry speaking style.",
    },
  });
  const character = await created.json();
  await request.patch(`/api/characters/${character.id}`, {
    data: {
      profile: {
        ...character.profile,
        speech_style: {
          ...character.profile.speech_style,
          tone: "Dry and gentle",
        },
      },
      expected_version: 1,
    },
  });
  await page.goto(`/characters/${character.id}/chat`);
  await expect(
    page.getByRole("button", { name: "Do something together" }),
  ).toBeInViewport();
  await expect(page.locator(".extras-menu")).toHaveCount(0);
  await page.getByRole("button", { name: "Do something together" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page
    .getByLabel("Your scene", { exact: true })
    .fill("We are old friends meeting in a bookshop on a rainy evening.");
  await page.getByLabel("Your name in the story").fill("Alex");
  await page.getByLabel("Content to avoid").evaluate((el) => {
    (el.closest("details") as HTMLDetailsElement).open = true;
  });
  await page
    .getByLabel("Content to avoid")
    .fill("No romantic commitment without my decision.");
  await page
    .getByRole("button", { name: "Send invitation", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page).toHaveURL(/\/chat$/);
  await expect(page.locator(".story-card")).toHaveCount(1);
  const firstCard = await (
    await request.get(
      `/api/conversations/${character.conversation_id}/timeline`,
    )
  ).json();
  const sid = firstCard[0].story_id;
  const ready = await (await request.get(`/api/stories/${sid}`)).json();
  expect(ready.segments).toHaveLength(0);
  await page.getByRole("link", { name: "Begin →", exact: true }).click();
  await expect(page).toHaveURL(/\/stories\//);
  await expect(
    page.getByRole("button", { name: "Show all", exact: true }),
  ).toBeEnabled();
  await expect(
    page.getByRole("heading", { name: "How would you like to respond?" }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Show all", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "How would you like to respond?" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Continue story →" }),
  ).toHaveCount(0);
  await page
    .getByRole("button", { name: "Ask what happened", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Show all", exact: true }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(
    page.getByText("She explains the missing letter.", { exact: true }),
  ).toBeVisible();
  // Pause by typing, then replace the unread suffix with the user's own line.
  await page.getByLabel("Contribution type").selectOption("dialogue");
  await page
    .getByLabel("Your contribution")
    .fill("I would like to take this slowly.");
  await page.getByRole("button", { name: "Contribute", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Show all", exact: true }),
  ).toBeEnabled();
  const changed = await (await request.get(`/api/stories/${sid}`)).json();
  expect(changed.segments[1].blocks).toHaveLength(1);
  await page.getByRole("button", { name: "Show all", exact: true }).click();
  await expect(
    page.getByText("I would like to take this slowly.", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Rewrite latest segment", exact: true })
    .click();
  await page
    .getByLabel("How should this segment change?")
    .fill("Let the rain settle before speaking.");
  await page
    .getByRole("button", { name: "Rewrite segment", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Show all", exact: true }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Show all", exact: true }).click();
  await expect(
    page.getByText("Revised scene: Let the rain settle before speaking.", {
      exact: true,
    }),
  ).toBeVisible();
  page.once("dialog", (d) => d.accept());
  await page
    .getByRole("button", { name: "Undo last decision", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "How would you like to respond?" }),
  ).toBeVisible();
  await expect(
    page.getByText("She explains the missing letter.", { exact: true }),
  ).toHaveCount(0);
  await page.getByRole("link", { name: "← Back to chat" }).click();
  await expect(page.locator(".story-card")).toHaveCount(1);
  await expect(page.getByLabel("Conversation history")).toHaveValue(
    character.conversation_id,
  );
  await page
    .getByLabel("Message", { exact: true })
    .fill("Back in ordinary chat.");
  await page.getByRole("button", { name: "Send ↑", exact: true }).click();
  await expect(page.locator(".message.assistant")).toHaveCount(1);
  await expect(page.locator(".story-card")).toHaveCount(1);
  await page.getByRole("link", { name: "Continue →", exact: true }).click();
  await expect(page).toHaveURL(/\/stories\//);
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "How would you like to respond?" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Change the subject", exact: true })
    .click();
  await page.getByRole("button", { name: "Show all", exact: true }).click();
  await expect(
    page.getByText("She turns to the weather.", { exact: true }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "test-results/story-mobile.png",
    fullPage: true,
  });
  page.once("dialog", (d) => d.accept());
  await page
    .getByRole("button", { name: "End without epilogue", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "This story is complete." }),
  ).toBeVisible();
  await page.getByRole("link", { name: "← Back to chat" }).click();
  await page.getByRole("link", { name: "Revisit →", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "This story is complete." }),
  ).toBeVisible();
});

test("invitation keyboard close preserves the draft and restores focus", async ({
  page,
  request,
}) => {
  const c = await (
    await request.post("/api/characters/generate", {
      data: { description: "A traveler" },
    })
  ).json();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/characters/${c.id}/chat`);
  await page.getByRole("button", { name: "Do something together" }).click();
  await page
    .getByLabel("Your scene", { exact: true })
    .fill("A quiet walk beside a lake.");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Do something together" }),
  ).toBeFocused();
  await page.getByRole("button", { name: "Do something together" }).click();
  await expect(page.getByLabel("Your scene", { exact: true })).toHaveValue(
    "A quiet walk beside a lake.",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});
