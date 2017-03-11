from twisted.web import server, resource
from twisted.web.server import Site
from twisted.internet import protocol, reactor
from twisted.python import log
from twisted.python.logfile import DailyLogFile


import json, sys, os

LISTEN_PORT = os.environ.get('LISTEN_PORT', 8080)

isCurrentlyPlaying = False
mpvProtocol = None

class MPVProtocol(protocol.Protocol):

    def errReceived(self, data):
        for line in data.split('\n'):
            log.msg("mpv stderr: %s" % line)

    def outReceived(self, data):
        for line in data.split('\n'):
            log.msg("mpv stdout: %s" % line)

    def childDataReceived(self, name, data):
        for line in data.split('\n'):
            log.msg("mpv output: %s" % line)

    def childConnectionLost(self, childFD):
        pass
            
    def processEnded(self, status):
        global isCurrentlyPlaying
        log.msg("Done playing, exited with status %s" % status)
        isCurrentlyPlaying = False
        mpvProtocol = None

    def kill(self):
        self.transport.signalProcess("KILL")

class PlayResource(resource.Resource):

    def render_POST(self, request):
        path = request.args.get('path', request.content.getvalue())
        if not path:
            request.setResponseCode(400)
            return ""
        if isCurrentlyPlaying:
            request.setResponseCode(409)
            return ""

        if path.startswith("LCL"):
            path="/media/AMD/"+path[3:]
            path = path.strip('\n')

        log.msg("Playing %s" % path)
        self.spawnMPV(path)
        request.setResponseCode(201)
        return ""

    def render_DELETE(self, request):
        if not isCurrentlyPlaying:
            request.setResponseCode(409)
            return ""
        mpvProtocol.kill()
        request.setResponseCode(201)
        return ""
        
    def spawnMPV(self, path):
        global mpvProtocol
        global isCurrentlyPlaying
        isCurrentlyPlaying = True
        mpvProtocol = MPVProtocol()
        reactor.spawnProcess(mpvProtocol, 'mpv', ['mpv', '--no-video', path], env=os.environ)

if __name__ == "__main__":
    log.startLogging(sys.stdout)
    root = resource.Resource()
    root.putChild("play", PlayResource())
    factory = Site(root)
    reactor.listenTCP(LISTEN_PORT, factory)
    reactor.run()
