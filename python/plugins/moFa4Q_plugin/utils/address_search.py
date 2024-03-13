from .search import Search


class AddressSearch(Search):

    def __init__(self, iface, filePath, lineEditSearch, pushButton):
        super().__init__(iface, filePath, lineEditSearch, pushButton)
