"""Pytest configuration for factory tests."""


def pytest_addoption(parser):
    parser.addoption('--skip-llm', action='store_true', default=False, help='Skip LLM judge tests')
    parser.addoption('--skip-types', nargs='+', default=[], help='Skip scenario types')


def pytest_configure(config):
    config.addinivalue_line('markers', 'llm_judge: marks tests requiring ANTHROPIC_API_KEY')
    config.addinivalue_line('markers', 'gpu: marks tests requiring GPU')
