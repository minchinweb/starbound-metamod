import sys
from pathlib import Path

import colorama
import minchin.text as text
import winshell
from invoke import run, task

SB_STEAM_ID = "211820"

SB_BASE_DIR = Path(r"D:\SteamLibrary\steamapps\common\Starbound")
SB_STEAM_MODS_DIR = Path( r"D:\SteamLibrary\steamapps\workshop\content\211820")

SB_UNIVERSE_DIR = SB_BASE_DIR / "storage" / "universe"
SB_PLAYER_DIR = SB_BASE_DIR / "storage" / "player"

SB_ASSETS = SB_BASE_DIR / "assets" / "packed.pak"

SB_ASSET_PACKER = SB_BASE_DIR / "win32" / "asset_packer.exe"
SB_ASSET_UNPACKER = SB_BASE_DIR / "win32" / "asset_unpacker.exe"
SB_DUMP_JSON = SB_BASE_DIR / "win32" / "dump_versioned_json.exe"
SB_LOAD_JSON = SB_BASE_DIR / "win32" / "make_version_json.exe"

STEAM_SB_MOD_URL = "http://steamcommunity.com/sharedfiles/filedetails/?id={}"


colorama.init()
GREEN = colorama.Fore.GREEN
RED = colorama.Fore.RED
YELLOW = colorama.Fore.YELLOW
RESET_ALL = colorama.Style.RESET_ALL


@task
def hello_world(ctx):
    print("Hello World!")


@task
def unpack_assets(ctx, source=SB_ASSETS, destination="unpacked"):
    """Unpack the game assets."""
    text.title("Asset Unpacker")

    source = Path(source)
    destination = Path(destination)

    # check source file
    if source.exists():
        print("Games Assets: {}FOUND{}!".format(GREEN, RESET_ALL))
    else:
        print("Game Assets: {}MISSING{}".format(RED, RESET_ALL))
        print("Exiting...")
        sys.exit(1)

    # check destination folder
    if destination.exists():
        # test if folder is empty
        if list(destination.rglob("*")):
            print("Destination Folder: {}Exists, Not Empty{}".format(YELLOW, RESET_ALL))
            print("    {}".format(destination.resolve()))
            ans = text.query_yes_no("    Empty Folder?")
            if ans == text.Answers.YES:
                winshell.delete_file(destination.rglob("*"), silent=True)
        else:
            print("Destination Folder: {}Exists, Empty{}!".format(GREEN, RESET_ALL))
    else:
        print("Destination Folder: {}MISSING{}".format(YELLOW, RESET_ALL))
        ans = text.query_yes_no("    Create?")
        if ans == text.Answers.YES:
            destination.mkdir(parents=True)
        else:
            print("Exiting...")
            sys.exit(1)

    # the actual unpacking!
    cmd = '"{}" "{}" "{}"'.format(
        SB_ASSET_UNPACKER,
        source,
        destination,
    )
    print("Unpacking...")
    run(cmd)
    print("{}Done!{}".format(GREEN, RESET_ALL))


