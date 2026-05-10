from enum import IntEnum

class Color (IntEnum):
    WHITE = 0
    BLACK = 1

    def __invert__(self):
        if self == self.WHITE:
            return self.BLACK
        else:
            return self.WHITE
