import sys
from time import sleep

from colorama import Fore


def handle_error(
    description,
    exception_details=None,
    wait_time=0,
    extra_description="",
    exit_=False,
):
    action = "Exiting" if exit_ else "Retrying"
    action += f" in {wait_time} seconds..." if wait_time else "..."
    exception_message = (
        f"\n{Fore.LIGHTBLACK_EX}{exception_details}"
        if exception_details is not None
        else ""
    )

    print(
        f"{Fore.RED}Error: {description}{extra_description}. {action}"
        f"{exception_message}{Fore.RESET}"
    )
    sleep(wait_time)

    if exit_:
        sys.exit(1)


class AuthenticationError(Exception):
    pass
