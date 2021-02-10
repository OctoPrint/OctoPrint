import {prepare_server, login, await_coreui} from "../util/util";

context("Upload tests", () => {
    const username = "admin";
    const password = "test";

    beforeEach(() => {
        prepare_server();

        // login
        login(username, password);

        cy.visit("/");
        await_coreui();
    });

    it("uploads file to local via button", () => {
        cy.get("[data-test-id=upload-local]").attachFile("e2e-test.gcode");
        cy.wait("@files");
        cy.get("[data-test-id=files-list]").contains("e2e-test.gcode");
    });
});
