CREATE TABLE IF NOT EXISTS public.answer_cache(
 key text PRIMARY KEY,session_id text NOT NULL REFERENCES public.sessions(id) ON DELETE CASCADE,
 payload text NOT NULL,expires_at text NOT NULL);
ALTER TABLE public.answer_cache ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.answer_cache FROM anon,authenticated;
GRANT SELECT,INSERT,UPDATE,DELETE ON public.answer_cache TO landlaw_runtime;
CREATE POLICY cache_runtime ON public.answer_cache TO landlaw_runtime USING(true) WITH CHECK(true);
