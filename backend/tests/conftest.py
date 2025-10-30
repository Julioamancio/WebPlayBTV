import pytest
from app.services import rate_limit as rl


@pytest.fixture(autouse=True)
def reset_rate_limit_state():
    # Antes do teste: nada a fazer
    yield
    # Depois de cada teste: limpar estado e restaurar desativado
    rl._requests.clear()
    rl.RATE_LIMIT_ENABLED = False
