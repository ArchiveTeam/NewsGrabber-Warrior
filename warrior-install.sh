#!/bin/sh -e


echo "installing pip3 modules"
if ! sudo pip3 install requests six --upgrade
then
  exit 1
fi

echo "Upgrading pip3"
if ! sudo pip3 install pip --upgrade
then
  exit 1
fi

echo "installing pip modules"
if ! sudo pip install requests six dnspython==1.15.0 youtube_dl wpull==1.2.3 html5lib==0.9999999 --upgrade
then
  exit 1
fi

echo "Upgrading pip"
if ! sudo pip install pip --upgrade
then
  exit 1
fi

echo "Installing / upgrading youtube_dl"
if ! sudo pip install youtube_dl --upgrade
then
  exit 1
fi

echo "Checking youtube-dl status"
if [ -e youtube-dl ]
then
  echo "youtube-dl symlink exists"
else
  ln -s /usr/local/bin/youtube-dl youtube-dl
fi
