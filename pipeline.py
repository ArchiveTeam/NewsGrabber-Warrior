# encoding=utf8
from distutils.version import StrictVersion
import datetime
import hashlib
import os
import random
import shutil
import socket
import subprocess
import sys
import time
import re
import urllib
from subprocess import call

sys.path.insert(0, os.getcwd())

import warcio
from warcio.archiveiterator import ArchiveIterator
from warcio.warcwriter import WARCWriter

assert hasattr(warcio, 'ATWARCIO'), 'warcio was not imported correctly. Location: ' + warcio.__file__

try:
    import requests
except ImportError:
    print('Please install or update the requests module.')
    sys.exit(1)
    
import seesaw
from seesaw.config import realize, NumberConfigValue
from seesaw.externalprocess import WgetDownload, ExternalProcess
from seesaw.item import ItemInterpolation, ItemValue
from seesaw.pipeline import Pipeline
from seesaw.project import Project
from seesaw.task import SimpleTask, SetItemKey, LimitConcurrent
from seesaw.tracker import PrepareStatsForTracker, GetItemFromTracker, \
    UploadWithTracker, SendDoneToTracker
from seesaw.util import find_executable


# check the seesaw version
if StrictVersion(seesaw.__version__) < StrictVersion("0.8.5"):
    raise Exception("This pipeline needs seesaw version 0.8.5 or higher.")


###########################################################################
# Find a useful Wpull executable.
#
# WPULL_EXE will be set to the first path that
# 1. does not crash with --version, and
# 2. prints the required version string
print(os.getcwd())
WPULL_EXE = find_executable(
    "Wpull",
    re.compile(r"\b1\.2\.3\b"),
    [
        "/usr/local/bin/wpull",
        "./wpull",
        os.path.expanduser("~/.local/share/wpull-1.2.3/wpull"),
        os.path.expanduser("~/.local/bin/wpull"),
        "/usr/bin/wpull",
        "/usr/local/lib/python3.7/site-packages/wpull",
        "./wpull_bootstrap",

    ]
)
YOUTUBE_DL_EXE = find_executable(
    "youtube-dl",
    None, # No version requirements
    [
        "./youtube-dl",
        "/usr/local/bin/youtube-dl",
        "/usr/bin/youtube-dl",
        "youtube-dl",
    ],
    '--version',
)
PYTHON3_EXE = find_executable(
    "Python",
    re.compile(r"^Python 3\."),
    [
        "python",
        "python3",
    ]
)

if not WPULL_EXE:
    raise Exception("No usable Wpull found.")
if not YOUTUBE_DL_EXE:
    raise Exception("No usable youtube-dl found.")

###########################################################################
# The version number of this pipeline definition.
#
# Update this each time you make a non-cosmetic change.
# It will be added to the WARC files and reported to the tracker.
VERSION = "20190531.01"
TRACKER_ID = 'newsgrabber'
TRACKER_HOST = 'tracker.archiveteam.org'


###########################################################################
# This section defines project-specific tasks.
#
# Simple tasks (tasks that do not need any concurrency) are based on the
# SimpleTask class and have a process(item) method that is called for
# each item.
class CheckIP(SimpleTask):
    def __init__(self):
        SimpleTask.__init__(self, "CheckIP")
        self._counter = 0

    def process(self, item):
        # NEW for 2014! Check if we are behind firewall/proxy

        if self._counter <= 0:
            item.log_output('Checking IP address.')
            ip_set = set()

            ip_set.add(socket.gethostbyname('twitter.com'))
            ip_set.add(socket.gethostbyname('facebook.com'))
            ip_set.add(socket.gethostbyname('youtube.com'))
            ip_set.add(socket.gethostbyname('microsoft.com'))
            ip_set.add(socket.gethostbyname('icanhas.cheezburger.com'))
            ip_set.add(socket.gethostbyname('archiveteam.org'))

            if len(ip_set) != 6:
                item.log_output('Got IP addresses: {0}'.format(ip_set))
                item.log_output(
                    'Are you behind a firewall/proxy? That is a big no-no!')
                raise Exception(
                    'Are you behind a firewall/proxy? That is a big no-no!')

        # Check only occasionally
        if self._counter <= 0:
            self._counter = 10
        else:
            self._counter -= 1


