import os
import re

from pydantic import BaseModel

ROMAN_NUMERAL = re.compile(
    "^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$", re.IGNORECASE
)


class Achievement(BaseModel):
    key: str = ""
    name: str = ""
    description: str = ""
    hidden: bool = False
    nag: bool = False
    timebased: bool = False

    @property
    def icon(self):
        key = self.key
        if "_" in key and ROMAN_NUMERAL.match(key.rsplit("_", 1)[1]):
            key = key.rsplit("_", 1)[0]

        if os.path.exists(
            os.path.join(os.path.dirname(__file__), "static", "img", f"{key}.svg")
        ):
            return f"{key}"
        else:
            return "trophy"


class AchievementsMetaClass(type):
    achievements = {}
    key_to_attr = {}

    def __new__(mcs, name, bases, args):
        cls = type.__new__(mcs, name, bases, args)

        for key, value in args.items():
            if isinstance(value, Achievement):
                value.key = key.lower()
                mcs.achievements[key] = value
                mcs.key_to_attr[key.lower()] = key

        return cls

    def all(cls):
        return cls.achievements.values()

    def get(cls, key):
        attr = cls.key_to_attr.get(key)
        if not attr:
            return None

        return cls.achievements.get(attr)


class Achievements(metaclass=AchievementsMetaClass):
    ## basics

    THE_WIZARD = Achievement(
        name="The Wizard",
        description="Complete the first run setup wizard.",
    )

    ONE_SMALL_STEP_FOR_MAN = Achievement(
        name="That's One Small Step For (A) Man", description="Finish your first print."
    )

    ADVENTURER = Achievement(
        name="The Adventurer",
        description="Install a plugin from the repository.",
    )

    TINKERER = Achievement(
        name="The Tinkerer",
        description="Install a plugin from a URL.",
    )

    BETTER_SAFE_THAN_SORRY = Achievement(
        name="Better Safe Than Sorry",
        description="Create a backup.",
    )

    ## print duration

    HALF_MARATHON = Achievement(
        name="Half Marathon",
        description="Finish a print that took longer than 12 hours.",
        nag=True,
    )

    MARATHON = Achievement(
        name="Marathon",
        description="Finish a print that took longer than 24 hours.",
        nag=True,
    )

    SPRINT = Achievement(
        name="Sprint",
        description="Finish a print that took less than 10 minutes.",
    )

    ACHIEVEMENT_NOT_FOUND = Achievement(
        name="Achievement Not Found",
        description="Reach a total print duration of 404 hours",
        hidden=True,
        nag=True,
    )

    ## print count

    CANT_GET_ENOUGH = Achievement(
        name="Can't Get Enough",
        description="Finish 10 prints in one day.",
        nag=True,
        timebased=True,
    )

    THE_MANUFACTURER_I = Achievement(
        name="The Manufacturer", description="Finish 10 prints.", nag=True
    )

    THE_MANUFACTURER_II = Achievement(
        name="The Manufacturer II",
        description="Finish 100 prints.",
        hidden=True,
        nag=True,
    )

    THE_MANUFACTURER_III = Achievement(
        name="The Manufacturer III",
        description="Finish 1000 prints.",
        hidden=True,
        nag=True,
    )

    ## date or date range specific

    HAPPY_BIRTHDAY_FOOSEL = Achievement(
        name="Happy Birthday, foosel",
        description="Start a print on foosel's birthday, March 21st.",
        hidden=True,
        timebased=True,
    )

    HAPPY_BIRTHDAY_OCTOPRINT = Achievement(
        name="Happy Birthday, OctoPrint",
        description="Start a print on OctoPrint's birthday, December 25th.",
        hidden=True,
        timebased=True,
    )

    SPOOKY = Achievement(
        name="Spooky",
        description="Start a print on Halloween, October 31st.",
        hidden=True,
        timebased=True,
    )

    SANTAS_LITTLE_HELPER = Achievement(
        name="Santa's Little Helper",
        description="Start a print between December 1st and December 24th.",
        hidden=True,
        timebased=True,
    )

    ## weekday specific

    TGIF = Achievement(
        name="TGIF",
        description="Start a print on a Friday.",
        timebased=True,
    )

    WEEKEND_WARRIOR = Achievement(
        name="Weekend Warrior",
        description="Start prints on four consecutive weekends.",
        timebased=True,
    )

    ## time specific

    EARLY_BIRD = Achievement(
        name="Early Bird",
        description="Start a print between 03:00 and 07:00.",
        hidden=True,
        timebased=True,
    )

    NIGHT_OWL = Achievement(
        name="Night Owl",
        description="Start a print between 23:00 and 03:00.",
        hidden=True,
        timebased=True,
    )

    ## file management

    CLEAN_HOUSE_I = Achievement(
        name="Clean House",
        description="Delete 100 files.",
        hidden=True,
    )

    CLEAN_HOUSE_II = Achievement(
        name="Clean House II",
        description="Delete 500 files.",
        hidden=True,
    )

    CLEAN_HOUSE_III = Achievement(
        name="Clean House III",
        description="Delete 1000 files.",
        hidden=True,
    )

    HEAVY_CHONKER = Achievement(
        name="Heavy Chonker",
        description="Upload a GCODE file larger than 500MB.",
    )

    THE_COLLECTOR_I = Achievement(
        name="The Collector",
        description="Upload 100 files.",
        hidden=True,
        nag=True,
    )

    THE_COLLECTOR_II = Achievement(
        name="The Collector II",
        description="Upload 500 files.",
        hidden=True,
        nag=True,
    )

    THE_COLLECTOR_III = Achievement(
        name="The Collector III",
        description="Upload 1000 files.",
        hidden=True,
        nag=True,
    )

    THE_ORGANIZER = Achievement(
        name="The Organizer",
        description="Create a folder.",
        hidden=True,
    )

    ## mishaps

    ALL_BEGINNINGS_ARE_HARD = Achievement(
        name="All Beginnings Are Hard", description="Cancel your first print."
    )

    ONE_OF_THOSE_DAYS = Achievement(
        name="Must Be One Of Those Days",
        description="Cancel ten consecutive prints on the same day.",
        hidden=True,
        timebased=True,
    )

    SO_CLOSE = Achievement(
        name="So Close",
        description="Cancel a print job at 95% progress or more.",
        hidden=True,
    )

    ## misc

    CROSSOVER_EPISODE = Achievement(
        name="What Is This, A Crossover Episode?",
        description="Connect to a printer running Klipper.",
        hidden=True,
    )

    HANG_IN_THERE = Achievement(
        name="Hang In There!",
        description="Pause the same print ten times.",
        hidden=True,
    )

    MASS_PRODUCTION = Achievement(
        name="Mass Production",
        description="Finish a print of the same file five times in a row.",
        hidden=True,
        nag=True,
    )

    WHAT_COULD_POSSIBLY_GO_WRONG = Achievement(
        name="What Could Possibly Go Wrong?",
        description="Start a print with an active undervoltage issue.",
        hidden=True,
    )


if __name__ == "__main__":
    import json

    achievements = Achievements.all()

    print("const ACHIEVEMENTS = ", end="")
    print(
        json.dumps(
            {
                a.key: {"name": a.name, "hidden": a.hidden}
                for a in sorted(achievements, key=lambda x: x.key)
            },
            indent=2,
        )
    )
