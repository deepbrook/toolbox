# Import Built-ins
from itertools import islice    

# Import Homebrew libs


class Quote:
    def __init__(self, price, size, side):
        self.price = price
        self.size = size
        self.side = side


class Side:
    def __init__(self, reverse=False):
        self._orders = {}
        self._reverse = reverse

    def add(self, order):
        self._orders[order.price] = order
        return True

    def remove(self, order):
        try:
            self._orders.pop(order.price)
            return True
        except KeyError:
            return False

    def __getitem__(self, key):
        keys = sorted(self._orders.keys(), reverse=self._reverse,
                      key=lambda x: float(x))
        if isinstance(key, int):
            key, = islice(keys, key, key + 1)
            return self._orders[key]
        elif not isinstance(key, slice):
            raise TypeError()
        return [self._orders[key] for
                key in islice(keys, key.start, key.stop, key.step)]


class Bids(Side):
    def __init__(self):
        super(Bids, self).__init__(reverse=True)


class Asks(Side):
    def __init__(self):
        super(Asks, self).__init__(reverse=False)


class Ledger:
    def __init__(self):
        self.asks = Asks()
        self.bids = Bids()

    def add(self, order):
        side = self.bids if order.side == 'bid' else self.asks
        side.add(order)

    def update(self, order):
        side = self.asks if order.side == 'ask' else self.bids
        if order.size == 0:
            side.remove(order)
        else:
            side.add(order)

    def top_level(self):
        return self.bids[0], self.asks[0]


