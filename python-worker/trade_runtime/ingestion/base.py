from trade_runtime.streams import StreamPublisher


class RuntimeIngestionAdapter:
    def __init__(self, publisher: StreamPublisher | None = None):
        self.publisher = publisher

    def emit(self, event):
        if self.publisher is None:
            return None
        return self.publisher.publish(event)
