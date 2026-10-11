-- Run with Supabase SQL editor or land-law migrate using an owner connection.
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA public;
CREATE TABLE IF NOT EXISTS public.releases(id text PRIMARY KEY,payload text NOT NULL,created_at text NOT NULL);
CREATE TABLE IF NOT EXISTS public.app_state(key text PRIMARY KEY,value text NOT NULL);
CREATE TABLE IF NOT EXISTS public.documents(
 release_id text NOT NULL REFERENCES public.releases(id),id text NOT NULL,payload text NOT NULL,
 title text NOT NULL,document_number text,project text,source_kind text NOT NULL,jurisdiction text NOT NULL,
 PRIMARY KEY(release_id,id));
CREATE TABLE IF NOT EXISTS public.chunks(
 release_id text NOT NULL,id text NOT NULL,document_id text NOT NULL,text text NOT NULL,
 locator text NOT NULL,parent_id text,page integer,checksum text NOT NULL,
 embedding_model text,embedding vector(768),search_tsv tsvector,
 PRIMARY KEY(release_id,id),FOREIGN KEY(release_id,document_id) REFERENCES public.documents(release_id,id));
CREATE OR REPLACE FUNCTION public.set_chunk_search() RETURNS trigger LANGUAGE plpgsql
 SET search_path=pg_catalog,public AS $$
 BEGIN NEW.search_tsv := to_tsvector('simple',lower(public.unaccent(replace(NEW.text,'đ','d')))); RETURN NEW; END $$;
DROP TRIGGER IF EXISTS chunk_search_trigger ON public.chunks;
CREATE TRIGGER chunk_search_trigger BEFORE INSERT OR UPDATE OF text ON public.chunks
 FOR EACH ROW EXECUTE FUNCTION public.set_chunk_search();
CREATE INDEX IF NOT EXISTS chunk_search_idx ON public.chunks USING gin(search_tsv);
CREATE INDEX IF NOT EXISTS chunk_vector_idx ON public.chunks USING hnsw(embedding vector_cosine_ops);
CREATE TABLE IF NOT EXISTS public.sessions(id text PRIMARY KEY,token_hash text NOT NULL,created_at text NOT NULL);
CREATE TABLE IF NOT EXISTS public.messages(id text PRIMARY KEY,session_id text NOT NULL REFERENCES public.sessions(id)
 ON DELETE CASCADE,role text NOT NULL,payload text NOT NULL,created_at text NOT NULL);
CREATE TABLE IF NOT EXISTS public.traces(id text PRIMARY KEY,session_id text NOT NULL REFERENCES public.sessions(id)
 ON DELETE CASCADE,payload text NOT NULL,created_at text NOT NULL);
CREATE TABLE IF NOT EXISTS public.counters(key text PRIMARY KEY,value integer NOT NULL,expires_at text NOT NULL);
CREATE INDEX IF NOT EXISTS message_session_idx ON public.messages(session_id,created_at);
-- No browser access. Backend uses a dedicated database role; no permissive RLS policies.
ALTER TABLE public.releases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.app_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.traces ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.counters ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.releases,public.app_state,public.documents,public.chunks,public.sessions,
 public.messages,public.traces,public.counters FROM anon,authenticated;
-- Provision a login role out of band, then assign this narrowly scoped role.
DO $$ BEGIN IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='landlaw_runtime') THEN
 CREATE ROLE landlaw_runtime NOLOGIN; END IF; END $$;
GRANT USAGE ON SCHEMA public TO landlaw_runtime;
GRANT SELECT ON public.releases,public.documents,public.chunks TO landlaw_runtime;
GRANT SELECT,INSERT,UPDATE,DELETE ON public.sessions,public.messages,public.traces,public.counters TO landlaw_runtime;
GRANT SELECT ON public.app_state TO landlaw_runtime;
CREATE POLICY corpus_runtime ON public.releases FOR SELECT TO landlaw_runtime USING(true);
CREATE POLICY document_runtime ON public.documents FOR SELECT TO landlaw_runtime USING(true);
CREATE POLICY chunk_runtime ON public.chunks FOR SELECT TO landlaw_runtime USING(true);
CREATE POLICY state_runtime ON public.app_state FOR SELECT TO landlaw_runtime USING(true);
CREATE POLICY session_runtime ON public.sessions TO landlaw_runtime USING(true) WITH CHECK(true);
CREATE POLICY message_runtime ON public.messages TO landlaw_runtime USING(true) WITH CHECK(true);
CREATE POLICY trace_runtime ON public.traces TO landlaw_runtime USING(true) WITH CHECK(true);
CREATE POLICY counter_runtime ON public.counters TO landlaw_runtime USING(true) WITH CHECK(true);
