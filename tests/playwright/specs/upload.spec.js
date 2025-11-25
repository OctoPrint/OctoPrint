const {test, expect} = require("../fixtures");

const gcodeName = "e2e-测试.gcode"; // non ascii name to protect against regressions like #5206
const gcodeContent =
    "M117 I'm just a test upload during E2E\nG28 X0 Y0\nM117 That is all folks!";

test("Successful upload", async ({page, ui, filesApi}) => {
    await ui.gotoLoggedInCore();
    await filesApi.ensureFileUnknown("local", gcodeName);

    await page.getByTestId("storage-selector-local").click();
    await expect(page.getByTestId("storage-selector-local")).toHaveClass(/active/);

    await page.getByTestId("upload").setInputFiles({
        name: gcodeName,
        mimeType: "text/plain",
        buffer: Buffer.from(gcodeContent)
    });

    await expect(page.getByTestId("files-list")).toContainText(gcodeName);
});
