const {test, expect} = require("../fixtures");

const gcodeName = "e2e-test.gcode";
const gcodeContent =
    "M117 I'm just a test upload during E2E\nG28 X0 Y0\nM117 That is all folks!";

test("Successful upload", async ({page, ui, filesApi}) => {
    await ui.gotoLoggedInCore();
    await filesApi.ensureFileUnknown("local", gcodeName);

    await page.getByTestId("upload-local").setInputFiles({
        name: gcodeName,
        mimeType: "text/plain",
        buffer: Buffer.from(gcodeContent)
    });

    await expect(page.getByTestId("files-list")).toContainText(gcodeName);
});
