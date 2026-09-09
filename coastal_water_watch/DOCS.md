# Coastal Water Watch installer

## Installation

1. Install **Coastal Water Watch** from the Holiday Let Manager app repository.
2. Start the app once and check its log for a successful installation message.
3. Restart Home Assistant.
4. Open **Settings > Devices & services**. Existing Coastal Water Watch entries
   will load automatically; for a first installation, select **Add integration**
   and choose **Coastal Water Watch**.

The app is expected to stop after completing the copy. It is not a background
service and should not be configured to start at boot.

Before replacing an existing version, the installer retains one rollback copy at
`/config/custom_components/.coastal_water_watch.previous`.

Coastal Water Watch is planning information, not a declaration that water is
safe. Conditions can change quickly. Follow current official advice and local
signage, and do not enter the water when warnings are in place.

