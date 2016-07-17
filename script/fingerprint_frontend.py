#!/usr/bin/env python3

"""Generate a file with all md5 hashes of the assets."""
from collections import OrderedDict
import glob
import hashlib
import json

fingerprint_file = 'homeassistant/components/frontend/version.py'
base_dir = 'homeassistant/components/frontend/www_static/'


def fingerprint():
    """Fingerprint the frontend files."""
    files = (glob.glob(base_dir + '**/*.html') +
             glob.glob(base_dir + '*.html') +
             glob.glob(base_dir + 'core.js'))

    md5s = OrderedDict()

    for fil in sorted(files):
        name = fil[len(base_dir):]
        with open(fil) as fp:
            md5 = hashlib.md5(fp.read().encode('utf-8')).hexdigest()
        md5s[name] = md5

    template = """\"\"\"DO NOT MODIFY. Auto-generated by script/fingerprint_frontend.\"\"\"

FINGERPRINTS = {}
"""

    result = template.format(json.dumps(md5s, indent=4))

    with open(fingerprint_file, 'w') as fp:
        fp.write(result)

if __name__ == '__main__':
    fingerprint()
