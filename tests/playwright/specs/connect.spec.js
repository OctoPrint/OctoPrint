// @ts-check
const {test, expect} = require("../fixtures");

test.describe("Printer connection", () => {
    test.beforeEach(async ({ui, connectionApi}) => {
        await ui.gotoLoggedInCore();
        const response = await connectionApi.disconnect();
        await expect(response.ok()).toBeTruthy();
    });

    test("connect & disconnect against virtual printer", async ({page}) => {
        await expect(page.getByTestId("state-string")).toHaveText("Offline");

        // Connect
        await page.getByTestId("connection-ports").selectOption("VIRTUAL");
        await page.getByTestId("connection-baudrates").selectOption("AUTO");
        await page.getByTestId("connection-printer-profiles").selectOption("Default");

        await expect(page.getByTestId("connection-connect")).toHaveText("Connect");
        await page.getByTestId("connection-connect").click();

        // State should change to Operational
        await expect(page.getByTestId("state-string")).toHaveText("Operational", {
            timeout: 15_000
        });

        // Connection panel should roll up
        await page.waitForFunction(
            () => {
                const element = document.querySelector(
                    "[data-test-id=sidebar-connection-content]"
                );
                if (!element) {
                    return false;
                }
                const parent = element.parentElement;
                return parent && parent.getBoundingClientRect().height === 0;
            },
            {timeout: 15_000}
        );

        // Disconnect
        await page.getByTestId("sidebar-connection-toggle").click();

        await expect(page.getByTestId("connection-connect")).toBeVisible();
        await expect(page.getByTestId("connection-connect")).toHaveText("Disconnect");
        await page.getByTestId("connection-connect").click();

        await expect(page.getByTestId("state-string")).toHaveText("Offline");
    });
});
