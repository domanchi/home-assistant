.PHONY: test
test: virtualenv
	venv/bin/python -m pytest modules/deploy/tests -v

virtualenv: venv/bin/activate
venv/bin/activate:
	test -d venv || virtualenv venv
	venv/bin/pip install -r requirements-minimal.txt
	touch venv/bin/activate

# Unencrypt secrets stored at rest.
	/usr/bin/git secret reveal