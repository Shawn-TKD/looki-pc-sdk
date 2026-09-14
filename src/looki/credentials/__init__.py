"""Credential-provider interfaces for a locally enrolled Looki owner."""

from .binding import OwnerBinding, owner_binding_from_framed_capture

__all__ = ["OwnerBinding", "owner_binding_from_framed_capture"]
