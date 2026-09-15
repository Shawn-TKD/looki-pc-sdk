# Instructions for coding agents

This repository controls user-owned Looki L1 devices from Windows and macOS. For a Windows host,
read `docs/WINDOWS-AGENT.md` before touching a device.

## Windows operating sequence

1. Use the repository virtual environment. Run `scripts/bootstrap-windows.ps1` when it does not
   exist.
2. Obtain the target Bluetooth MAC from the user. Never guess or copy the address from research
   vectors.
3. Ask the user to disconnect the phone App and wake the Looki.
4. Start with the read-only `status` command.
5. Pair only when the user asks, or when Windows has no usable Classic Bluetooth bond. `--renew`
   removes only this host's bond for the specified address.
6. Treat `photo`, recording, diary, privacy-light and media commands as device-changing operations.
   They require the user's own private `*.looki-binding` file.

## Protocol invariants

- LCMP v1 uses Classic Bluetooth RFCOMM server channel 3 (DLCI 6).
- Wait for the device to send tag 200. ACK its sequence, then send tag 201 containing the current
  session's challenge.
- Never replay a captured challenge. Do not treat tag 200's signature as a shared client secret.
- Wait for the first tag 202 result 0 before sending business commands.
- Basic status queries do not require owner-binding on the verified firmware.
- Owner-binding belongs after challenge authentication and only enables protected operations for
  that owner's device.

## Evidence and reporting

Use `--trace` when diagnosing. It omits the challenge, binding and hotspot password. Report the last
successful trace event, Windows error number and whether Looki was in pairing or normal mode.

Public research vectors may contain packet structure, direction, length, tags and relative timing.
Do not add live link keys, owner-binding, hotspot passwords, account tokens or personal media to the
public repository. Those values do not help another device authenticate.
