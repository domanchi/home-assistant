from datetime import datetime

from .serializer import serialize_to_yaml
from .cadence import Cadence
from .task import tasklist


def run() -> None:
    serialize_to_yaml(*tasklist)
