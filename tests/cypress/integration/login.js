describe('Login tests', () => {
    const username = 'admin';
    const password = 'test';

    describe('Successful login', () => {

        it('logs in', () => {
            cy.visit('/');
            cy.window()
                .should('have.nested.property', 'OctoPrint.loginui.startedUp', true);

            cy.get('#login-user')
                .type(username);
            cy.get('#login-password')
                .type(password);

            cy.get('#login-button')
                .click();
            cy.window({timeout: 30000})
                .should('have.nested.property', 'OctoPrint.coreui.startedUp', true);

            cy.get('#navbar_login a.dropdown-toggle span')
                .should('contain', username);
            cy.getCookie('session_P5000')
                .should('exist');
            cy.getCookie('remember_token_P5000')
                .should('not.exist');
            cy.url()
                .should('contain', '#temp');
        });

        it('logs in with remember me', () => {
            cy.visit('/');
            cy.window()
                .should('have.nested.property', 'OctoPrint.loginui.startedUp', true);

            cy.get('#login-user')
                .type(username);
            cy.get('#login-password')
                .type(password);
            cy.get('#login-remember')
                .click();

            cy.get('#login-button')
                .click();
            cy.window({timeout: 30000})
                .should('have.nested.property', 'OctoPrint.coreui.startedUp', true);

            cy.get('#navbar_login a.dropdown-toggle span')
                .should('contain', username);
            cy.getCookie('session_P5000')
                .should('exist');
            cy.getCookie('remember_token_P5000')
                .should(($cookie) => {
                    expect($cookie).to.have.property('value');
                    expect($cookie.value).to.match(new RegExp('^' + username + '\|'));
                });
            cy.url()
                .should('contain', '#temp');
        });

        it('logs in and logs out again', () => {
            cy.visit('/');
            cy.window()
                .should('have.nested.property', 'OctoPrint.loginui.startedUp', true);

            cy.get('#login-user')
                .type(username);
            cy.get('#login-password')
                .type(password);

            cy.get('#login-button')
                .click();

            cy.window({timeout: 30000})
                .should('have.nested.property', 'OctoPrint.coreui.startedUp', true);

            cy.get('#navbar_login a.dropdown-toggle')
                .click();
            cy.get('#logout_button')
                .click();

            cy.window({timeout: 30000})
                .should('have.nested.property', 'OctoPrint.loginui.startedUp', true);

            cy.get('h2.form-signin-heading')
                .should('be.visible')
                .should('contain', 'Please log in');
        })
    });

    context('Unauthorized login attempts', () => {
        it('uses wrong user name', () => {
            cy.visit('/');
            cy.window()
                .should('have.nested.property', 'OctoPrint.loginui.startedUp', true);

            cy.get('#login-user')
                .type('idonotexist');
            cy.get('#login-password')
                .type('test');
            cy.get('#login-button')
                .click();
        });

        it('uses wrong password', () => {
            cy.visit('/');
            cy.window()
                .should('have.nested.property', 'OctoPrint.loginui.startedUp', true);

            cy.get('#login-user')
                .type('admin');
            cy.get('#login-password')
                .type('wrongpassword');
            cy.get('#login-button')
                .click();
        });

        afterEach(() => {
            cy.get('h2.form-signin-heading')
                .should('be.visible')
                .should('contain', 'Please log in');
            cy.get('#login-error')
                .should('be.visible')
                .should('contain', 'Incorrect username or password');
        });
    });
});
