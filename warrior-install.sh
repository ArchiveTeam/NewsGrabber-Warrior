#!/bin/sh -e

echo "installing pip requests"
if ! sudo pip install requests --upgrade
then
  exit 1
fi

echo "installing pip six"
if ! sudo pip install six --upgrade
then
  exit 1
fi

sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt-get update && sudo apt-get install -y unzip python3.4

if ! sudo pip3 install virtualenv
then
  exit 1
fi
virtualenv -p /usr/bin/python3.4 pipeline_env
. pipeline_env/bin/activate
if  [ -f "/usr/local/bin/wpull" ]; 
  then
  echo "wpull 1.2.3 already install"
fi
if  [ ! -f "v1.2.3.zip" ]; 
  then 
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
if  [ -f "youtube-dl" ]; 
  then
  echo "youtube-dl already exists"
fi
if  [ ! -f "youtube-dl" ]; 
  then
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

echo "Upgrading pip"
if ! sudo pip install pip --upgrade
then
  exit 1
fi

# check virtual environment for python
python3 checkvenv.py
