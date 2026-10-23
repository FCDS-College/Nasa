from abc import ABC, abstractmethod


class DocumentLoader(ABC):

    """Abstract interface for loaders that produce documents in the internal dict representation."""
    @abstractmethod
    def load(self, source):
        """
        Load documents from a source.

        Parameters
        ----------
        source:
            Input source such as a file, directory, or data source.

        Returns
        -------
        list[dict]
            Documents in the internal document representation.
        """
        pass

