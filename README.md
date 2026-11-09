[![HACS Custom][hacs_shield]][hacs]
[![GitHub Latest Release][releases_shield]][latest_release]
[![GitHub All Releases][downloads_total_shield]][releases]<!-- piotrmachowski_support_badges_start -->
[![Ko-Fi][ko_fi_shield]][ko_fi]
[![buycoffee.to][buycoffee_to_shield]][buycoffee_to]
[![PayPal.Me][paypal_me_shield]][paypal_me]
[![Revolut.Me][revolut_me_shield]][revolut_me]
<!-- piotrmachowski_support_badges_end -->


[hacs_shield]: https://img.shields.io/static/v1.svg?label=HACS&message=Custom&style=popout&color=orange&labelColor=41bdf5&logo=HomeAssistantCommunityStore&logoColor=white
[hacs]: https://hacs.xyz/docs/faq/custom_repositories

[latest_release]: https://github.com/PiotrMachowski/Home-Assistant-custom-components-SmartThings-Soundbar/releases/latest
[releases_shield]: https://img.shields.io/github/release/PiotrMachowski/Home-Assistant-custom-components-SmartThings-Soundbar.svg?style=popout

[releases]: https://github.com/PiotrMachowski/Home-Assistant-custom-components-SmartThings-Soundbar/releases
[downloads_total_shield]: https://img.shields.io/github/downloads/PiotrMachowski/Home-Assistant-custom-components-SmartThings-Soundbar/total


# SmartThings Soundbar

Adds support for SmartThings enabled Soundbar

## Features

- Turn on/off 
- Set volume
- Step volume up/down
- Mute/unmute
- Select source
- Show current volume level
- Show current state: on/off/playing/paused/idle
- Show if muted/unmuted
- Show current source


## Configuration

The integration is set up from the Home Assistant UI:

