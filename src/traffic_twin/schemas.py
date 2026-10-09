"""Strict, bounded public input contract; no commands or server paths accepted."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class ODRow(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)
    origin_gate: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$")
    destination_gate: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$")
    rate_per_hour: float = Field(ge=0, le=1800)
    interval_start: float = Field(default=0, ge=0, le=14100)
    interval_end: float = Field(default=300, gt=0, le=14400)

    @model_validator(mode="after")
    def interval(self):
        if self.interval_end <= self.interval_start or self.interval_start % 300 or self.interval_end % 300:
            raise ValueError("OD intervals must be positive and aligned to 300-second boundaries")
        return self

class PolicyParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)
    green_extension_seconds: float | None = Field(default=None, ge=1, le=15)
    downstream_occupancy_threshold: float | None = Field(default=None, ge=10, le=90)
    managed_curb_stop_seconds: float | None = Field(default=None, ge=0, le=30)

class DownstreamBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)
    gate_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$")
    start_seconds: float = Field(ge=0, le=14400)
    end_seconds: float = Field(gt=0, le=14400)
    speed_m_s: float = Field(default=0.1, ge=0.1, le=2)

class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)
    network_id: Literal["baseline"] = "baseline"
    policy: Literal["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7"] = "S0"
    policy_parameters: PolicyParameters | None = None
    downstream_block: DownstreamBlock | None = None
    seed: int = Field(default=42, ge=0, le=2147483647)
    demand_scale: float = Field(default=1, gt=0, le=5)
    duration_seconds: float = Field(default=600, ge=10, le=14400)
    step_seconds: Literal[0.25, 0.5] = 0.5
    trajectory: bool = True
    warmup_seconds: float = Field(default=0, ge=0, le=3600)
    demand_end_seconds: float | None = Field(default=None, ge=1, le=12600)
    period: Literal["am", "pm"] = "am"
    rate_per_gate: float = Field(default=120, ge=1, le=1800)
    drain_seconds: float = Field(default=0, ge=0, le=3600)
    od: list[ODRow] | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def times(self):
        if abs(self.duration_seconds / self.step_seconds - round(self.duration_seconds / self.step_seconds)) > 1e-9:
            raise ValueError("duration_seconds must be an integer number of simulation steps")
        end = self.demand_end_seconds or self.duration_seconds - self.drain_seconds
        if self.warmup_seconds >= end or end > self.duration_seconds:
            raise ValueError("Require warmup_seconds < demand_end_seconds <= duration_seconds")
        if self.downstream_block and not 0 <= self.downstream_block.start_seconds < self.downstream_block.end_seconds <= self.duration_seconds:
            raise ValueError("Downstream block must fit inside the simulation window")
        if self.od and any(row.interval_end > end for row in self.od):
            raise ValueError("OD intervals must fit inside demand_end_seconds")
        return self

    def engine_config(self):
        result = self.model_dump(exclude_none=True)
        result["demand_end_seconds"] = self.demand_end_seconds or self.duration_seconds - self.drain_seconds
        return result
