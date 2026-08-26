"""Shared package identity for network clients and release tooling."""

from pathlib import Path


NAME = "grounded"
REPOSITORY_URL = "https://github.com/jostelzer/grounded"


def version() -> str:
    value = (
        (Path(__file__).resolve().parents[1] / "VERSION")
        .read_text(encoding="utf-8")
        .strip()
    )
    if not value or any(character.isspace() for character in value):
        raise RuntimeError("VERSION must contain one non-empty version token")
    return value.removeprefix("v")


def user_agent(*, mailto: str | None = None, qualifier: str | None = None) -> str:
    product = f"{NAME}/{version()}"
    if qualifier:
        product += f" {qualifier}"
    contact = f"; mailto:{mailto.strip()}" if mailto and mailto.strip() else ""
    return f"{product} (+{REPOSITORY_URL}{contact})"
