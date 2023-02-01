// @ts-check
const {test, expect} = require("../fixtures");

test("Open settings", async ({page, ui}) => {
    await ui.gotoLoggedInCore();

    // open settings dialog
    await page.getByTestId("settings-open").click();

    // verify it's open
    await expect(page.getByTestId("settings-dialog")).toBeVisible();
});

test.describe.parallel("Close settings", () => {
    test.beforeEach(async ({page, ui}) => {
        await ui.gotoLoggedInCore();
        await page.getByTestId("settings-open").click();
        await expect(page.getByTestId("settings-dialog")).toBeVisible();
    });

    test("via button", async ({page}) => {
        await page.getByTestId("settings-close-button").click();
    });

    test("via x", async ({page}) => {
        await page.getByTestId("settings-close-x").click();
    });

    test("via ESC", async ({page}) => {
        await page.getByTestId("settings-dialog").press("Escape");
    });

    test.fixme("via click outside", async ({page}) => {
        // TODO: this doesn't work yet
        await page.locator(".modal-scrollable").click();
    });

    test.afterEach(async ({page}) => {
        // verify it's closed
        await expect(page.getByTestId("settings-dialog")).not.toBeVisible();
    });
});
