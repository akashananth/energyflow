"""
Energy Price Producer
─────────────────────
Simulates a real-time feed of electricity spot prices across European regions.

Real-world equivalent: ENTSO-E Transparency Platform publishes prices like this
every 15 minutes. We simulate the same structure so our pipeline is realistic.

Price model:
  - Base price varies by region (Germany/France cheaper, UK more expensive)
  - Day/night cycle: prices peak 07:00–09:00 and 17:00–20:00 (demand peaks)
  - Random noise + occasional renewable surplus spikes (negative prices!)
  - Occasional missing/late data to simulate real-world messiness
"""

import json
import logging
import math
import os
import random
import time
from datetime import datetime, timezone

from kafka import KafkaProducer
from kafka.errors import KafkaError

# ── Config from environment variables ─────────────────────────────────────────
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_NAME = os.getenv("TOPIC_NAME", "energy.prices")
PUBLISH_INTERVAL = float(os.getenv("PUBLISH_INTERVAL_SECONDS", "5"))

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger(__name__)

# ── Market configuration ───────────────────────────────────────────────────────
# Each region has a base price (€/MWh) and volatility factor.
# These loosely reflect real European electricity market characteristics.
REGIONS = {
    "DE": {"base_price": 65.0,  "volatility": 0.15},  # Germany — large renewables share
    "FR": {"base_price": 60.0,  "volatility": 0.10},  # France — nuclear baseload, stable
    "GB": {"base_price": 80.0,  "volatility": 0.20},  # Great Britain — island, more volatile
    "NL": {"base_price": 68.0,  "volatility": 0.18},  # Netherlands
    "ES": {"base_price": 55.0,  "volatility": 0.22},  # Spain — high solar, more swings
}

# Energy sources mix (affects price signals)
ENERGY_SOURCES = ["wind", "solar", "nuclear", "gas", "coal", "hydro"]


def demand_multiplier(hour: int) -> float:
    """
    Returns a price multiplier based on hour of day.
    Models real electricity demand curves:
      - Morning peak: 07:00–09:00
      - Evening peak: 17:00–20:00
      - Night trough: 01:00–05:00
    """
    # Two peaks modeled as gaussian bumps
    morning_peak = 0.4 * math.exp(-0.5 * ((hour - 8) / 1.5) ** 2)
    evening_peak = 0.5 * math.exp(-0.5 * ((hour - 18) / 2.0) ** 2)
    night_trough = -0.2 * math.exp(-0.5 * ((hour - 3) / 2.0) ** 2)
    return 1.0 + morning_peak + evening_peak + night_trough


def generate_price_event(region: str, simulated_hour: int) -> dict:
    """
    Generates a single price event for a region.
    
    Returns a dict that will be serialized to JSON and sent to Kafka.
    This structure IS our data contract — downstream consumers depend on it.
    """
    config = REGIONS[region]
    base = config["base_price"]
    vol = config["volatility"]

    # Apply demand curve
    price = base * demand_multiplier(simulated_hour)

    # Add random noise (log-normal so prices don't go wildly negative often)
    noise = random.gauss(0, base * vol * 0.3)
    price += noise

    # Simulate renewable surplus events — negative prices are REAL and common
    # when solar/wind produces more than demand (storage/grid can't absorb it)
    if random.random() < 0.03:  # 3% chance
        price = random.uniform(-20, -5)
        log.info(f"⚡ Negative price event in {region}: {price:.2f} €/MWh")

    # Simulate data quality issues (real pipelines deal with this constantly)
    quality_flag = "ok"
    if random.random() < 0.02:   # 2% chance of sensor glitch
        price = None
        quality_flag = "missing"
    elif random.random() < 0.01:  # 1% chance of stale/duplicate data
        quality_flag = "suspect"

    now = datetime.now(timezone.utc)

    return {
        # Core price data
        "event_id": f"{region}-{now.strftime('%Y%m%dT%H%M%S%f')}",
        "region": region,
        "price_eur_mwh": round(price, 4) if price is not None else None,
        "currency": "EUR",
        "unit": "MWh",

        # Time context
        "timestamp_utc": now.isoformat(),
        "market_hour": simulated_hour,          # which hour of day we're simulating
        "delivery_period": "PT15M",             # 15-minute delivery period (ISO 8601)

        # Grid context (affects trading decisions)
        "dominant_source": random.choice(ENERGY_SOURCES),
        "renewable_share_pct": round(random.uniform(10, 85), 1),

        # Data quality metadata — this feeds our observability layer
        "quality_flag": quality_flag,
        "producer_version": "1.0.0",
        "schema_version": "1",                  # increment when structure changes
    }


def create_producer() -> KafkaProducer:
    """
    Creates a Kafka producer with retries.
    Kafka might not be ready immediately when the container starts.
    """
    retries = 0
    while retries < 10:
        try:
            producer = KafkaProducer(
                bootstrap_servers=BOOTSTRAP_SERVERS,
                # Serialize dict → JSON bytes
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                # Use region as the key → ensures same region always goes to same partition
                # This is important for ordering guarantees
                key_serializer=lambda k: k.encode("utf-8"),
                # Wait for all in-sync replicas to acknowledge (durability)
                acks="all",
                # Retry on transient failures
                retries=3,
            )
            log.info(f"✅ Connected to Kafka at {BOOTSTRAP_SERVERS}")
            return producer
        except KafkaError as e:
            retries += 1
            log.warning(f"Kafka not ready yet ({retries}/10): {e}. Retrying in 5s...")
            time.sleep(5)

    raise RuntimeError("Could not connect to Kafka after 10 attempts")


def on_send_success(record_metadata):
    log.debug(
        f"Sent → topic={record_metadata.topic} "
        f"partition={record_metadata.partition} "
        f"offset={record_metadata.offset}"
    )


def on_send_error(excp):
    log.error(f"Failed to send message: {excp}")


def main():
    log.info(f"🚀 Starting EnergyFlow producer → topic: {TOPIC_NAME}")
    producer = create_producer()

    # Simulate time advancing through the day
    # Each publish interval = 15 minutes of simulated market time
    simulated_hour = 0
    tick = 0

    try:
        while True:
            # Every tick, publish prices for ALL regions simultaneously
            # (real markets publish all regions at the same interval)
            for region in REGIONS:
                event = generate_price_event(region, simulated_hour)

                producer.send(
                    TOPIC_NAME,
                    key=region,
                    value=event
                ).add_callback(on_send_success).add_errback(on_send_error)

            producer.flush()  # ensure all messages are sent before sleeping

            tick += 1
            # Advance simulated hour every 4 ticks (every ~20 seconds in real time)
            simulated_hour = (tick // 4) % 24

            log.info(
                f"📊 Published prices for {len(REGIONS)} regions | "
                f"Simulated hour: {simulated_hour:02d}:00 | "
                f"Tick: {tick}"
            )

            time.sleep(PUBLISH_INTERVAL)

    except KeyboardInterrupt:
        log.info("Shutting down producer...")
    finally:
        producer.close()


if __name__ == "__main__":
    main()