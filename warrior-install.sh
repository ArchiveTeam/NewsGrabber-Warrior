#!/bin/sh -e

sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt-get update && sudo apt-get install -y unzip python3.4

sudo pip3 install virtualenv
virtualenv -p /usr/bin/python3.4 pipeline_env
. pipeline_env/bin/activate
wget https://github.com/ArchiveTeam/wpull/archive/v1.2.3.zip && unzip v1.2.3.zip && cd wpull-1.2.3/
copy ../wpullsetup.py setup.py
sudo python3 setup.py install 
# Yes do this again to fix a bug
sudo python3 setup.py install
cd ..
sudo pip3 install lastversion
#lastversion ytdl-org/youtube-dl
wget https://github.com/ytdl-org/youtube-dl/releases/download/2019.05.20/youtube-dl
chmod +x youtube-dl

if ! sudo pip3 freeze | grep -q requests
then
  echo "Installing requests"
  if ! sudo pip3 install requests
  then
    exit 1
  fi
fi

if ! sudo pip3 freeze | grep -q six
then
  echo "Installing six"
  if ! sudo pip3 install six
  then
    exit 1
  fi
fi

echo "installing pip requests"
if ! sudo pip2 install requests --upgrade
then
  exit 1
fi

echo "installing pip six"
if ! sudo pip2 install six --upgrade
then
  exit 1
fi

echo "Upgrading pip"
if ! sudo pip2 install pip --upgrade
then
  exit 1
fi


# V wpull V

VERSION='1.2.3'
TARBALL_32='wpull-1.2.3-linux-i686-3.4.3-20160302011132.zip'
CHECKSUM_32=0ef742c65336ad4c3205419782f2cec5
TARBALL_64='wpull-1.2.3-linux-x86_64-3.4.3-20160302011013.zip'
CHECKSUM_64=e1e792acd2cd0e4b2a5e35d897aa9d64
INSTALL_DIR="${HOME}/.local/share/wpull-${VERSION}/"

if [ "`uname -m`" = "x86_64" ]; then
    TARBALL=${TARBALL_64}
    CHECKSUM=${CHECKSUM_64}
else
    TARBALL=${TARBALL_32}
    CHECKSUM=${CHECKSUM_32}
fi

DOWNLOAD_URL="https://launchpad.net/wpull/trunk/v${VERSION}/+download/${TARBALL}"

set +e
${INSTALL_DIR}/wpull --version > /dev/null 2>&1
RETVAL=$?
set -e

echo "Test for Wpull returned $RETVAL"

if [ $RETVAL -ne 0 ]; then
    echo "Downloading Wpull"

    TMP_DIR=/tmp/${CHECKSUM}/
    mkdir -p ${TMP_DIR}

    wget $DOWNLOAD_URL --continue --directory-prefix ${TMP_DIR}

    echo "Verify checksum"
    RESULT_CHECKSUM=`md5sum "${TMP_DIR}/${TARBALL}" | cut -f 1 -d " "`
    if [ "$RESULT_CHECKSUM" != "$CHECKSUM" ]; then
        echo "Checksum failed. Got ${RESULT_CHECKSUM}. Need ${CHECKSUM}"
        exit 1
    fi

    echo "Extracting contents to ${INSTALL_DIR}"
    mkdir -p "${INSTALL_DIR}"
    # tar -xzf "${TMP_DIR}/${TARBALL}" --strip-components 1 --directory "${INSTALL_DIR}"
    python -c "import zipfile; f=zipfile.ZipFile('${TMP_DIR}/${TARBALL}'); f.extractall('${INSTALL_DIR}')"
    chmod +x ${INSTALL_DIR}/wpull

    echo Done
fi
