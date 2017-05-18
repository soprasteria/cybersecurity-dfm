DOC_DIR = doc

.init:
	#Dirty quickfix about setuptools and python2.7
	# More details here https://github.com/geerlingguy/drupal-vm/issues/562
	rm -fr /usr/local/lib/python2.7/dist-packages/distribute*
	pip install -r requirements.txt

default: .init .doc
	python setup.py build
.doc:
	$(MAKE) -C $(DOC_DIR) html
.test:
	python tests
