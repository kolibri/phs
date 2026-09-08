from pydantic import BaseModel, ConfigDict


class InventoryModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
