-- Keep request-time metadata separate from the large immutable vector archive.
CREATE TABLE public.release_metadata (
  id text PRIMARY KEY REFERENCES public.releases(id) ON DELETE CASCADE,
  payload text NOT NULL
);
INSERT INTO public.release_metadata(id,payload)
SELECT id, jsonb_set(payload::jsonb,'{documents}',
  (SELECT coalesce(jsonb_agg(d - 'chunks'),'[]'::jsonb)
   FROM jsonb_array_elements(payload::jsonb->'documents') d))::text
FROM public.releases;
ALTER TABLE public.release_metadata ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.release_metadata FROM anon, authenticated;
GRANT SELECT ON public.release_metadata TO landlaw_runtime;
CREATE POLICY runtime_metadata_read ON public.release_metadata FOR SELECT TO landlaw_runtime USING (true);