@task
def unpack_steam_mods(
    ctx,
    source=SB_STEAM_MODS_DIR,
    destination="unpacked-mods",
    override_existing=False,
    skip_existing=False,
    verbose=False,
):
    """Unpack all steam mods."""
    text.title("Steam Mod Unpacker")

    count_skipped = 0
    count_unpacked = 0
    count_errorred = 0
    error_list = []

    source = Path(source)
    destination = Path(destination)

    # check source file
    if source.exists():
        print("Steam Mods: {}FOUND{}!".format(GREEN, RESET_ALL))
    else:
        print("Steam Mods: {}MISSING{}".format(RED, RESET_ALL))
        print("Exiting...")
        sys.exit(1)

    # check destination folder
    if destination.exists():
        # test if folder is empty
        if list(destination.rglob("*")):
            print("Destination Folder: {}Exists, Not Empty{}".format(YELLOW, RESET_ALL))
            print("    {}".format(destination.resolve()))
            ans = text.query_yes_no("    Empty Folder?", default="no")
            if ans == text.Answers.YES:
                winshell.delete_file(destination.rglob("*"), silent=True)
        else:
            print("Destination Folder: {}Exists, Empty{}!".format(GREEN, RESET_ALL))
    else:
        print("Destination Folder: {}MISSING{}".format(YELLOW, RESET_ALL))
        ans = text.query_yes_no("    Create?")
        if ans == text.Answers.YES:
            destination.mkdir(parents=True)
        else:
            print("Exiting...")
            sys.exit(1)

    print("Unpacking...")
    for fn in source.iterdir():
        if fn.is_dir():
            mod_id = fn.name
            mod_destination = destination / mod_id
            skip_this = False
            override_this = False
            if mod_destination.exists():
                if not override_existing and not skip_existing:
                    ans = text.query_yes_no_all_none(
                        (
                            "Destination folder for "
                            "mod {} exists. Override?".format(mod_id)
                        ),
                        default="none",
                    )
                    if ans == text.Answers.YES:
                        override_this = True
                    elif ans == text.Answers.NO:
                        skip_this = True
                    elif ans == text.Answers.ALL:
                        override_existing = True
                        override_this = True
                    elif ans == text.Answers.NONE:
                        skip_existing = True
                        skip_this = True

                if override_this or override_existing:
                    winshell.rmdir(mod_destination)
                else:
                    skip_this = True

            # the actual unpacking!
            if skip_this:
                if verbose:
                    print("    {}Skipping{} {}...".format(YELLOW, RESET_ALL, mod_id))
                count_skipped += 1
            else:
                if (fn / "contents.pak").exists():
                    cmd = '"{}" "{}" "{}"'.format(
                        SB_ASSET_UNPACKER,
                        fn / "contents.pak",
                        mod_destination,
                    )
                    try:
                        run(cmd)
                    except Exception as e:
                        # print(e)
                        count_errorred += 1
                        error_list.append(mod_id)
                    else:
                        count_unpacked += 1
                else:
                    print(
                        "    {}Skipping{}, missing file: {}".format(
                            YELLOW, RESET_ALL, (fn / "contents.pak")
                        )
                    )
                    count_skipped += 1

    print()
    print(
        (
            "{}Done!{} {} mods unpacked, {} skipped, and {} errorred.".format(
                GREEN, RESET_ALL, count_unpacked, count_skipped, count_errorred
            )
        )
    )
    if error_list:
        print("{}Errors{}: {}".format(YELLOW, RESET_ALL, ", ".join(error_list)))


