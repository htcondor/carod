.PHONY: build condor-job-hooks condor-low-latency

RPMBUILD_DIRS := BUILD BUILDROOT RPMS SOURCES SPECS SRPMS

NAME := condor-low-latency
SPEC := ${NAME}.spec
VERSION := $(shell grep -i version: "${SPEC}" | awk '{print $$2}')
RELEASE := $(shell grep -i 'define rel' "${SPEC}" | awk '{print $$3}')
SOURCE := ${NAME}-${VERSION}-${RELEASE}.tar.gz
DIR := ${NAME}-${VERSION}

build: condor-low-latency

condor-low-latency: SPECS/${SPEC} SOURCES/${SOURCE}
	mkdir -p BUILD RPMS SRPMS
	rpmbuild --define="_topdir ${PWD}" -ba SPECS/${SPEC}

SPECS/${SPEC}: ${SPEC}
	mkdir -p SPECS
	cp -f ${SPEC} SPECS

SOURCES/${SOURCE}: carod config/carod.conf
	mkdir -p SOURCES
	rm -rf ${DIR}
	mkdir ${DIR}
	mkdir ${DIR}/config
	cp -f carod ${DIR}
	cp -f config/carod.conf ${DIR}/config
	cp -f LICENSE-2.0.txt INSTALL ${DIR}
	tar -cf ${SOURCE} ${DIR}
	mv "${SOURCE}" SOURCES

clean:
	rm -rf ${RPMBUILD_DIRS} ${DIR}