class PrepareDirectories(SimpleTask):
    def __init__(self, warc_prefix):
        SimpleTask.__init__(self, "PrepareDirectories")
        self.warc_prefix = warc_prefix

    def process(self, item):
        item_name = item["item_name"]
        escaped_item_name = item_name.replace(':', '_').replace('/', '_').replace('~', '_')
        dirname = "/".join((item["data_dir"], escaped_item_name))

        if os.path.isdir(dirname):
            shutil.rmtree(dirname)

        os.makedirs(dirname)

        item["item_dir"] = dirname
        item["warc_file_base"] = "%s-%s-%s" % (self.warc_prefix, escaped_item_name,
            time.strftime("%Y%m%d-%H%M%S"))

        open("%(item_dir)s/%(warc_file_base)s.warc.gz" % item, "w").close()


class MoveFiles(SimpleTask):
    def __init__(self):
        SimpleTask.__init__(self, "MoveFiles")

    def process(self, item):
        os.rename("%(item_dir)s/%(warc_file_base)s-deduplicated.warc.gz" % item,
              "%(data_dir)s/%(warc_file_base)s-deduplicated.warc.gz" % item)

        shutil.rmtree("%(item_dir)s" % item)

class PrintDebug(SimpleTask):
    def __init__(self):
        SimpleTask.__init__(self, "SimpleTask")
    def process(self, item):
        print("Currently here")
 

class DeduplicateWarcExtProc(ExternalProcess):
    def __init__(self, args):
        call(["python", "-u", "dedupe.py", sourcewarc, " ", destwarc])

class DeduplicateWarcExtProcArgs(object):
    def realize(self, item):
        dedup_args = [
            '%(item_dir)s/%(warc_file_base)s.warc.gz' % item,
            '%(item_dir)s/%(warc_file_base)s-deduplicated.warc.gz' % item
        ]
        sourcewarc = "%(item_dir)s/%(warc_file_base)s.warc.gz" % item
        destwarc = "%(item_dir)s/%(warc_file_base)s.deduplicatedwarc.gz" % item
        print('python -u dedupe.py ' + sourcewarc + ' ' + destwarc)
        call(["python", "-u", "dedupe.py", sourcewarc, " ", destwarc])
        return realize(dedup_args, item)


def get_hash(filename):
    with open(filename, 'rb') as in_file:
        return hashlib.sha256(in_file.read()).hexdigest()

CWD = os.getcwd()
PIPELINE_SHA256 = get_hash(os.path.join(CWD, 'pipeline.py'))
WARRIOR_INSTALL_SHA256 = get_hash(os.path.join(CWD, 'warrior-install.sh'))
WPULL_BOOTSTRAP_SHA256 = get_hash(os.path.join(CWD, 'wpull_bootstrap'))

def stats_id_function(item):
    d = {
        'pipeline_hash': PIPELINE_SHA256,
        'warrior_install_hash': WARRIOR_INSTALL_SHA256,
        'wpull_bootstrap_hash': WPULL_BOOTSTRAP_SHA256,
        'python_version': sys.version,
    }

    return d


