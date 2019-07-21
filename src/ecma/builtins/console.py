class Console:
    def log(self, *args):
        print(" ".join(str(a) for a in args))


console = Console()
