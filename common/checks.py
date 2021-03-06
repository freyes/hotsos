#!/usr/bin/python3
import re

from common import (
    cli_helpers,
)

SVC_EXPR_TEMPLATE = r".+\S*(\s|(bin|[0-9]+)/)({})(\s+.+|$)"


class ServiceChecksBase(object):
    """This class should be used by any plugin that wants to identify
    and check the status of running services."""

    def __init__(self, service_exprs, hint_range=None):
        """
        @param service_exprs: list of python.re expressions used to match a
        service name.
        @param hint_range: optional range reflecting a range that can be
                           extracted from any of the provided expressions and
                           used as a pre-search before doing a full search in
                           order to reduce unnecessary full searches.
        """
        self.services = {}
        self.service_exprs = []

        for expr in service_exprs:
            hint = None
            if hint_range:
                start, end = hint_range
                hint = expr[start:end]

            self.service_exprs.append((expr, hint))

        self.ps_func = cli_helpers.get_ps

    def get_service_info_str(self):
        """Create a list of "<service> (<num running>)" for running services
        detected. Useful for display purposes."""
        service_info_str = []
        for svc in sorted(self.services):
            num_daemons = self.services[svc]["ps_cmds"]
            service_info_str.append("{} ({})".format(svc, len(num_daemons)))

        return service_info_str

    def _get_running_services(self):
        """
        Execute each provided service expression against lines in ps and store
        each full line in a list against the service matched.
        """
        for line in self.ps_func():
            for expr, hint in self.service_exprs:
                if hint:
                    ret = re.compile(hint).search(line)
                    if not ret:
                        continue

                """
                look for running process with this name.
                We need to account for different types of process binary e.g.

                /snap/<name>/1830/<svc>
                /usr/bin/<svc>

                and filter e.g.

                /var/lib/<svc> and /var/log/<svc>
                """
                ret = re.compile(SVC_EXPR_TEMPLATE.format(expr)).match(line)
                if ret:
                    svc = ret.group(3)
                    if svc not in self.services:
                        self.services[svc] = {"ps_cmds": []}

                    self.services[svc]["ps_cmds"].append(ret.group(0))

    def __call__(self):
        """This can/should be extended by inheriting class."""
        self._get_running_services()


class PackageChecksBase(object):
    """This class should be used by any plugin that wants to identify
    and check the status of some package_exprs."""

    def __init__(self, package_exprs):
        """
        @param package_exprs: list of python.re expressions used to match
        package names.
        """
        self.package_exprs = package_exprs
        self.pkg_match_expr_template = \
            r"^ii\s+(python3?-)?({}[0-9a-z\-]*)\s+(\S+)\s+.+"
        self._packages = []

    @property
    def packages(self):
        if self._packages:
            return self._packages

        dpkg_l = cli_helpers.get_dpkg_l()
        if not dpkg_l:
            return

        for line in dpkg_l:
            for pkg in self.package_exprs:
                expr = self.pkg_match_expr_template.format(pkg)
                ret = re.compile(expr).match(line)
                if ret:
                    pyprefix = ret[1] or ""
                    result = "{}{} {}".format(pyprefix, ret[2], ret[3])
                    self._packages.append(result)

        return self._packages
