from time import time

from colorama import Fore


class Status:
    def __init__(self, name, color, total):
        self.count = 0
        self.name = name
        self.color = color
        self.total = total

    def increment(self):
        self.count += 1

    def print(self, message, add=True):
        print(f"{self.color}{message}{Fore.RESET}")
        if add:
            self.increment()

    def report(self):
        try:
            percentage = self.count/self.total*100
        except ZeroDivisionError:
            percentage = 0

        return (
            f"*\t{self.color}{self.name}{Fore.RESET}: {self.count} "
            f"({percentage:.0f}%)"
        )


class Progress:
    def __init__(self, total):
        self.start_time = time()

        self.total = total
        self.generated = Status("Generated for cross-seeding", Fore.LIGHTGREEN_EX, total)
        self.already_exists = Status("Already exists", Fore.LIGHTYELLOW_EX, total)
        self.not_found = Status("Not found", Fore.LIGHTRED_EX, total)
        self.error = Status("Errors", Fore.RED, total)
        self.skipped = Status("Skipped", Fore.LIGHTBLACK_EX, total)

    def report(self):
        divider = f"\n{'-' * 50}"
        messages = '\n'.join(
            x.report()
            for x in (
                self.generated,
                self.already_exists,
                self.not_found,
                self.error,
                self.skipped,
            )
        )

        return (
            f"{divider}\nAnalyzed {self.total} local torrents in {time() - self.start_time:.2f} "
            f"seconds:\n{messages}{divider}"
        )
