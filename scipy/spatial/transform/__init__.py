import sys
import numpy as np

class Rotation:
    @classmethod
    def from_rotvec(cls, rotvec):
        return cls()
    def as_matrix(self):
        return np.eye(3)
    @classmethod
    def identity(cls):
        return cls()
