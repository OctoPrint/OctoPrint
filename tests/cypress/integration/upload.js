import {prepare_server, login, ensure_file_unknown, await_coreui} from "../util/util";

context("Upload tests", () => {
    const username = "admin";
    const password = "test";
    const upload = "e2e-test.gcode";

    beforeEach(() => {
        prepare_server();

        // login
        login(username, password);

        // clean up file if needed
        ensure_file_unknown("local", upload);

        cy.visit("/");
        await_coreui();
    });

    it("uploads file to local via button", () => {
        cy.get("[data-test-id=upload-local]").attachFile(upload);
        cy.wait("@files");
        cy.get("[data-test-id=files-list]").contains(upload);
    });
});
