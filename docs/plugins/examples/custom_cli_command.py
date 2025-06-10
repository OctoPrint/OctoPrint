# Needs OctoPrint 1.3.x or newer

import click


def clitest_commands(*args, **kwargs):
    @click.command("greet")
    @click.option("--greeting", "-g", default="Hello", help="The greeting to use")
    @click.argument("name", default="World")
    def greet_command(greeting, name):
        """Greet someone by name, the greeting can be customized."""
        click.echo(f"{greeting} {name}!")

    @click.command("random")
    @click.argument("name", default="World")
    @click.pass_context
    def random_greet_command(ctx, name):
        """Greet someone by name with a random greeting."""

        greetings = [
            "Hello",
            "Buon giorno",
            "Hola",
            "Konnichiwa",
            "Oh hai",
            "Hey",
            "Salve",
        ]

        from random import randrange

        greeting = greetings[randrange(0, len(greetings))]
        ctx.invoke(greet_command, greeting=greeting, name=name)

    return [greet_command, random_greet_command]


__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_hooks__ = {"octoprint.cli.commands": clitest_commands}
