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

uninstall = None
verbose = None

def get_options():
    global verbose, uninstall
    try:
        opts, args = getopt.getopt(sys.argv[1:], "uv", ["uninstall", "verbose"])
    except getopt.GetoptError as err:
        print(str(err))
        sys.exit(2)

    for o, a in opts:
        if o in ("-u", "--uninstall"):
            uninstall = True
        elif o in ("-v", "--verbose"):
            verbose = True
        else:
            assert False, "unhandled option"

def uninstall_kernel_packages(apt_cache, to_uninstall, keep_headers, remove_headers):
    for pkg in to_uninstall + remove_headers:
        apt_cache[pkg].mark_delete()
    for pkg in keep_headers:
        apt_cache[pkg].mark_install()
    if verbose:
        print("Will install: ",
              sorted([ x.name for x in apt_cache.get_changes()
                      if x.marked_install ]))
        print("Will remove: ",
              sorted([ x.name for x in apt_cache.get_changes()
                      if x.marked_delete ]))
    if uninstall:
        apt_cache.commit()
    else:
        apt_cache.clear()

def get_header_package_lists(running, cache, latest, keep_headers, remove_headers):
    latest_headers = latest.replace('image','headers')
    running_headers = "linux-headers-" + running
    
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

def get_installed_kernels(installed, cache):
    latest = ""
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
    return latest

def main():
    get_options()

    running_kernel = platform.uname()[2]
    installed_kernels = []

    apt_cache = apt.Cache()
    latest_kernel = get_installed_kernels(installed_kernels, apt_cache)

    to_uninstall = [x for x in installed_kernels
                    if apt_pkg.version_compare(x, latest_kernel) < 0 and not running_kernel in x]

    keep_headers = []
    remove_headers = []
    get_header_package_lists(running_kernel, apt_cache, latest_kernel, keep_headers, remove_headers)

    if verbose:
        print("Latest:", latest_kernel)
        print("Running:", running_kernel)
        print("Installed:", sorted(installed_kernels))
        print("Keep headers:", sorted(keep_headers))
        print("Remove headers:", sorted(remove_headers))

    if (to_uninstall + remove_headers):
        uninstall_kernel_packages(apt_cache, to_uninstall, keep_headers, remove_headers)
    else:
        if verbose:
            print("Nothing to uninstall!")        

if __name__ == "__main__":
    main()