"""Incremental crash-recovery manifest backed by JSON lines + fsync."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

InvocationShape = Literal["thin", "rich", "resumed"]


class Step(BaseModel):
    model_config = ConfigDict(frozen=True)

    step_id: str
    name: str
    ts: datetime
    invocation_shape: InvocationShape
    payload: dict[str, Any]


class ManifestState(BaseModel):
    complete: bool
    steps: list[Step]


class Manifest:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append_step(self, step: Step) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.path, "ab") as file:
            data = (step.model_dump_json() + "\n").encode("utf-8")
            file.write(data)
            file.flush()
            os.fsync(file.fileno())

    @classmethod
    def load(cls, path: Path) -> ManifestState:
        if not path.exists():
            return ManifestState(complete=False, steps=[])

        steps: list[Step] = []

        with open(path, "rb") as file:
            for line in file:
                line = line.strip()

                if not line:
                    continue

                steps.append(Step.model_validate_json(line))

        complete = bool(steps) and steps[-1].name == "complete"

        return ManifestState(complete=complete, steps=steps)
