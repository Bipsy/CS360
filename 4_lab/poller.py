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
		self.cache = {}
		self.size = 1024
		
	def open_socket(self):
		""" Setup the socket for incoming clients """
		try:
			self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.server.bind((self.host, self.port))
			self.server.listen(5)
		except socket.error, (value, message):
			if self.server:
				self.server.close()
			print "Could not open socket: " + message
			sys.exit(1)
			
	def run(self):
		""" Use poll() to handle each incoming client. """
		self.poller = select.epoll()
		self.pollmask = select.EPOLLIN | select.EPOLLHUP | select.EPOLLERR
		self.poller.register(self.server, self.pollmask)
		while True:
			try:
				fds = self.poller.poll(timeout=1)
			except:
				return
			for (fd, event) in fds:
				if event & (select.POLLHUP | select.POLLERR):
					self.handleError(fd)
					continue
				if fd == self.server.fileno():
					self.handleServer()
					continue
				result = self.handleClient(fd)
				
	def handleError(self, fd):
		self.poller.unregister(fd)
		if fd == self.server(fileno()):
			self.server.close()
			self.open_socket()
			self.poller.register(self.server, self.pollmask)
		else:
			self.clients[fd].close()
			del self.clients[fd]
			
	def handleServer(self):
		while True:
			try:
				(client, address) = self.server.accept()
			except socket.error, (value, message):
				if value == errno.EAGAIN or errno.EWOULDBLOCK:
					return
				print traceback.format_exc()
				sys.exit()
			client.setblocking(0)
			self.clients[client.fileno()] = client
			self.cache[client.fileno()] = ""
			self.poller.register(client.fileno(), self.pollmask)
		
	def handleClient(self, fd):
		print "handling client"
		while True:
			try:
				data = self.clients[fd].recv(self.size)
				self.cache[fd] += data
				end_index = self.cache[fd].find("\r\n\r\n")
				if end_index != -1:
					cached_message = self.cache[fd]
					handleHttpRequest(fd, cached_message[:end_index+4])
					self.cache[fd] = cached_message[end_index+4:]
					break;
				if not data:
					cleanup(fd)
			except socket.error, (value, message):
				if data == 'EAGAIN' or data == 'EWOULDBLOCK':
					break
				print traceback.format_exc()
				sys.exit()
			
	def handleHttpRequest(self, fd, message):
		lines = message.splitlines()
		first_line = lines[0].split()
		if first_line[0] != "GET":
			cleanup(fd)
		url = first_line[1]
		header_lines = lines[1:]
		headers = {}
		for line in header_lines:
			header = line.split(':')
			if header.size() < 2:
				continue
			headers[header[0]] = header[1]
		url_parsed = url.split('/')
		file_name = url_parsed[-1]
		if file_name == "":
			file_name = "index.html"
		with open(file_name, 'rb') as f:
			self.clients[fd].send(f.read())
		
			
		
	def cleanup(self, fd):
		self.poller.unregister(fd)
		self.clients[fd].close()
		del self.clients[fd]
		return

		
		
		
		
		
