from facefusion import wording


def test_get() -> None:
	assert wording.get('python_not_supported')
	assert wording.get('help.source_paths')
	assert wording.get('invalid') is None

def test_updated_buttons() -> None:
	assert wording.get('uis.start_button') == '▶ START'
	assert wording.get('uis.stop_button') == '■ STOP'
	assert wording.get('uis.clear_button') == '🗑️ CLEAR'
