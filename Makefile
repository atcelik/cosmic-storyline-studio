# Usage: make all EP=ep01      (add DRAFT=1 for a fast half-resolution preview)
EP ?= ep01
DRAFT ?= 0
PY ?= python3
E_JSON = episodes/$(EP)/episode.json
D = $(if $(filter 1,$(DRAFT)),--draft,)

check:
	$(PY) scripts/validate.py $(E_JSON)
merge:
	$(PY) scripts/merge_parts.py episodes/$(EP)
sheets:
	$(PY) scripts/contact_sheet.py $(E_JSON)
pick-auto:
	$(PY) scripts/pick.py $(E_JSON) --auto
validate:
	$(PY) scripts/validate.py $(E_JSON) --assets
publish-check:
	$(PY) scripts/validate.py $(E_JSON) --assets --strict
assets:
	$(PY) scripts/get_assets.py episodes/$(EP)
assets-search:
	$(PY) scripts/get_assets.py episodes/$(EP) --search
fetch:
	$(PY) scripts/fetch_nasa.py $(E_JSON)
tts:
	$(PY) scripts/tts.py $(E_JSON) $(if $(ENGINE),--engine $(ENGINE),)
render:
	$(PY) scripts/render.py $(E_JSON) $(D)
audio:
	$(PY) scripts/audio.py $(E_JSON) $(D)
meta:
	$(PY) scripts/meta.py $(E_JSON)
all: validate tts render audio meta
smoke:
	$(PY) tests/smoke.py
.PHONY: assets assets-search check merge sheets pick-auto validate publish-check fetch tts render audio meta all smoke
