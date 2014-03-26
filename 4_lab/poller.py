import select
import socket
import sys
import errno
import os.path
import time
import traceback

class Poller:
	""" Polling server """
	def __init__(self, port):
		self.host = ""
		self.port = port
		self.open_socket()
		self.clients = {}
		self.client_times = {}
		self.cache = {}
		self.size = 1024
		self.hosts = {}
		self.media = {}
		self.timeout = 1
		self.status_messages = {200: 'OK', 400: 'Bad Request', 403: 'Forbidden', 404: 'Not Found', 500: 'Internal Server Error', 501: 'Not Implemented'}
		
	def config(self):
		with open('web.conf') as f:
			lines = f.readlines()
			for line in lines:
				#print line.strip()
				words = line.split()
				for word in words:
					word.strip()
				if len(words) < 3:
					#print "Configuration line was too short"
					continue
				#print words[0]	
				if words[0] != 'host' and words[0] != 'media' and words[0] != 'parameter':
					continue
				if words[0] == 'host':
					print "Found a host"
					word = words[2]
					if word[0] != '/':
						self.hosts[words[1]] = os.getcwd() + '/' + word
					else:
						self.hosts[words[1]] = words[2]
				elif words[0] == 'media':
					self.media[words[1]] = words[2]
				elif words[0] == 'parameter':
					self.timeout = int(words[2])
				else:
					print words[0]
					print "Configuration line didn't match any know type"
		#for host in self.hosts:
		#	print host
		
	def open_socket(self):
		""" Setup the socket for incoming clients """
		try:
			self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.server.bind((self.host, self.port))
			self.server.listen(5)
			self.server.setblocking(0)
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
		
		""" Congigure the server """
		self.config()
		
		while True:
			current_time = lambda: int(round(time.time()))
			try:
				#print "Getting file active sockets..."
				first_time = current_time()
				fds = self.poller.poll(timeout=1)
				for (fd, event) in fds:
					if fd != self.server.fileno():
						self.client_times[fd] = first_time
				second_time = current_time()
				idle_sockets = []
				for fd in self.client_times:
					if second_time - self.client_times[fd] > self.timeout:
						idle_sockets.append(fd)
				for fd in idle_sockets:
					self.cleanup(fd)
				#print "Finished getting sockets..."
			except:
				print traceback.format_exc()
				sys.exit()
			for (fd, event) in fds:
				if event & (select.POLLHUP | select.POLLERR):
					self.handleError(fd)
					continue
				if fd == self.server.fileno():
					self.handleServer()
					continue
				result = self.handleClient(fd)
				
	def handleError(self, fd):
		if fd == self.server.fileno():
			self.poller.unregister(fd)
			self.server.close()
			self.open_socket()
			self.poller.register(self.server, self.pollmask)
		else:
			self.cleanup(fd)
			
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
			self.client_times[client.fileno()] = int(round(time.time()))
		
	def handleClient(self, fd):
		#print "Handling client"
		while True:
			try:
				data = self.clients[fd].recv(self.size)
				self.cache[fd] += data
				end_index = self.cache[fd].find("\r\n\r\n")
				if end_index != -1:
					cached_message = self.cache[fd]
					self.handleHttpRequest(fd, cached_message[:end_index+4])
					self.cache[fd] = ""
					break;
				if not data:
					break
			except socket.error, (value, message):
				if data == 'EAGAIN' or data == 'EWOULDBLOCK':
					self.cleanup(fd)
					break
				print traceback.format_exc()
				sys.exit()
		#print "Finished Handling Client..."
			
	def handleHttpRequest(self, fd, message):
		print message
		""" We will handle the http request with the following steps:
			1. Parse and check first line for proper method
				a. Method must be GET
				b. URL must exist
				c. Version must be HTTP/1.1
			2. Parse headers and discard incorrect headers
				a. Determine host header
			3. Retrieve requested object
			4. Build response and send response
		"""
			
		#1	-- Need to check if request line is valid
		lines = message.splitlines()
		first_line = lines[0].split()
		#print first_line[1]
		if len(first_line) != 3:
			self.handleHttpResponse(fd, 400, "")
			self.cleanup(fd)
			return
		elif first_line[0] != 'GET':
			self.handleHttpResponse(fd, 501, "", "", "")
			self.cleanup(fd)
			return
		
		#2  -- Need to parse headers and determine host header	
		header_lines = lines[1:]
		headers = {}
		host_path = self.hosts['default']
		for line in header_lines:
			header = line.split(':')
			if len(header) < 2:
				continue
			if header[0] == 'Host':
				for host in self.hosts:
					if header[1].strip() == host:
						host_path = self.hosts[header[1].strip()]
			else:
				headers[header[0]] = header[1]
		#print headers
		
		#3 & #1.b
		url = first_line[1]
		if url == '/':
			url = '/index.html'
		abs_path = host_path + url
		if os.path.isfile(abs_path) == False:
			#print abs_path
			self.handleHttpResponse(fd, 404, "", "", "")
			return
		try:
			with open(abs_path, 'rb') as f:
				file_name, file_extension = os.path.splitext(abs_path)
				self.handleHttpResponse(fd, 200, f.read(), file_name, file_extension)
				return
		except IOError:
			file_name, file_extension = os.path.splitext(abs_path)
			self.handleHttpResponse(fd, 403, "", file_name, file_extension)
			return 
			
			
	def handleHttpResponse(self, fd, status_code, content, file_name, file_extension):
		response = "HTTP/1.1 " + str(status_code) + " " + self.status_messages[status_code] + "\r\n"
		if status_code == 200:
			response += "Content-Type: " + self.media[file_extension.strip()[1:]] + "\r\n"
			gmt = time.gmtime(os.path.getmtime(file_name+file_extension))
			format = '%a, %d %b %Y %H:%M:%S GMT'
			time_string = time.strftime(format, gmt)
			response += "Last-Modified: " + time_string + "\r\n"
		else:
			response += "Content-Type: text/html\r\n"
			content = "<!DOCTYPE html><html><head></head><body></body></html>"
		response += "Server: Python Server\r\n"
		response += "Content-Length: " + str(len(content)) + "\r\n"
		from  email.utils import formatdate
		response += "Date: " + formatdate(timeval=None, localtime=False, usegmt=True) + "\r\n\r\n"
		print response
		response += content
		#print response
		#print "Sending Response...
		sent = self.clients[fd].send(response)
		while True:
			try:
				if sent < len(content):
					sent += self.clients[fd].send(response[sent:])
				else:
					break;
			except socket.error, (errno, string):
				if errno == 11:
					continue
				else:
					print traceback.format_exc()
					sys.exit()
						
		#print "Finished Sending Response..."
		return
			
	def cleanup(self, fd):
		self.poller.unregister(fd)
		self.clients[fd].close()
		del self.clients[fd]
		del self.cache[fd]
		del self.client_times[fd]
		return

		
		
		
		
		
