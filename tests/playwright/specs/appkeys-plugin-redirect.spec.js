const {test, expect} = require("../fixtures");

test.describe("Appkeys Plugin", async () => {
    test("normal", async ({page, baseURL, loginApi, appkeysApi}) => {
        await loginApi.loginDefault();

        const [token, authUrl] = await appkeysApi.request("TestApp");
        appkeysApi.startPolling(token);

        await page.goto(authUrl);

        await expect(page).toHaveTitle("OctoPrint App Authentication");
        await expect(page.locator("#auth-choice")).toBeVisible();

        await page.getByTestId("auth-reject").click();

        await expect(page).toHaveURL(authUrl);
        await expect(page.locator("#auth-choice")).not.toBeVisible();
        await expect(page.locator("#auth-done")).toBeVisible();
    });

    test("https redirect ignored", async ({page, baseURL, loginApi, appkeysApi}) => {
        await loginApi.loginDefault();

        const [token, authUrl] = await appkeysApi.request("TestApp");
        appkeysApi.startPolling(token);

        const redirectUrl = "https://octoprint.org";
        const pageUrl = authUrl + "?redirect=" + encodeURI(redirectUrl);
        await page.goto(pageUrl);

        await expect(page).toHaveTitle("OctoPrint App Authentication");
        await expect(page.locator("#auth-choice")).toBeVisible();

        await page.getByTestId("auth-reject").click();

        await expect(page).toHaveURL(pageUrl);
        await expect(page.locator("#auth-choice")).not.toBeVisible();
        await expect(page.locator("#auth-done")).toBeVisible();
    });

    test("javascript redirect ignored", async ({page, baseURL, loginApi, appkeysApi}) => {
        await loginApi.loginDefault();

        const [token, authUrl] = await appkeysApi.request("TestApp");
        appkeysApi.startPolling(token);

        const redirectUrl = "javascript:alert(document.domain)";
        const pageUrl = authUrl + "?redirect=" + encodeURI(redirectUrl);
        await page.goto(pageUrl);

        const alerts = [];
        page.on("dialog", async (dialog) => {
            const msg = dialog.message();
            console.log("Received alert:", msg);
            alerts.push(msg);
            dialog.accept();
        });

        await expect(page).toHaveTitle("OctoPrint App Authentication");
        await expect(page.locator("#auth-choice")).toBeVisible();

        await page.getByTestId("auth-reject").click();

        await expect(page).toHaveURL(pageUrl);
        await expect(page.locator("#auth-choice")).not.toBeVisible();
        await expect(page.locator("#auth-done")).toBeVisible();

        expect(alerts.length).toBe(0);
    });
});
