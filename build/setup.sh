#!/bin/bash

WORKSPACE=$(pwd)
VIRTUALENV=${WORKSPACE}/ve
SOURCE=$(pwd)

set -ex

rm -rf workspace
ln -s . workspace

cat >Makefile <<EOF
SOURCE = ${SOURCE}
VIRTUALENV = ${VIRTUALENV}
PYTHONPATH = ${SOURCE}:${SOURCE}/bigtest
include \$(SOURCE)/build/Makefile.workspace
EOF

rm -rf ${VIRTUALENV} python
#virtualenv ${VIRTUALENV}
virtualenv ${VIRTUALENV} --system-site-packages
mkdir -p ${VIRTUALENV}/log
#mkdir -p ${VIRTUALENV}/bin
ln -snf ve python
ln -snf bin ${VIRTUALENV}/sbin

export PYTHONPATH=${SOURCE}:${SOURCE}/bigtest

cat >${VIRTUALENV}/bin/bm <<EOF
#!/bin/bash
exec make -C ${WORKSPACE} "\$@"
EOF
chmod +x ${VIRTUALENV}/bin/bm

cp ${SOURCE}/bigtest/bt ${SOURCE}/ve/bin/bt

set +x

echo "+++ Your workspace has been set up in ${WORKSPACE},"
echo "+++ and your shell is put in a Python virtualenv in ${VIRTUALENV}."
echo "+++ In the ve shell, bm is a shortcut for make -C ${WORKSPACE}."
echo "+++ To register your running vms for tests, run"
echo "+++   bm register-vms-floodlight"
echo "+++ To test the controller VM (initial round of integration tests)"
echo "+++   bm check-vms-floodlight"
echo "+++ To run main integration tests"
echo "+++   bm check-tests-floodlight"
echo "+++ To run an individual integration test, just run "
echo "+++   {test}.py "
echo "+++ All test files are under ${WORKSPACE}/floodlight-test/bigtest/"
echo "+++ Once you are done with testing, remember to clean up with"
echo "+++   bm clean"
