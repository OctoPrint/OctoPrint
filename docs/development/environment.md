# Setting up a Development environment

## Obtaining, building and running the source

This describes the **general, platform agnostic** steps in obtaining, building and running.

### Prerequisites

  - [Stable Python 3](https://python.org) (check OctoPrint's README or `pyproject.toml` for the currently supported Python versions!)
  - [Git](https://git-scm.com)

How to install this depends on your Operative System and will not be explained here.

### Installation steps

  - Checkout the OctoPrint sources from their Git repository:
  
        git clone https://github.com/OctoPrint/OctoPrint.git
  
  - Enter the checked out source folder:
  
        cd OctoPrint
  
  - Create a virtual environment in the checked out source folder to use for
    installing and running OctoPrint and its dependencies. Creating virtual environments avoids potential versioning
    issues for the dependencies with system wide installed instances: 
    
        python -m venv venv
  
    :::{note}
    This assumes that the `python` binary is available directly on your `PATH`. If
    it cannot be found on your `PATH` like this you'll need to specify the full path here,
    e.g. `/path/to/python -m venv venv`
    :::
  
  - Activate the virtual environment
  
      - on Linux or macOS: 
  
            source venv/bin/activate
        
      - on Git Bash under Windows:
    
            source venv/Scripts/activate
  
  - Update `pip` in the virtual environment:
  
        pip install --upgrade pip
  
  - Install OctoPrint in ["editable" mode](https://pip.pypa.io/en/stable/cli/pip_install/#cmdoption-e),
    including its regular *and* development and plugin development dependencies:
  
        pip install -e '.[develop,plugins,docs]'
  
  - Set up the pre-commit hooks that make sure any changes you do adhere to the styling rules:
  
        pre-commit install
  
  - Tell `git` where to find the file with revisions to exclude for `git blame`:
  
        git config blame.ignoreRevsFile .git-blame-ignore-revs

When the virtual environment is activated you can then:

  - run the OctoPrint server via `octoprint serve`

and if your current working directory is OctoPrint's checked out source you can also:

  - run the unit test suite via `go-task test-unit`
  - run the e2e test suite from the checked out source folder via `go-task test-e2e`
  - trigger the pre-commit check suite via `go-task pre-commit`
  - rebuild `.css` files from `.less` sources. See `octoprint dev css:build --help`
  - build the documentation running `go-task docs-build` (the documentation will be 
    available in the newly created `docs/_build` directory)
  - serve the documentation with enabled automatic reload by running `go-task docs-serve`,
    it's then available under `http://localhost:8000` in your browser
  - check whether there are newer versions of OctoPrint's dependencies available via
    `go-task check-deps`
  - update, compile and bundle OctoPrint's translation files via `go-task babel-refresh`,
    `go-task babel-compile` and `go-task babel-bundle` respectively
  - check out even more options with `go-task --list`


Additionally:

  - running `git commit` will trigger a `pre-commit` run on your changes to make sure everything is properly
    formatted and linted
  - `git blame` will ignore past revisions that were only reformatting the source code, as
    listed in `.git-blame-ignore-revs`

## IDE Setup

:::{note}
Using another IDE than the ones below? Please send a
[Pull Request](https://github.com/OctoPrint/OctoPrint/blob/master/CONTRIBUTING.md#pull-requests) to get the necessary
steps into this guide!
:::

### Visual Studio Code

  - Install Visual Studio Code from [code.visualstudio.com](https://code.visualstudio.com/Download)
  - Click on "File", then "Open Folder", and select OctoPrint's checkout folder (e.g. `~/devel/OctoPrint` or `C:\Devel\OctoPrint`)
  - Create a directory `.vscode` if not already present in the root of the project
  - Create the following files inside the `.vscode` directory[^1]:

    - `settings.json`:

      ``` json
      {
        "python.defaultInterpreterPath": "venv/bin/python",
        "editor.formatOnSave": true,
        "[python]": {
          "editor.formatOnSave": true,
          "editor.codeActionsOnSave": {
            "source.fixAll.ruff": "explicit",
            "source.organizeImports": "explicit"
          },
          "editor.defaultFormatter": "charliermarsh.ruff"
        },
        "python.linting.pylintEnabled": false,
        "python.linting.flake8Enabled": false,
        "python.linting.enabled": true,
        "python.testing.unittestEnabled": false,
        "python.testing.pytestEnabled": true
      }
      ```
    - `tasks.json`:

      ```json
      {
        "version": "2.0.0",
        "tasks": [
          {
            "label": "Build: Clean Build Artifacts",
            "type": "shell",
            "command": "${command:python.interpreterPath} ./setup.py clean"
          },
          {
            "label": "Build: Install dependencies",
            "type": "shell",
            "command": "${command:python.interpreterPath} -m pip install -e .[develop,plugins,docs]"
          },
          {
            "label": "Build: Clean & Install Deps",
            "dependsOn": ["Build: Clean Build Artifacts", "Build: Install dependencies"],
            "problemMatcher": []
          }
        ]
      }
      ```

    - `launch.json`

      ```json
      {
        "version": "0.2.0",
        "configurations": [
          {
            "name": "OctoPrint",
            "type": "debugpy",
            "request": "launch",
            "module": "octoprint",
            "args": [
              "serve",
              "--debug"
            ],
            "cwd": "${workspaceFolder}/src",
            "preLaunchTask": "Build: Clean & Install Deps"
          }
        ]
      }
      ```

  - In the terminal install the python extension by running this command:

        code --install-extension ms-python.python

    and the ruff extension by running this command:

        code --install-extension charliermarsh.ruff

Summary of Visual Studio Code config:

  - Pressing `F5` will now start OctoPrint in debug mode
  - The unit tests should be discovered and startable through the corresponding tab
  - Your terminal inside Visual Studio Code uses the virtual python environment
  - Saving a file will run an auto formatter and import sort

[^1]: You might be wondering why those files aren't included in OctoPrint's sources. The idea is to keep things
IDE agnostic and leave it to everyone themselves what kind of editor or IDE they want to use.

### PyCharm

:::{warning}
I no longer use PyCharm and thus can no longer check if the setup actually works. This section hasn't
been updated in half a decade now and I would be very surprised if everything still works as documented here.
Consider this very much outdated!
:::



  - "File" > "Open ...", select OctoPrint checkout folder (e.g. `~/devel/OctoPrint` or `C:\Devel\OctoPrint`)
  - Register virtual environments:
  
    - **(Linux, Windows)** "File" > "Settings ..." > "Project: OctoPrint" > "Project Interpreter" > "Add local ...",
      select OctoPrint `venv` folder (e.g. `~/devel/OctoPrint/venv` or `C:\Devel\OctoPrint\venv`).
    - **(macOS)** "PyCharm" > "Preferences ..." > "Project: OctoPrint" > "Project Interpreter" > "Add ..." >
      "Virtualenv Environment > "Existing Environment", select OctoPrint `venv` folder (e.g. `~/devel/OctoPrint/venv`).
  
    If desired, repeat for any other additional Python venvs (e.g. for separate Python 3 versions).
  
  - Right click "src" in project tree, mark as source folder
  - Add Run/Debug Configuration, select "Python":
  
      - Name: OctoPrint server
      - Module name: `octoprint`
      - Parameters: `serve --debug`
      - Project: `OctoPrint`
      - Python interpreter: Project Default
      - Working directory: the OctoPrint checkout folder (e.g. `~/devel/OctoPrint` or `C:\Devel\OctoPrint`)
      - If you want build artifacts to be cleaned up on run (recommended): "Before Launch" > "+" > "Run external tool" > "+"
  
        - Name: Clean build directory
        - Program: `$ModuleSdkPath$`
        - Parameters: `setup.py clean`
        - Working directory: `$ProjectFileDir$`
  
    - If you want dependencies to auto-update on run if necessary (recommended): "Before Launch" > "+" > "Run external tool" > "+"
  
        - Name: Update OctoPrint dependencies
        - Program: `$ModuleSdkPath$`
        - Parameters: `-m pip install -e '.[develop,plugins]'`
        - Working directory: `$ProjectFileDir$`
  
      Note that sadly that seems to cause some hiccups on current PyCharm versions due to `$PyInterpreterDirectory$`
      being empty sometimes, so if this fails to run on your installation, you should update your dependencies manually
      for now.
  
  - Add Run/Debug Configuration, select "Python tests" and therein "pytest":
  
      - Name: OctoPrint tests
      - Target: Custom
      - Project: `OctoPrint`
      - Python interpreter: Project Default
      - Working directory: the OctoPrint checkout folder (e.g. `~/devel/OctoPrint` or `C:\Devel\OctoPrint`)
      - Just like with the run configuration for the server you can also have the dependencies auto-update on run of
        the tests, see above on how to set this up.
  
  - Add Run/Debug Configuration, select "Python":
  
      - Name: OctoPrint docs
      - Module name: `sphinx.cmd.build`
      - Parameters: `-v -T -E ./docs ./docs/_build -b html`
      - Project: `OctoPrint`
      - Python interpreter: `venv` environment
      - Working directory: the OctoPrint checkout folder (e.g. `~/devel/OctoPrint` or `C:\Devel\OctoPrint`)
      - Just like with the run configuration for the server you can also have the dependencies auto-update when building
        the documentation, see above on how to set this up.
  
    Note that this requires you to also have installed the additional `docs` dependencies into the Python 3 venv as
    described above via `pip install -e '.[develop,plugins,docs]'`.
  
  - Settings > Tools > File Watchers (you might have to enable this, it's a bundled plugin), add new:
  
      - Name: pre-commit
      - File type: Python
      - Scope: Module 'OctoPrint'
      - Program: `<OctoPrint venv folder>/bin/pre-commit` (Linux) or `<OctoPrint venv folder>/Scripts/pre-commit` (Windows)
      - Arguments: `run --hook-stage manual --files $FilePath$`
      - Output paths to refresh: `$FilePath$`
      - Working directory: `$ProjectFileDir$`
      - disable "Auto-save edited files to trigger the watched"
      - enable "Trigger the watched on external changes"

To switch between virtual environments (e.g. Python 3.9 and 3.14), all you need to do now is change the Project Default Interpreter and restart
OctoPrint. On current PyCharm versions you can do that right from a small selection field in the footer of the IDE.
Otherwise go through Settings.