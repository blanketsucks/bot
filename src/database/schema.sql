CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS users (
    id BIGINT NOT NULL,
    credits BIGINT NOT NULL DEFAULT 100,
    catch_id BIGINT DEFAULT 1,
    selected BIGINT DEFAULT 1,
    pokemons UUID[],
    detailed_pokemon_view BOOLEAN DEFAULT FALSE,
    redeems INT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS market (
    id SERIAL PRIMARY KEY,
    price BIGINT,
    pokemon_id UUID,
    owner_id BIGINT
);

CREATE TABLE IF NOT EXISTS pokemons (
    id UUID DEFAULT uuid_generate_v4(),
    catch_id BIGINT NOT NULL,
    dex_id BIGINT NOT NULL,
    owner_id BIGINT NOT NULL,
    nickname TEXT,
    level INT DEFAULT 1,
    exp INT DEFAULT 0,
    ivs INT[6] NOT NULL,
    evs INT[6] NOT NULL,
    moves TEXT[4] NOT NULL,
    nature TEXT,
    is_shiny BOOLEAN DEFAULT FALSE,
    is_starter BOOLEAN DEFAULT FALSE,
    is_favourite BOOLEAN DEFAULT FALSE,
    is_listed BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS guilds (
    id BIGINT,
    prefix VARCHAR(15) DEFAULT 'p!',
    spawn_channels BIGINT[],
    exp_channels BIGINT[]
);

CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    name TEXT,
    description TEXT,
    kind INT,
    price INT
);