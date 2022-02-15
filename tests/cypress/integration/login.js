import {prepare_server, await_coreui, await_loginui, login} from "../util/util";

context("Login tests", () => {
    const username = "admin";
    const password = "test";

    beforeEach(() => {
        prepare_server();
    });

    context("Successful login", () => {
        beforeEach(() => {
            cy.visit("/?l10n=en");
            await_loginui();
            cy.location().should((loc) => {
                expect(loc.pathname).to.eq("/login/");
            });
        });

        it("logs in", () => {
            cy.get("[data-test-id=login-username]").type(username);
            cy.get("[data-test-id=login-password]").type(password);

            cy.get("[data-test-id=login-submit]").click({force: true});
            cy.wait("@login");

            await_coreui();

            cy.get("[data-test-id=login-menu-title]").should("contain", username);
            cy.getCookie("session_P5000").should("exist");
            cy.getCookie("remember_token_P5000").should("not.exist");
            cy.location().should((loc) => {
                expect(loc.hash).to.eq("#temp");
            });
        });

        it("logs in with remember me", () => {
            cy.get("[data-test-id=login-username]").type(username);
            cy.get("[data-test-id=login-password]").type(password);
            cy.get("[data-test-id=login-remember-me]").click();

            cy.get("[data-test-id=login-submit]").click({force: true});
            cy.wait("@login");

            await_coreui();

            cy.get("[data-test-id=login-menu-title]").should("contain", username);
            cy.getCookie("session_P5000").should("exist");
            cy.getCookie("remember_token_P5000").should(($cookie) => {
                expect($cookie).to.have.property("value");
                expect($cookie.value).to.match(new RegExp("^" + username + "|"));
            });
            cy.location().should((loc) => {
                expect(loc.hash).to.eq("#temp");
            });
        });
    });

    context("Successful logout", () => {
        it("logs out", () => {
            // login
            login(username, password);

            cy.visit("/?l10n=en");

            await_coreui();

            cy.get("[data-test-id=login-menu]").click();
            cy.get("[data-test-id=logout-submit]").click();
            cy.wait("@logout");

            await_loginui();
            cy.location().should((loc) => {
                expect(loc.pathname).to.eq("/login/");
            });
        });
    });

    context("Unauthorized login attempts", () => {
        beforeEach(() => {
            cy.visit("/?l10n=en");
            await_loginui();
            cy.location().should((loc) => {
                expect(loc.pathname).to.eq("/login/");
            });
        });

        it("uses wrong user name", () => {
            cy.get("[data-test-id=login-username]").type("idonotexist");
            cy.get("[data-test-id=login-password]").type("test");
            cy.get("[data-test-id=login-submit]").click();
        });

        it("uses wrong password", () => {
            cy.get("[data-test-id=login-username]").type("admin");
            cy.get("[data-test-id=login-password]").type("wrongpassword");
            cy.get("[data-test-id=login-submit]").click();
        });

        afterEach(() => {
            cy.get("[data-test-id=login-title]")
                .should("be.visible")
                .should("contain", "Please log in");
            cy.get("[data-test-id=login-error]")
                .should("be.visible")
                .should("contain", "Incorrect username or password");
        });
    });
});
