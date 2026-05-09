import { test, expect } from "@playwright/test";

test.describe("smoke", () => {
  test("home loads", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("body")).toBeVisible();
  });

  test("learn index loads", async ({ page }) => {
    await page.goto("/learn");
    await expect(page.locator("body")).toBeVisible();
  });

  test("systematic beginner lesson loads", async ({ page }) => {
    await page.goto("/learn/beginner/15-systematic-approach");
    await expect(page.locator("body")).toBeVisible();
  });
});
