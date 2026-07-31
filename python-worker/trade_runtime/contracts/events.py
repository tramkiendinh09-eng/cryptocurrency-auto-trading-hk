from pydantic import BaseModel, Field


class BaseRuntimeEvent(BaseModel):
    event_type: str
    symbol: str
    exchange: str

    def to_stream_entry(self) -> dict[str, str]:
        payload = self.model_dump()
        return {key: str(value) for key, value in payload.items()}


class MarketTickEvent(BaseRuntimeEvent):
    event_type: str = Field(default="market_tick")
    price: float
    volume: float
    quote_volume: float = 0.0
    event_time: str = ""
