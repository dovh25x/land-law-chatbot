-- Preserve Gemini/BGE archives and add a separate E5 index, never mix dimensions.
ALTER TABLE public.chunks DROP CONSTRAINT chunk_embedding_dimension;
ALTER TABLE public.chunks ADD CONSTRAINT chunk_embedding_dimension
 CHECK (embedding IS NULL OR vector_dims(embedding) IN (384,768,1024));
CREATE INDEX chunk_vector_384_idx ON public.chunks USING hnsw
 ((embedding::vector(384)) vector_cosine_ops) WHERE vector_dims(embedding)=384;
