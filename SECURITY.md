# Security

## Private device material

`.looki-binding` files contain the application-layer owner context accepted by one Looki.
They are deliberately excluded by `.gitignore`, but the portable format itself is not encrypted.
Treat one like a device password:

- never commit it, attach it to an issue, or paste it into logs;
- transfer it to another computer through an encrypted archive or an encrypted removable drive;
- store it only in the local `private/` directory;
- remove the copy from a computer that should no longer control the device.

The SDK never prints the payload, hotspot password, or raw media filename during normal CLI use.
Raw HCI captures can contain all of these and must not be published.

## Scope

Use this project only with a device you own or have explicit permission to test. Report a suspected
credential leak privately to the repository maintainer instead of opening a public issue with data.
