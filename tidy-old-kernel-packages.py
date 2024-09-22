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

class KernelPackageUninstaller:
    def __init__(self, verbose = False):
        self.verbose = verbose
        self.apt_cache = apt.Cache();
        self.remove_header_list = [];
        self.remove_kernel_list = [];
        self.keep_header_list = [];
        self.installed_header_list = [];
        self.running_kernel = platform.uname()[2];
        self.get_installed_kernels()
        self.get_header_package_lists()
    

    def uninstall(self, doit = False):

        for pkg in self.remove_kernel_list + self.remove_header_list:
            self.apt_cache[pkg].mark_delete()
        for pkg in self.keep_header_list:
            self.apt_cache[pkg].mark_install()

        if self.verbose:
            print("Will install: ",
                sorted([ x.name for x in self.apt_cache.get_changes()
                      if x.marked_install ]))
            print("Will remove: ",
                sorted([ x.name for x in self.apt_cache.get_changes()
                      if x.marked_delete ]))
            
        if doit:
            self.apt_cache.commit()
        else:
            self.apt_cache.clear()

    def get_header_package_lists(self):
        latest_headers = self.latest_kernel.replace('image','headers')
        running_headers = "linux-headers-" + self.running_kernel
    
        for pkg in self.apt_cache.keys():
            if self.apt_cache[pkg].is_installed and re.match('linux-headers-\d',pkg):
                # Ignore small meta-packages
                if self.apt_cache[pkg].versions[0].installed_size < 1000000:
                    continue
                if 'lustre' in pkg:
                    continue
                if pkg in latest_headers or pkg in running_headers:
                    self.keep_header_list.append(pkg)
                    continue
                self.remove_header_list.append(pkg)

    def get_installed_kernels(self):
        latest = ""
        self.installed_kernels = []
        for pkg in self.apt_cache.keys():
            if pkg == 'linux-image':
                continue
            if re.match('linux-image-[a-z]+(-pae)?$', pkg):
                continue
            if 'lustre' in pkg:
                continue
            if 'linux-image' in pkg:
                if self.apt_cache[pkg].is_installed:
                    self.installed_kernels.append(pkg)
                if apt_pkg.version_compare(pkg, latest) > 0:
                    latest = pkg
        self.latest_kernel = latest
        self.remove_kernel_list = [x for x in self.installed_kernels
                                   if apt_pkg.version_compare(x, self.latest_kernel) < 0 and not self.running_kernel in x]
        
    def describe_plan(self):
        if verbose:
            print("Latest:", self.latest_kernel)
            print("Running:", self.running_kernel)
            print("Installed:", sorted(self.installed_kernels))
            print("Keep headers:", sorted(self.keep_header_list))
            print("Remove headers:", sorted(self.remove_header_list))

def main():
    get_options()

    tidy_tool = KernelPackageUninstaller(verbose)
    tidy_tool.describe_plan()
    tidy_tool.uninstall(uninstall)    

if __name__ == "__main__":
    main()