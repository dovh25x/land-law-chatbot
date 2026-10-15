import pytest
from landlaw.provider import Budget, BudgetExceeded, GroqProvider, ProviderUnavailable

def test_llm_budget_and_invalid_vectors():
    b=Budget()
    for _ in range(6):b.llm()
    with pytest.raises(BudgetExceeded):b.llm()
    with pytest.raises(ProviderUnavailable):GroqProvider.normalize_vector([0.0]*384)
    with pytest.raises(ProviderUnavailable):GroqProvider.normalize_vector([float('nan')]*384)
