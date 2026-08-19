"""
Abstract interface every platform driver implements.
"""

from abc import ABC, abstractmethod


class GraphDriver(ABC):

    @abstractmethod
    def connect(self):
        raise NotImplementedError

    @abstractmethod
    def close(self):
        raise NotImplementedError

    @abstractmethod
    def clear_database(self):
        raise NotImplementedError

    @abstractmethod
    def load_nodes(self, nodes: list[dict], batch_size: int) -> float:
        raise NotImplementedError

    @abstractmethod
    def load_edges(self, edges: list[dict], batch_size: int) -> float:
        raise NotImplementedError

    @abstractmethod
    def create_primary_index(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def create_secondary_index(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def run_read_query(self, cypher: str, aql: str, params: dict) -> list:
        raise NotImplementedError

    @abstractmethod
    def get_footprint(self) -> dict:
        raise NotImplementedError
