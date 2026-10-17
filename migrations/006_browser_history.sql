-- No conversation payloads on the application server. This is intentionally irreversible.
DELETE FROM public.answer_cache;
DELETE FROM public.traces;
DELETE FROM public.messages;
REVOKE ALL ON public.answer_cache, public.traces, public.messages FROM landlaw_runtime;
CREATE TABLE public.turns(id text PRIMARY KEY,session_id text NOT NULL REFERENCES public.sessions(id) ON DELETE CASCADE,
 fingerprint text NOT NULL,status text NOT NULL,lease_until text NOT NULL,created_at text NOT NULL);
CREATE UNIQUE INDEX running_turn_session ON public.turns(session_id) WHERE status='running';
ALTER TABLE public.turns ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.turns FROM anon,authenticated;
GRANT SELECT,INSERT,UPDATE,DELETE ON public.turns TO landlaw_runtime;
CREATE POLICY runtime_turns ON public.turns TO landlaw_runtime USING(true) WITH CHECK(true);
CREATE TABLE public.source_reviews(id text PRIMARY KEY,release_id text NOT NULL REFERENCES public.releases(id),
 document_id text NOT NULL,checksum text NOT NULL,checked_at text NOT NULL,status text NOT NULL,receipt text NOT NULL);
ALTER TABLE public.source_reviews ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.source_reviews FROM anon,authenticated;
GRANT SELECT ON public.source_reviews TO landlaw_runtime;
CREATE POLICY runtime_source_reviews ON public.source_reviews FOR SELECT TO landlaw_runtime USING(true);
-- Runtime may update only cooldown metadata; it still cannot publish corpus.
CREATE POLICY runtime_cooldown ON public.app_state FOR ALL TO landlaw_runtime
 USING(key='provider_cooldown_until') WITH CHECK(key='provider_cooldown_until');
GRANT INSERT,UPDATE ON public.app_state TO landlaw_runtime;
