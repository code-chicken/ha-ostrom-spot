# Ostrom Spot Prices

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

This Home Assistant custom integration retrieves dynamic (hourly or 15-minute) electricity spot prices directly from the official [Ostrom API](https://ostrom.de/).

The primary goal of this integration is to provide the live price data needed for the **Home Assistant Energy Dashboard**, allowing you to accurately track your electricity costs based on your actual consumption and the dynamic hourly prices.

---

## ⚠️ Beta Version

This integration is functional but currently in a beta state. It has been tested and works, but there may be bugs or future changes. Please open an [Issue](https://github.com/code-chicken/ha-ostrom-spot/issues) if you find any problems.

## Key Features

* Fetches current and future electricity prices (the real end-customer price: spot price + taxes & levies) for your specific postal code.
* Creates a `sensor.current_price` (in `EUR/kWh`) that updates its value in sync with the price intervals (hourly or 15-min, as soon as Ostrom provides them).
* Provides all upcoming prices for today and tomorrow as attributes on the sensor, perfect for automations or custom charts.
* **Enables the Home Assistant Energy Dashboard** for accurate, dynamic cost tracking.
* **(Optional)** Can automatically create hourly and daily cost sensors based on your main energy meter.

## Installation (HACS)

This integration is designed to be installed via the [Home Assistant Community Store (HACS)](https://hacs.xyz/).

1.  Ensure HACS is installed in your Home Assistant.
2.  **Add as a Custom Repository (during Beta):**
    * Go to HACS > Integrations.
    * Click the three dots (...) in the top right corner and select "Custom repositories".
    * In the "Repository" field, paste this URL: `https://github.com/code-chicken/ha-ostrom-spot`
    * Select "Integration" as the category.
    * Click "Add".
3.  The "Ostrom Spot Prices" integration will now appear. Click "Install" and follow the prompts.
4.  **Restart Home Assistant** (This is a required step).

## Configuration

### Step 1: Get Ostrom API Credentials

This integration requires a **Client ID** and a **Client Secret** from Ostrom to access your account data.

1.  Log in to your Ostrom customer portal.
2.  Navigate to the API section to generate your credentials.
3.  If you cannot find this section, you may need to contact Ostrom support to request API access.

### Step 2: Add Integration in Home Assistant

1.  Go to **Settings > Devices & Services**.
2.  Click **"Add Integration"** (bottom right) and search for **"Ostrom Spot Prices"**.
3.  A configuration dialog will appear. Enter the following:
    * **Client ID:** Your API Client ID from the Ostrom portal.
    * **Client Secret:** Your API Client Secret from the Ostrom portal.
    * **Postal Code:** Your 5-digit German postal code (e.g., 33378). This is required for the API to calculate correct grid fees and taxes.
4.  Click "Submit". The integration will test the credentials and set up your new `sensor.current_price`.

## Usage: Tracking Your Costs

You now have two excellent ways to track your costs.

### Method 1 (Recommended): The Energy Dashboard

This is the easiest and most robust method. It will automatically calculate your real, consumption-weighted average price.

1.  Go to **Settings > Dashboards > Energy**.
2.  Find the **Electricity grid** card.
3.  Under **Electricity consumption**, click `+ Add Consumption` and select your main energy import sensor (e.g., `sensor.stromnetz_importierte_energie`). This must be a `total_increasing` sensor.
4.  Under **Costs**, select **"Use an entity with the current price"** and choose `sensor.current_price` from the dropdown.

That's it! Home Assistant will now automatically multiply your consumption (kWh) from every hour (or 15-min interval) by the price that was valid during that interval (`sensor.current_price`).

### Method 2: Automated Cost Sensors

If you prefer to have separate sensors for your costs, you can configure the integration to create them for you.

1.  Go to **Settings > Devices & Services** and find the "Ostrom Spot Prices" integration.
2.  Click the **"Configure"** button.
3.  In the **"Total consumption sensor"** dropdown, select your main energy meter (the same one you would use for the Energy Dashboard).
4.  Click "Submit".

The integration will reload and **automatically create** the following new sensors, which will be linked to your device:
* `sensor.ostrom_hourly_consumption` (A helper sensor that tracks your hourly kWh)
* `sensor.ostrom_daily_consumption` (A helper sensor that tracks your daily kWh)
* `sensor.hourly_cost` (Calculates `hourly_consumption * current_price`)
* `sensor.daily_cost` (Calculates `daily_consumption * current_price`)

### Example: Future Price Chart (ApexCharts)

You can use the sensor's attributes to build a chart of upcoming prices.

1.  Make sure you have [ApexCharts-Card](https://github.com/RomRider/apexcharts-card) installed (available in HACS).
2.  Add a new card with the following YAML:

```yaml
type: custom:apexcharts-card
graph_span: 24h
span:
  start: hour
  offset: '-0h'
header:
  title: Strompreise (€/kWh)
  show: true
apex_config:
  xaxis:
    type: datetime
    labels:
      datetimeFormatter:
        hour: 'HH:mm'
        day: dd MMM
  plotOptions:
    bar:
      colors:
        ranges:
          - from: 0
            to: 0.15
            color: '#2ecc71'
          - from: 0.15
            to: 0.2
            color: '#a6d96a'
          - from: 0.2
            to: 0.25
            color: '#ffff99'
          - from: 0.25
            to: 0.3
            color: '#fdae61'
          - from: 0.3
            to: 0.35
            color: '#f46d43'
          - from: 0.35
            to: 1
            color: '#d73027'
series:
  - entity: sensor.current_price
    attribute: all_prices
    float_precision: 3
    type: column
    name: Preis
    data_generator: |
      const prices = entity.attributes.all_prices;
      return Object.entries(prices).map(([timestamp, value]) => {
        const date = new Date(timestamp);
        return [date, value];
      });
    show:
      datalabels: false
      in_header: true
yaxis:
  - min: ~0.15
    max: ~0.40
    decimals: 2
```    