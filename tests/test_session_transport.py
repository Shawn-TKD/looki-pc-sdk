from __future__ import annotations

import unittest

from looki.device.session import LookiSession
from looki.protocol.lcmp import Framer, fields, frame, message, uint


class FakeTransport:
    def __init__(self, incoming: bytes) -> None:
        self.incoming = [incoming]
        self.sent: list[bytes] = []
        self.closed = False
        self.connection_metadata = {"encryption_mode": 2}

    def settimeout(self, _timeout: float | None) -> None:
        pass

    def sendall(self, data: bytes) -> None:
        self.sent.append(data)

    def recv(self, _size: int) -> bytes:
        if self.incoming:
            return self.incoming.pop(0)
        raise TimeoutError

    def close(self) -> None:
        self.closed = True


class SessionTransportTest(unittest.TestCase):
    def test_authentication_uses_injected_transport_and_fresh_challenge(self) -> None:
        challenge = b"fresh-challenge"
        incoming = (
            frame(uint(1, 41) + message(200, message(1, challenge)))
            + frame(uint(1, 42) + message(202))
        )
        transport = FakeTransport(incoming)
        trace: list[dict[str, object]] = []
        session = LookiSession(
            "AA:BB:CC:DD:EE:FF",
            transport_factory=lambda _address, _channel, _timeout: transport,
            trace=trace.append,
        )

        with session:
            session.authenticate()

        decoded = []
        framer = Framer()
        for packet in transport.sent:
            for body in framer.feed(packet):
                decoded.extend(fields(body))
        self.assertIn((2, 0, 41), decoded)
        self.assertIn((2, 0, 42), decoded)
        auth_payload = next(value for tag, wire, value in decoded if tag == 201 and wire == 2)
        self.assertIn((1, 2, challenge), list(fields(auth_payload)))
        self.assertTrue(transport.closed)
        self.assertIn("auth.challenge.accepted", [event["event"] for event in trace])
        connected = next(event for event in trace if event["event"] == "transport.connected")
        self.assertEqual(connected["encryption_mode"], 2)


if __name__ == "__main__":
    unittest.main()
