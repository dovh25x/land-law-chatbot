"""Pinned E5 embedding contract shared by corpus and queries."""
def contract(settings, release=None):
    from .local_embedding import MODEL
    expected = {'provider':'local_onnx','model':MODEL['name'],
                'dimensions':384,'format_version':'v1','local_model_spec':dict(MODEL)}
    if release:
        value = release.get('embedding_contract')
        if value != expected:
            raise ValueError('Unsupported embedding contract; pinned E5 is required')
    elif (settings.embedding_provider,settings.embedding_model,settings.embedding_dimensions) != ('local_onnx',MODEL['name'],384):
        raise ValueError('Unsupported embedding contract')
    return expected
