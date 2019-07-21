class Number(float):
    def __str__(self):
        if self.is_integer():
            return "%d" % self
        return super().__str__()

    def __add__(self, other):
        return Number(super().__add__(other))
