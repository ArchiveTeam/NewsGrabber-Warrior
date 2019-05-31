#!/bin/sh -e

sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt-get update && sudo apt-get install -y unzip python3.4

sudo pip3 install virtualenv
virtualenv -p /usr/bin/python3.4 pipeline_env
. pipeline_env/bin/activate
set +e
v1.2.3.zip /dev/null 2>&1
RETVAL=$?
set -e
if [ $RETVAL -ne 0 ]; then
  echo "Downloading Wpull"
  wget https://github.com/ArchiveTeam/wpull/archive/v1.2.3.zip && unzip -o v1.2.3.zip && cd wpull-1.2.3/
  cp ../wpullsetup.py setup.py
  sudo python3 setup.py install 
  # Yes do this again to fix a bug
  sudo python3 setup.py install
  cd ..
  echo "Done downloading / installing wpull"
 fi
sudo pip3 install lastversion
#lastversion ytdl-org/youtube-dl
set +e
youtube-dl /dev/null 2>&1
RETVAL=$?
set -e
if [ $RETVAL -ne 0 ]; then
  wget https://github.com/ytdl-org/youtube-dl/releases/download/2019.05.20/youtube-dl
  sudo chmod +x youtube-dl
fi

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

# check virtual environment for python
python3 checkvenv.py
