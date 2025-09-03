<!--
Thank you for your interest in contributing to OctoPrint, it's
highly appreciated!

Please make sure you have read the "guidelines for contributing" as
linked just above this form, there's a section on Pull Requests in there
as well which contains important information.

As a summary, please make sure you have ticked all points on this
checklist:
-->

- [ ] You have read through `CONTRIBUTING.md`
- [ ] Your changes are not possible to do through a plugin and relevant
  to a large audience (ideally all users of OctoPrint)
- [ ] If your changes are large or otherwise disruptive: You have
  made sure your changes don't interfere with current development by
  talking it through with the maintainers, e.g. through a
  Brainstorming ticket
- [ ] Your PR targets OctoPrint's `dev` branch
- [ ] Your PR was opened from a custom branch on your repository
  (no PRs from your version of `main`, `bugfix`, `next` or `dev`
  please), e.g. `wip/my_new_feature` or `wip/my_bugfix`
- [ ] Your PR only contains relevant changes: no unrelated files,
  no dead code, ideally only one commit - rebase and squash your PR
  if necessary!
- [ ] If your changes include style sheets: You have modified the
  `.less` source files, not the `.css` files (those are generated
  with `lessc`)
- [ ] You have tested your changes (please state how!) - ideally you
  have added unit tests
- [ ] You have run the existing unit tests against your changes and
  nothing broke (`pytest`)
- [ ] You have run the included `pre-commit` suite against your changes
  and nothing broke (`pre-commit run --all-files`)
- [ ] You have added yourself to the `AUTHORS.md` file :)

<!--
Describe your PR further using the template provided below. The more
details the better!
-->

#### What does this PR do and why is it necessary?

#### How was it tested? How can it be tested by the reviewer?

#### Was any kind of genAI (ChatGPT, Copilot etc) involved in creating this PR?

#### Any background context you want to provide?

#### What are the relevant tickets if any?

#### Screenshots (if appropriate)

#### Further notes

<!--
Be advised that your PR will be checked automatically by CI. Should any of the CI
checks fail, you will be expected to fix them before your PR will be reviewed, so
keep an eye on it!
-->
