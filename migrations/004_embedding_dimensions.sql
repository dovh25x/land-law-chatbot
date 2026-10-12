-- Preserve old vectors and support explicit, dimension-filtered expression indexes.
DROP INDEX IF EXISTS public.chunk_vector_idx;
ALTER TABLE public.chunks ALTER COLUMN embedding TYPE vector USING embedding::vector;
ALTER TABLE public.chunks ADD CONSTRAINT chunk_embedding_dimension
 CHECK (embedding IS NULL OR vector_dims(embedding) IN (768,1024));
CREATE INDEX chunk_vector_768_idx ON public.chunks USING hnsw
 ((embedding::vector(768)) vector_cosine_ops) WHERE vector_dims(embedding)=768;
CREATE INDEX chunk_vector_1024_idx ON public.chunks USING hnsw
 ((embedding::vector(1024)) vector_cosine_ops) WHERE vector_dims(embedding)=1024;