class WgetArgs(object):
    def realize(self, item):
        item_name = item['item_name']
        item_type, item_value = item_name.split(':', 1)

        item['item_type'] = item_type
        item['item_value'] = item_value

        wpull_args = [
            WPULL_EXE,
            '-nv',
            '-U', 'ArchiveTeam; Googlebot/2.1',
            '--no-check-certificate',
            '--no-robots',
            '--dns-timeout', '20',
            '--connect-timeout', '20',
            '--read-timeout', '900',
            '--session-timeout', '1800',
            '--tries', '5',
            '--waitretry', '5',
            '--max-redirect', '20',
            '--output-file', ItemInterpolation("%(item_dir)s/wpull.log"),
            '--database', ItemInterpolation("%(item_dir)s/wpull.db"),
            '--delete-after',
            '--page-requisites',
            '--no-parent',
            '--concurrent', '5',
            '--warc-file', ItemInterpolation("%(item_dir)s/%(warc_file_base)s"),
            '--level', '0',
            '--page-requisites-level', '5',
            '--span-hosts-allow', 'page-requisites',
            '--warc-header', 'pipeline-py-sha256: ' + PIPELINE_SHA256,
            '--warc-header', 'warrior-install-sh-sha256: ' + WARRIOR_INSTALL_SHA256,
            '--warc-header', 'operator: Archive Team',
            '--warc-header', 'newsgrabber-dld-script-version: ' + VERSION,
            '--warc-header', ItemInterpolation('ftp-item: %(item_name)s'),
            '--reject-regex', r'(^https?://launcher\.spot\.im/spot/(www\.spot\.im/launcher/|launcher\.spot\.im/|modules/launcher/){3,}bundle\.js)|(https?://static\.xx\.fbcdn\.net/rsrc\.php/)'
        ]

        if '-videos' in item_value:
            wpull_args.append('--youtube-dl')
            wpull_args.append('--youtube-dl-exe')
            wpull_args.append(YOUTUBE_DL_EXE)

        list_url = 'http://master.newsbuddy.net/' + item_value
        list_data = requests.get(list_url)
        #wpull_args.append(list_url)
        if list_data.status_code == 200:
            for url in list_data.text.splitlines():
                url = url.strip()
                wpull_args.append(url)

        if 'bind_address' in globals():
            wpull_args.extend(['--bind-address', globals()['bind_address']])
            print('')
            print('*** Wpull will bind address at {0} ***'.format(
                globals()['bind_address']))
            print('')

        return realize(wpull_args, item)

###########################################################################
# Initialize the project.
#
# This will be shown in the warrior management panel. The logo should not
# be too big. The deadline is optional.
project = Project(
    title="newsgrabber",
    project_html="""
        <img class="project-logo" alt="Project logo" src="http://archiveteam.org/images/thumb/f/f3/Archive_team.png/235px-Archive_team.png" height="50px" title=""/>
        <h2>archiveteam.org <span class="links"><a href="http://archiveteam.org/">Website</a> &middot; <a href="http://tracker.archiveteam.org/newsgrabber/">Leaderboard</a></span></h2>
        <p>Archiving all the news!</p>
    """
)

pipeline = Pipeline(
    CheckIP(),
    GetItemFromTracker("http://%s/%s" % (TRACKER_HOST, TRACKER_ID), downloader,
        VERSION),
    PrepareDirectories(warc_prefix="newsgrabber"),
    WgetDownload(
        WgetArgs(),
        max_tries=2,
        accept_on_exit_code=[0, 4, 8]
    ),
    LimitConcurrent(
        NumberConfigValue(min=1, max=20, default="1",
            name="shared:dedupe_threads", title="Deduplicate threads",
            description="The maximum number of concurrent dedupes."),
DeduplicateWarcExtProc(
            DeduplicateWarcExtProcArgs()
    ) 
    ),
    PrepareStatsForTracker(
        defaults={"downloader": downloader, "version": VERSION},
        file_groups={
            "data": [
                 ItemInterpolation("%(item_dir)s/%(warc_file_base)s-deduplicated.warc.gz")
            ]
        },
        id_function=stats_id_function,
    ),
    PrintDebug(),
    MoveFiles(),
    LimitConcurrent(
        NumberConfigValue(min=1, max=4, default="1",
            name="shared:rsync_threads", title="Rsync threads",
            description="The maximum number of concurrent uploads."),
        UploadWithTracker(
            "http://%s/%s" % (TRACKER_HOST, TRACKER_ID),
            downloader=downloader,
            version=VERSION,
            files=[
                ItemInterpolation("%(data_dir)s/%(warc_file_base)s-deduplicated.warc.gz")
            ],
            rsync_target_source_path=ItemInterpolation("%(data_dir)s/"),
            rsync_extra_args=[
                "--recursive",
                "--partial",
                "--partial-dir", ".rsync-tmp",
            ]
        ),
    ),
    SendDoneToTracker(
        tracker_url="http://%s/%s" % (TRACKER_HOST, TRACKER_ID),
        stats=ItemValue("stats")
    )
)
