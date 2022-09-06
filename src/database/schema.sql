CREATE TABLE IF NOT EXISTS users (
    id BIGINT NOT NULL,
    credits BIGINT NOT NULL DEFAULT 100,
    catch_id BIGINT DEFAULT 1,
    selected BIGINT DEFAULT 1,
    pokemons JSON
);

CREATE TABLE IF NOT EXISTS market (
    id BIGINT,
    price BIGINT,
    pokemon_id BIGINT,
    owner_id BIGINT,

    PRIMARY KEY(id)
);

CREATE TABLE IF NOT EXISTS guilds (
    id BIGINT,
    prefix VARCHAR(15) DEFAULT 'p!',
    spawn_channels BIGINT[],
    exp_channels BIGINT[]
);