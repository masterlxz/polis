-- Spike (ADR 0015). Dados 100% sintéticos: nomes combinados ao acaso, sem CPF e sem nenhuma pessoa real.
-- Distribuição enviesada (r^2) para nomes comuns repetirem mais, como na vida real; semente fixa.
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- unaccent não é IMMUTABLE; o envoltório é o padrão para indexar (ADR 0012).
CREATE FUNCTION f_unaccent(text) RETURNS text
  LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
  AS $$ SELECT public.unaccent('public.unaccent', $1) $$;

CREATE TABLE pessoa (
  id          integer PRIMARY KEY,
  nome_publico text NOT NULL,
  cargo       text NOT NULL,
  uf          char(2) NOT NULL,
  partido     text NOT NULL,
  fonte       text NOT NULL,
  coletado_em date NOT NULL,
  url_fonte   text NOT NULL
);

SELECT setseed(0.42);

WITH
 pn AS (SELECT ARRAY['José','João','Maria','Ana','Antônio','Francisca','Luiz','Márcia','Conceição','André','Jussara','Heitor','Luíza','Sérgio','Clóvis','Vânia','Ítalo','Zélia','Carlos','Paulo','Pedro','Lucas','Marcos','Fernanda','Juliana','Patrícia','Aline','Camila','Rafael','Daniel','Bruno','Gustavo','Beatriz','Larissa','Helena','Rosângela','Raimundo','Edson','Cláudia','Tânia'] AS a),
 sn AS (SELECT ARRAY['da Silva','dos Santos','Oliveira','Souza','Rodrigues','Ferreira','Alves','Pereira','Lima','Gomes','Ribeiro','Carvalho','Araújo','Barbosa','Cardoso','Nascimento','Moreira','Fonseca','Magalhães','Tavares','Costa','Martins','Rocha','Almeida','Nunes','Mendes','Dias','Teixeira','Correia','Pinto','Freitas','Lacerda','Monteiro','Bastos','Machado','Vieira','Castro','Ramos','Lopes','Medeiros','Azevedo','Cavalcanti','Batista','Duarte','Farias','Guimarães','Barros','Siqueira','Melo','Coelho','Campos','Xavier','Borges','Pires','Andrade','Cunha','Moura','Reis','Brito','Peixoto','Amaral','Viana','Sampaio','Leal','Prado','Matos','Rezende','Franco','Cordeiro','Assis','Bezerra','Lemos','Aguiar','Paiva','Rangel','Veloso','Toledo','Nogueira','Pacheco'] AS a)
INSERT INTO pessoa
SELECT
  g,
  pn.a[1 + floor(array_length(pn.a, 1) * power(random(), 2))::int] || ' ' ||
  sn.a[1 + floor(array_length(sn.a, 1) * power(random(), 2))::int] || ' ' ||
  sn.a[1 + floor(array_length(sn.a, 1) * power(random(), 2))::int],
  (ARRAY['Deputado Federal','Senador','Vereador','Prefeito','Governador'])[1 + g % 5],
  (ARRAY['AC','AL','AM','AP','BA','CE','DF','ES','GO','MA','MG','MS','MT','PA','PB','PE','PI','PR','RJ','RN','RO','RR','RS','SC','SE','SP','TO'])[1 + g % 27],
  'Partido ' || (g % 30),
  'Fonte sintética',
  DATE '2026-11-01',
  'https://exemplo.invalid/fonte/' || g
FROM generate_series(1, 300000) AS g, pn, sn;

CREATE INDEX pessoa_nome_trgm ON pessoa USING gin (f_unaccent(nome_publico) gin_trgm_ops);

-- V2 (spike da busca): palavras sem acento, config 'simple' (sem stemming), consulta por prefixo.
ALTER TABLE pessoa ADD COLUMN nome_tsv tsvector
  GENERATED ALWAYS AS (to_tsvector('simple', f_unaccent(nome_publico))) STORED;
CREATE INDEX pessoa_nome_tsv ON pessoa USING gin (nome_tsv);
ANALYZE pessoa;
