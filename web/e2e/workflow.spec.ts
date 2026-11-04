import { test, expect } from "@playwright/test";

test("create → edit → chat → refine → portrait edit → restore → return", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/characters");
  await expect(
    page.getByRole("heading", { name: "你的第一个角色，会是谁？" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "开始创造 →" }).click();
  await page
    .getByLabel("你想遇见怎样的角色？")
    .fill(
      "银发蓝眼的图书管理员，安静、聪明、关心朋友，住在山城，语气略带讽刺。",
    );
  await page.getByRole("button", { name: "创造我的角色 →" }).click();
  await expect(page).toHaveURL(/\/characters\/[\w-]+\/edit/);
  const editUrl = page.url();
  await page.getByLabel("名字", { exact: true }).fill("薇拉");
  await page.getByRole("button", { name: "保存修改" }).click();
  await expect(page.getByText("✓ 已保存 · 设定 v2")).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("名字", { exact: true })).toHaveValue("薇拉");
  await page.getByRole("link", { name: "开始对话 ↗" }).click();
  await page.getByLabel("消息", { exact: true }).fill("你在看什么？");
  await page.getByRole("button", { name: "发送 ↑" }).click();
  await expect(
    page.getByText("一本关于垂死恒星的书。听起来是不是很振奋？", {
      exact: true,
    }),
  ).toBeVisible();
  await page.reload();
  await expect(page.getByText("你在看什么？", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "编辑角色 ↗" }).click();
  await page.getByLabel("你希望怎样调整？").fill("让她更冷淡，但仍然关心朋友");
  await page.getByRole("button", { name: "✧ 预览 AI 修改" }).click();
  await expect(page.getByRole("heading", { name: "修改预览" })).toBeVisible();
  await expect(page.getByText("✓ 已保存 · 设定 v2")).toBeVisible();
  await page.getByRole("button", { name: "采用这些修改" }).click();
  await expect(page.getByText("✓ 已保存 · 设定 v3")).toBeVisible();
  await expect(page.getByLabel("背景故事")).toHaveValue("在山城的图书馆工作。");
  await expect(page.getByLabel("头发", { exact: true })).toHaveValue(
    "银色长发",
  );
  await page.getByRole("button", { name: "✧ 生成头像" }).click();
  await expect(page.getByAltText("头像版本 1")).toBeVisible();
  await page.getByRole("button", { name: "选用此版" }).click();
  await expect(page.getByText("使用中", { exact: true })).toBeVisible();
  await page.getByLabel("修改当前头像").fill("把头发改成蓝色");
  await page.getByRole("button", { name: "修改头像", exact: true }).click();
  await expect(page.getByAltText("头像版本 2")).toBeVisible();
  await page.getByRole("button", { name: "选用此版" }).click();
  await expect(
    page.locator(".image-version.selected").getByAltText("头像版本 2"),
  ).toBeVisible();
  await page
    .locator(".image-version")
    .filter({ has: page.getByAltText("头像版本 1") })
    .getByRole("button", { name: "选用此版" })
    .click();
  await expect(
    page.locator(".image-version.selected").getByAltText("头像版本 1"),
  ).toBeVisible();
  page.once("dialog", (dialog) => dialog.accept());
  await page
    .locator(".version-list>div")
    .filter({ hasText: "v2 · 手动编辑" })
    .getByRole("button", { name: "恢复", exact: true })
    .click();
  await expect(page.getByText("✓ 已保存 · 设定 v4")).toBeVisible();
  await page.getByRole("link", { name: "开始对话 ↗" }).click();
  await expect(page.getByText("你在看什么？", { exact: true })).toBeVisible();
  await page.getByLabel("消息", { exact: true }).fill("接着聊吧");
  await page.getByRole("button", { name: "发送 ↑" }).click();
  await expect(page.locator(".message.assistant")).toHaveCount(2);
  await page.goto("/characters");
  await expect(page.getByRole("heading", { name: "薇拉" })).toBeVisible();
  await page.getByRole("link", { name: "继续对话" }).click();
  await expect(page.getByText("接着聊吧", { exact: true })).toBeVisible();
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
  await expect(page.getByLabel("名字", { exact: true })).toHaveValue("薇拉");
  expect(errors).toEqual([]);
});

test("failed chat retry preserves one user turn", async ({ page, request }) => {
  const response = await request.post("/api/characters/generate", {
    data: { description: "测试角色" },
  });
  const character = await response.json();
  await page.goto(`/characters/${character.id}/chat`);
  await page.getByLabel("消息", { exact: true }).fill("重试测试");
  let intercepted = false;
  await page.route("**/api/conversations/*/messages", async (route) => {
    if (route.request().method() === "POST" && !intercepted) {
      intercepted = true;
      // Let the backend commit the turn, then simulate a lost response.
      await route.fetch();
      await route.fulfill({
        status: 502,
        contentType: "application/json",
        body: JSON.stringify({ detail: "测试网络响应丢失" }),
      });
    } else await route.continue();
  });
  await page.getByRole("button", { name: "发送 ↑" }).click();
  await expect(page.locator(".error[role=alert]")).toContainText(
    "测试网络响应丢失",
  );
  await page.getByRole("button", { name: "重试这条消息" }).click();
  await expect(page.locator(".message.user")).toHaveCount(1);
  await expect(page.locator(".message.assistant")).toHaveCount(1);
  await expect(page.getByLabel("消息", { exact: true })).toHaveValue("");
});

test("portrait selection cannot bypass a stale profile conflict", async ({
  page,
  request,
}) => {
  const created = await request.post("/api/characters/generate", {
    data: { description: "版本冲突测试角色" },
  });
  const character = await created.json();
  const base = `/api/characters/${character.id}`;
  await request.post(`${base}/images/generate`, { data: {} });
  await page.goto(`/characters/${character.id}/edit`);
  await page.getByLabel("名字", { exact: true }).fill("此页未保存的名字");
  const otherPage = await request.patch(base, {
    data: {
      profile: { ...character.profile, name: "其他页面保存的名字" },
      expected_version: 1,
    },
  });
  expect(otherPage.ok()).toBeTruthy();
  await page.getByRole("button", { name: "选用此版" }).click();
  await expect(page.getByText("使用中", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "保存修改" }).click();
  await expect(page.locator(".error[role=alert]")).toContainText(
    "角色已在其他页面更新",
  );
  const saved = await (await request.get(base)).json();
  expect(saved.profile.name).toBe("其他页面保存的名字");
  expect(saved.current_image_id).not.toBeNull();
});
