# Commit formatting

The format of the commit messages in OctoPrint's repository generally tries to follow the 
[conventional commit spec](https://www.conventionalcommits.org) to make the commit log
more uniform and easier to read and skim through, especially during release preparations.

This document describes how this is currently implemented.

Note that not all commits in OctoPrint's repository are following this format. Merge and
revert commits are kept on git's default formatting to make things easier when using
stock tooling, anything prior to June 2024 still uses [a different approach](https://gitmoji.dev),
and here and there a different type or scope than those documented gets (mis-)used out
of confusion at commit-time. 

Also, while contributors are welcome to use this format, it's not required from them 
either (and pull requests are usually squashed in any case on merge).

Consider the following more a guideline rather than a rule[^1], and a cheat sheet for developers
to hopefully make everything more uniform in the future.

[^1]: If it was a strict rule, there would be pre-commit powered linter in place 😉

## General commit

In general, conventionally formatted commits look like the following:

```none
<type>[(<scope>)][!]: <description>

<body>

<references>

<footer>
```

Non-exhaustive lists of both `type`s and optional `scope`s can be found below.

An optional `!` following the `type` or `type(scope)` tag designates a *breaking change*.

The optional multiline `body` must be separated from the header line by one empty line. it should
describe the commit further, as needed.

Any optional `references` should be separated from the previous part by one empty line. This is where
the [GitHub specific linking keywords](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue#linking-a-pull-request-to-an-issue-using-a-keyword)
(e.g. `Closes #1234` or `Fixes #5678`) go.

The optional multiline `footer` must be separated from the body (or header, if there is no body) by
one empty line. 

### Merge & revert commits

Contrary to the format described above, both merge and revert commits follow the default `git` format:

```none
Merge branch '<merged branch>' into <merge target>
```

```none
Revert "<commit message>"
```

### Examples

```
feat: add achievements plugin
```

```
fix(ci): update raspberrypi keyfile to fix canary build
```

```
ux: improve readability of progress bars

Bringing back the optics that got lost after merging #4105, now that
browsers have more options to make this stuff work.

Also introduced a new ko-binding `progressbar` for easier implementation
of dynamic progress bars.

Closes #5267
```

```none
Merge branch 'bugfix' into dev
```

```none
Revert "fix(ci): update raspberrypi keyfile to fix canary build"
```

## Types

The following types can be used. This list is non-exhaustive and will be extended as needed.

- ``chore``: general chores (e.g. version bumps, dependency bumps, release preparations, ...)
- ``ci``: continuous integration related (e.g. workflow adjustments)
- ``docs``: documentation related changed (includes full blown docs as well as bundled markdown files)
- ``dx``: developer experience related (e.g. introduction of a new task in the `Taskfile`, improvement of existing tooling)
- ``feat``: adding a new feature (e.g. a new bundled plugin, new UI feature, ...)
- ``fix``: bug or security fix
- ``meta``: updating meta files (e.g. `.github/*.yml` and similar, minus the workflows, those are covered under `ci`)
- ``refactor``: refactoring related, no (intentional) public API changes
- ``style``: code style related changes (e.g. pre-commit configuration updates and their required code adjustments)
- ``test``: test related changes (unit tests, e2e tests)
- ``wip``: commit is part of a work in progress & will likely be squashed later

## Scopes

The following scopes can be used. This list is non-exhaustive and will be extended as needed.

- ``achievements``: bundled achievements plugin
- ``analysis``: related to the file analysis
- ``api``: related to the public REST API
- ``appkeys``: bundled application keys plugin
- ``auth``: authentication and session management
- ``backup``: bundled backup plugin
- ``ccmgr``: bundled custom control manager plugin
- ``ci``: CI related
- ``cli``: related to the command line interface
- ``coreui``: related to the core user interface
- ``corewizard``: bundled corewizard plugin
- ``discovery``: bundled discovery plugin 
- ``docs``: documentation related
- ``e2e``: related to the Playwright based end-to-end tests
- ``errortracking``: bundled errortracking plugin
- ``eventmgr``: bundled event manager plugin
- ``gcv``: bundled gcode viewer plugin
- ``healthcheck``: bundled health check plugin
- ``i18n``: translation files
- ``jsclient``: JavaScript client library
- ``plugins``: anything plugins related
- ``pmgr``: bundled plugin manager plugin
- ``serial``: bundled serial connector plugin
- ``settings``: settings related
- ``storage``: related to the internal storage API
- ``swu``: bundled software update plugin
- ``systeminfo``: systeminfo related
- ``timelapse``: bundled timelapse plugin
- ``tornado``: related to the Tornado implementation
- ``tracking``: bundled anonymous usage tracking plugin
- ``upmgr``: bundled upload manager plugin
- ``ux``: related to the general user experience
- ``virtualprinter``: bundled virtual printer plugin