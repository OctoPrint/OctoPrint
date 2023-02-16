const {test, expect} = require("../fixtures");

test("Error free page load", async ({page, ui}) => {
    const errors = [];
    page.on("pageerror", (error) => {
        errors.push(`[${error.name}] ${error.message}`);
    });
    page.on("console", (msg) => {
        if (msg.type() === "error") {
            errors.push(`[${msg.type()}] ${msg.text()}`);
        }
    });

    await ui.gotoLoggedInCore();

    await expect(errors).toStrictEqual([]);
});
