#!/usr/bin/python3
# vi:sw=4:ts=4:ai:cindent:et
# identify uninstallable kernel image packages (i.e. not latest,
# running, or dependency-tracking)
# requires the python-apt module to be installed

# Copyright Tim Cutts <tim@thecutts.org>, 2017-2024

import getopt, sys, platform, re

try:
    import apt, apt_pkg
except ImportError:
    print("Please install the python-apt package and try again")
    sys.exit(1)

try:
    opts, args = getopt.getopt(sys.argv[1:], "uv", ["uninstall", "verbose"])
except getopt.GetoptError as err:
    print(str(err))
    sys.exit(2)

uninstall = None
verbose = None
for o, a in opts:
    if o in ("-u", "--uninstall"):
        uninstall = True
    elif o in ("-v", "--verbose"):
        verbose = True
    else:
        assert False, "unhandled option"

running = platform.uname()[2]
latest = ""
installed = []

cache = apt.Cache()
for pkg in cache.keys():
    if pkg == 'linux-image':
        continue
    if re.match('linux-image-[a-z]+(-pae)?$', pkg):
        continue
    if 'lustre' in pkg:
        continue
    if 'linux-image' in pkg:
        if cache[pkg].is_installed:
            installed.append(pkg)
            if apt_pkg.version_compare(pkg, latest) > 0:
                latest = pkg

touninstall = [x for x in installed if apt_pkg.version_compare(x, latest) < 0 and not running in x]

latest_headers = latest.replace('image','headers')
running_headers = "linux-headers-" + running
keep_headers = []
remove_headers = []

for pkg in cache.keys():
    if cache[pkg].is_installed and re.match('linux-headers-\d',pkg):
        # Ignore small meta-packages
        if cache[pkg].versions[0].installed_size < 1000000:
            continue
        if 'lustre' in pkg:
            continue
        if pkg in latest_headers or pkg in running_headers:
            keep_headers.append(pkg)
            continue
        remove_headers.append(pkg)

if verbose:
    print("Latest:", latest)
    print("Running:", running)
    print("Installed:", sorted(installed))
    print("Keep headers:", sorted(keep_headers))
    print("Remove headers:", sorted(remove_headers))

if not (touninstall + remove_headers):
    if verbose:
        print("Nothing to uninstall!")
else:
    for pkg in touninstall + remove_headers:
        cache[pkg].mark_delete()
    for pkg in keep_headers:
        cache[pkg].mark_install()
    if verbose:
        print("Will install: ", sorted([ x.name for x in cache.get_changes() if x.marked_install ]))
        print("Will remove: ", sorted([ x.name for x in cache.get_changes() if x.marked_delete ]))
    if uninstall:
        cache.commit()
    else:
        cache.clear()
