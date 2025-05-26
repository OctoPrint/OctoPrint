const {test, expect} = require("../fixtures");

test.describe.parallel("Page loads", async () => {
    ["recovery", "rescue"].forEach((endpoint) => {
        ["", "/"].forEach((suffix) => {
            test(`endpoint: ${endpoint}${suffix}`, async ({page, baseURL, loginApi}) => {
                await loginApi.loginDefault();
                await page.goto(`${baseURL}/${endpoint}${suffix}`);

                await expect(page).toHaveTitle("OctoPrint Recovery");
                await expect(page).toHaveURL(`${baseURL}/recovery/`);
                await expect(page.locator("#recovery")).toBeVisible();
            });
        });
    });
});
