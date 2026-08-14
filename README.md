# Smart Solity for Home Assistant

Unofficial Home Assistant custom integration for door locks registered in the
Smart Solity mobile app.

## Features

- Lock and unlock from a Home Assistant lock entity
- Door-lock state polling every 30 seconds
- Battery percentage sensor
- Multiple locks on one Smart Solity account
- Automatic token renewal without storing the account password
- Korean and English setup UI
- Matter-aligned user and credential actions:
  - List registered users and credential types (PIN values are redacted)
  - Invite a manager or member
  - Create date-range, weekly, or one-time visitor PINs
  - Retrieve recent access and alarm events
- Capability attributes for PIN, card, fingerprint, face, and dual authentication

## Install

### HACS

1. In HACS, open **Integrations** and choose **Custom repositories**.
2. Add `https://github.com/mk0000001/ha-smart-solity` with the
   **Integration** category.
3. Install **Smart Solity**, restart Home Assistant, then add the integration
   from **Settings → Devices & services**.

### Manual

Copy `custom_components/smart_solity` into the `custom_components` directory in
your Home Assistant configuration directory, then restart Home Assistant.

Go to **Settings → Devices & services → Add integration**, search for
**Smart Solity**, and sign in with the account used by the Smart Solity app.

## Notes

This project uses an undocumented cloud API and is not affiliated with Solity.
The integration stores the cloud-issued token pair in the Home Assistant config
entry. The password is SHA-256/Base64 encoded for the login request and is never
saved by the integration.

Visitor PINs are not saved by the integration. Be aware that Home Assistant
automation and script traces may retain action input, so use PIN actions manually
or restrict trace retention when the PIN must remain secret.