@task(iterable=["mods"])
def copy_mods_to_server(
    ctx,
    source=SB_STEAM_MODS_DIR,
    destination=None,
    override_existing=False,
    skip_existing=False,
    update_existing=False,
    verbose=False,
    mods=None,
):
    """Copy and 'flat file' steam mods to server mod directory."""
    text.title("Copy and 'flat file' steam mods to server mod directory.")

    count_copied = 0
    count_updated = 0
    count_skipped = 0
    count_missing = 0
    count_errorred = 0
    missing_list = []
    error_list = []

    source = Path(source)
    # check source file
    if source.exists():
        print("Steam Mods: {}FOUND{}!".format(GREEN, RESET_ALL))
        print("    {}".format(source.resolve()))
    else:
        print("Steam Mods: {}MISSING{}".format(RED, RESET_ALL))
        print("    {}".format(source.resolve()))
        print("Exiting...")
        sys.exit(1)

    if destination:
        destination = Path(destination)
    else:
        print("Destination: {}UNDEFINED{}".format(RED, RESET_ALL))
        print("Exiting...")
        sys.exit(1)

    # check destination folder
    if destination.exists():
        # test if folder is empty, other than a "mods.txt" file
        other_files = set(destination.rglob("*")) - set(destination.rglob("mods.txt"))
        if other_files:
            print("Destination Folder: {}Exists, Not Empty{}".format(YELLOW, RESET_ALL))
            print("    {}".format(destination.resolve()))
            ans = text.query_yes_no("    Empty Folder?", default="no")
            if ans == text.Answers.YES:
                for x in other_files:
                    winshell.delete_file(str(x.resolve()), silent=True)

        else:
            print("Destination Folder: {}Exists, Empty{}!".format(GREEN, RESET_ALL))
    else:
        print("Destination Folder: {}MISSING{}".format(YELLOW, RESET_ALL))
        print("    {}".format(destination.resolve()))
        ans = text.query_yes_no("    Create?")
        if ans == text.Answers.YES:
            destination.mkdir(parents=True)
        else:
            print("Exiting...")
            sys.exit(1)

    if not mods:
        if (destination / "mods.txt").exists():
            with (destination / "mods.txt").open() as f:
                # drop everything after '#'
                mods = [line.split("#", 1)[0].strip() for line in f]
                # remove empty lines
                mods = [line for line in mods if line]
            print("Using 'mods.txt' in destination folder.")
        else:
            print(
                "{}Provide a list of the steam IDs of the mods you want to copy{}".format(
                    RED, RESET_ALL
                )
            )
            print("Exiting...")
            sys.exit(1)

    print("Coping...")
    for fn in source.iterdir():
        if fn.is_dir() and (fn.name in mods or mods[0].lower() == "all"):
            mod_source = fn / "contents.pak"
            if not mod_source.exists():
                print(
                    f"{YELLOW}Mod {mod_id} in non-typical format. Skipping.{RESET_ALL}"
                )
                count_skipped += 1
                continue

            mod_id = fn.name
            mod_destination = destination / f"{mod_id}.pak"
            skip_this = False
            override_this = False

            if mod_destination.exists():
                if update_existing:
                    # last modified time
                    source_mtime = mod_source.stat().st_mtime
                    destination_mtime = mod_destination.stat().st_mtime

                    if source_mtime > destination_mtime:
                        override_this = True
                        count_updated += 1

                if not override_existing and not skip_existing:
                    ans = text.query_yes_no_all_none(
                        (
                            "Destination file for "
                            "mod {} exists. Overwrite?".format(mod_id)
                        ),
                        default="none",
                    )
                    if ans == text.Answers.YES:
                        override_this = True
                    elif ans == text.Answers.NO:
                        skip_this = True
                    elif ans == text.Answers.ALL:
                        override_existing = True
                        override_this = True
                    elif ans == text.Answers.NONE:
                        skip_existing = True
                        skip_this = True

                if override_this or override_existing:
                    winshell.delete_file(str(mod_destination))
                else:
                    skip_this = True

            # the actual unpacking!
            if skip_this:
                if verbose:
                    print("    {}Skipping{} {}...".format(YELLOW, RESET_ALL, mod_id))
                count_skipped += 1
            else:
                winshell.copy_file(str(mod_source), str(mod_destination))
                count_copied += 1

    print("Check for completion...")
    for mod_id in mods:
        mod_destination = destination / f"{mod_id}.pak"
        if not mod_destination.exists():
            missing_list.append(mod_id)
            count_missing += 1

    print()
    print(
        (
            "{}Done!{} {} mods copied, {} updated, {} skipped, {} missing, and {} errorred.".format(
                GREEN,
                RESET_ALL,
                count_copied,
                count_updated,
                count_skipped,
                count_missing,
                count_errorred,
            )
        )
    )
    if missing_list:
        print(
            "{}Missing from source{}: {}".format(
                YELLOW, RESET_ALL, ", ".join(missing_list)
            )
        )
    if error_list:
        print("{}Errors{}: {}".format(YELLOW, RESET_ALL, ", ".join(error_list)))
