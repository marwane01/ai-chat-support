CREATE TABLE IF NOT EXISTS hotels (
  hotel_id       VARCHAR PRIMARY KEY,
  name           TEXT NOT NULL,
  city           TEXT NOT NULL,
  country        TEXT NOT NULL,
  stars          INT,
  lat            DOUBLE PRECISION,
  lon            DOUBLE PRECISION,
  amenities_json JSONB
);

CREATE TABLE IF NOT EXISTS room_rates (
  hotel_id            VARCHAR REFERENCES hotels(hotel_id),
  room_type           TEXT,
  occupancy           INT,
  currency            TEXT,
  base_rate           NUMERIC,
  refundable          BOOLEAN,
  breakfast_included  BOOLEAN
);

CREATE TABLE IF NOT EXISTS policies (
  hotel_id   VARCHAR REFERENCES hotels(hotel_id),
  key        TEXT,
  value      TEXT,
  updated_at TIMESTAMP DEFAULT NOW()
);
