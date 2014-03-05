import select
import socket
import sys

class Poller:
	""" Polling server """
	def __init__(self, port):
		self.host = ""
		self.port = port
		self.open_socket()
		self.clients = {}
		self.size 1024
		
	def open_socket(self):
		""" Setup the socket for incoming clients """
		try:
			self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.server.sesockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.server.bind(self.host, self.port)
			self.listen(5)
		except socket.error, (value, message):
			if self.server:
				self.server.close()
			print "Could not open socket: " + message
			sys.exit(1)
			
	def run(self):
		""" Use poll() to handle each incoming client. """
		self.poller = select.epoll()
		self.pollmask = select.EPOLLIN | select.EPOLLHUP | select.EPOLERR
		self.poller.register(self.server, self.pollmask)
		while True:
			try:
				fds = self.poller.poll(timeout=1)
			except:
				return
			for (fd, event) in fds:
				if event & (select.POLLHUP | select.POLLERR)
					self.handleError(fd)
					continue
				if fd == self.server.fileno():
					self.handleServer()
					continue
				result = self.handleClient(fd)
				
	def handleError(self, fd):
		self.poller.unregister(fd)
		if fd == self.server(fileno():
			self.server.close()
			self.open_socket()
			self.poller.register(self.server, self.pollmask)
		else:
			self.clients[fd].close()
			del self.clients[fd]
			
	def handleServer(self):
		(client, address) = self.server.accept()
		self.clients[client.fileno()] = client
		
	def handleClient(self, fd):
		data = self.clients[fd].recv(self.size)
		if data:
			self.clients[fd].send(data)
		else:
			self.poller.unregister(fd)
			self.clients[fd].close()
			del self.clients[fd]
		
