#!/usr/bin/python

# Based on an example from http://code.google.com/p/pybonjour/

import select
import pybonjour

class BonjourForwarder(object):
    def __init__(self, out_socket, regtype, timeout=1):
        self.out_socket = out_socket

        self.regtype = regtype
        self.timeout = timeout
        self.resolved = []

    def start(self):
        browse_sdRef = pybonjour.DNSServiceBrowse(
            regtype=self.regtype,
            callBack=self._browse_callback)

        try:
            while True:
                # Bonjour needs a timeout when resolving a service to keep from
                # overloading the network with traffic.
                rlist, wlist, xlist = select.select([browse_sdRef], [], [],
                    self.timeout)

                if browse_sdRef in rlist:
                    pybonjour.DNSServiceProcessResult(browse_sdRef)
        finally:
            browse_sdRef.close()

    def _browse_callback(self,
            sdRef,
            flags,
            interfaceIndex,
            errorCode,
            serviceName,
            regtype,
            replyDomain):
        # Ignore this message if it's an error.
        if errorCode != pybonjour.kDNSServiceErr_NoError:
            return

        # Alert our watchers that a service disconnected.
        if not (flags & pybonjour.kDNSServiceFlagsAdd):
            self.out_socket.send_json({
                'type': 'disconnect',
                'name': serviceName,
                'domain': replyDomain})
            return

        resolve_sdRef = pybonjour.DNSServiceResolve(
            0,
            interfaceIndex,
            serviceName,
            regtype,
            replyDomain,
            self._resolve_callback)

        try:
            while not self.resolved:
                rlist, wlist, xlist = select.select([resolve_sdRef], [], [],
                    self.timeout)

                if resolve_sdRef in rlist:
                    pybonjour.DNSServiceProcessResult(resolve_sdRef)
                else:
                    print 'timed out'
                    break
            else:
                self.resolved.pop()
        finally:
            resolve_sdRef.close()

    def _resolve_callback(self,
            sdRef,
            flags,
            interfaceIndex,
            errorCode,
            fullname,
            hosttarget,
            port,
            txtRecord):
        if errorCode == pybonjour.kDNSServiceErr_NoError:
            self.resolved.append(True)
            self.out_socket.send_json({
                'type': 'resolved',
                'fullname': fullname,
                'hosttarget': hosttarget,
                'port': port})