1. Go to **Settings > Devices & services > Add integration** and search for **SmartThings Soundbar**.
2. Choose how to sign in:
   - **Use my SmartThings integration login** (recommended, shown when Home Assistant's official [SmartThings integration](https://www.home-assistant.io/integrations/smartthings/) is set up). The soundbar borrows that integration's login, which renews itself, so there is no token to manage. The official integration must stay set up and loaded.
   - **Paste a personal access token** (see [below](#getting-a-token)).
3. Pick your soundbar from the list of devices on your account.

To switch an existing soundbar between the two, open its entry and choose **Reconfigure**.

Each soundbar is added as its own entry. To change the maximum volume, open the entry and click **Configure**.

| Option | Default | Description |
| --- | --- | --- |
| Maximum volume | 100 | Soundbar volume level that Home Assistant treats as 100% |

If SmartThings rejects the token later (for example because it expired), Home Assistant shows a **Re-authenticate** prompt where you can paste a new one.

### Migrating from YAML

YAML configuration is deprecated. Existing `media_player: - platform: smartthings_soundbar` entries are imported automatically on startup, keeping their entity IDs, name and `max_volume`. After the import, a repair notice asks you to remove the YAML block from `configuration.yaml`.

## Getting a token

Make sure your device is connected to your SmartThings account, then create a personal access token at https://account.smartthings.com/tokens with the **Devices** scopes (list, see, control).

> **Note:** SmartThings now limits new personal access tokens to 24 hours. Tokens created before 30 December 2024 keep their original lifetime. If your token expires, use the re-authenticate prompt to paste a new one.

## Installation

### Using [HACS](https://hacs.xyz/) (recommended)

This integration can be added to HACS as a [custom repository](https://hacs.xyz/docs/faq/custom_repositories):
* URL: `https://github.com/PiotrMachowski/Home-Assistant-custom-components-SmartThings-Soundbar`
* Category: `Integration`

After adding a custom repository you can use HACS to install this integration using user interface.

### Manual

To install this integration manually you have to download [*smartthings_soundbar.zip*](https://github.com/PiotrMachowski/Home-Assistant-custom-components-SmartThings-Soundbar/releases/latest/download/smartthings_soundbar.zip) and extract its contents to `config/custom_components/smartthings_soundbar` directory:
```bash
mkdir -p custom_components/smartthings_soundbar
cd custom_components/smartthings_soundbar
wget https://github.com/PiotrMachowski/Home-Assistant-custom-components-SmartThings-Soundbar/releases/latest/download/smartthings_soundbar.zip
unzip smartthings_soundbar.zip
rm smartthings_soundbar.zip
```

Restart Home Assistant after installing, then add the integration from the UI.

## Supported devices

This integration was confirmed to work with following devices:

- Samsung HW-N950
- Samsung HW-Q800B
- Samsung HW-Q800T
- Samsung HW-Q950T
- Samsung HW-Q990B
- Samsung HW-Q990C
- Samsung HW-Q90R
- Samsung HW-Q80R
- Samsung HW-Q70R
- Samsung HW-S60T
- Samsung HW-S61T



<!-- piotrmachowski_support_links_start -->

## Support

If you want to support my work with a donation you can use one of the following platforms:

<table>
  <tr>
    <th>Platform</th>
    <th>Payment methods</th>
    <th>Link</th>
    <th>Comment</th>
  </tr>
  <tr>
    <td>Ko-fi</td>
    <td>
      <li>PayPal</li>
      <li>Credit card</li>
    </td>
    <td>
      <a href='https://ko-fi.com/piotrmachowski' target='_blank'><img height='35px' src='https://storage.ko-fi.com/cdn/kofi6.png?v=6' border='0' alt='Buy Me a Coffee at ko-fi.com' />
    </td>
    <td>
      <li>No fees</li>
      <li>Single or monthly payment</li>
    </td>
  </tr>
  <tr>
    <td>buycoffee.to</td>
    <td>
      <li>BLIK</li>
      <li>Bank transfer</li>
    </td>
    <td>
      <a href="https://buycoffee.to/piotrmachowski" target="_blank"><img src="https://buycoffee.to/btn/buycoffeeto-btn-primary.svg" height="35px" alt="Postaw mi kawę na buycoffee.to"></a>
    </td>
    <td></td>
  </tr>
  <tr>
    <td>PayPal</td>
    <td>
      <li>PayPal</li>
    </td>
    <td>
      <a href="https://paypal.me/PiMachowski" target="_blank"><img src="https://www.paypalobjects.com/webstatic/mktg/logo/pp_cc_mark_37x23.jpg" border="0" alt="PayPal Logo" height="35px" style="height: auto !important;width: auto !important;"></a>
    </td>
    <td>
      <li>No fees</li>
    </td>
  </tr>
  <tr>
    <td>Revolut</td>
    <td>
      <li>Revolut</li>
      <li>Credit Card</li>
    </td>
    <td>
      <a href="https://revolut.me/314ma" target="_blank"><img src="https://assets.revolut.com/assets/favicons/favicon-32x32.png" height="32px" alt="Revolut"></a>
    </td>
    <td>
      <li>No fees</li>
    </td>
  </tr>
</table>

### Powered by
[![PyCharm logo.](https://resources.jetbrains.com/storage/products/company/brand/logos/jetbrains.svg)](https://jb.gg/OpenSourceSupport)


[ko_fi_shield]: https://img.shields.io/static/v1.svg?label=%20&message=Ko-Fi&color=F16061&logo=ko-fi&logoColor=white

[ko_fi]: https://ko-fi.com/piotrmachowski

[buycoffee_to_shield]: https://shields.io/badge/buycoffee.to-white?style=flat&labelColor=white&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAABhmlDQ1BJQ0MgcHJvZmlsZQAAKJF9kT1Iw1AUhU9TpaIVh1YQcchQnayIijhKFYtgobQVWnUweemP0KQhSXFxFFwLDv4sVh1cnHV1cBUEwR8QVxcnRRcp8b6k0CLGC4/3cd49h/fuA4R6malmxzigapaRisfEbG5FDLzChxB6MIZ+iZl6Ir2QgWd93VM31V2UZ3n3/Vm9St5kgE8knmW6YRGvE09vWjrnfeIwK0kK8TnxqEEXJH7kuuzyG+eiwwLPDBuZ1BxxmFgstrHcxqxkqMRTxBFF1ShfyLqscN7irJarrHlP/sJgXltOc53WEOJYRAJJiJBRxQbKsBClXSPFRIrOYx7+QcefJJdMrg0wcsyjAhWS4wf/g9+zNQuTE25SMAZ0vtj2xzAQ2AUaNdv+PrbtxgngfwautJa/UgdmPkmvtbTIEdC3DVxctzR5D7jcAQaedMmQHMlPSygUgPcz+qYcELoFulfduTXPcfoAZGhWSzfAwSEwUqTsNY93d7XP7d+e5vx+AIahcq//o+yoAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH5wETCy4vFNqLzwAAAVpJREFUOMvd0rFLVXEYxvHPOedKJnKJhrDLuUFREULE7YDCMYj+AydpsCWiaKu29hZxiP4Al4aWwC1EdFI4Q3hqEmkIBI8ZChWXKNLLvS0/Qcza84V3enm/7/s878t/HxGkeTaIGziP+EB918nawu7Dq1d0e1+2J2bepnk2jFEUVVF+qKV51o9neBCaugfge70keoxxUbSWjrQ+4SUyzKZ5NlnDZdzGG7w4DIh+dtZEFntDA98l8S0MYwctNGrYz9WqKJePFLq80g5Sr+EHlnATp+NA+4qLaZ7FfzMrzbMBjGEdq8GrJMZnvAvFC/8wfAwjWMQ8XmMzaW9sdevNRgd3MFhvNpbaG1u/Dk2/hOc4gadVUa7Um425qii/7Z+xH9O4jwW8Cqv24Tru4hyeVEU588cfBMgpPMI9nMFe0BkFzVOYrYqycyQgQJLwTC2cDZCPeF8V5Y7jGb8BUpRicy7OU5MAAAAASUVORK5CYII=

[buycoffee_to]: https://buycoffee.to/piotrmachowski

[buy_me_a_coffee_shield]: https://img.shields.io/static/v1.svg?label=%20&message=Buy%20me%20a%20coffee&color=6f4e37&logo=buy%20me%20a%20coffee&logoColor=white

[buy_me_a_coffee]: https://www.buymeacoffee.com/PiotrMachowski

[paypal_me_shield]: https://img.shields.io/static/v1.svg?label=%20&message=PayPal.Me&logo=paypal

[paypal_me]: https://paypal.me/PiMachowski

[revolut_me_shield]: https://img.shields.io/static/v1.svg?label=%20&message=Revolut&logo=revolut

[revolut_me]: https://revolut.me/314ma
<!-- piotrmachowski_support_links_end -->
