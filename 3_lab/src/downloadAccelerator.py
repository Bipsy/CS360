import argparse
import os
import requests
import threading

class Downloader:

	def __init__(self):
		self.args = None
		self.parse_arguments()

	def parse_arguments(self):
	 	''' This function simply parses the command line arguments. It uses a single thread by default, but more threads can be requested. Currently, it assumes that the url given to it is correct. I am 	looking for a way to have argparse verify the structure of the url'''
		parser = argparse.ArgumentParser(prog='Mass Downloader', description='A simple script that downloads a single file using parallel get requests', add_help=True)
		parser.add_argument('-n', type=int, action='store', help='Specify the number of threads to use for downloading file', default=1)
		parser.add_argument('url', type=str, action='store', help='Specify the url from which to download file')
		args = parser.parse_args()
		self.thread_number = args.n
		self.url = args.url
		self.download(args.url)
		
	def download(self, url):
		print 'Sending head request %s' % url
		response = requests.head(url)
		if response.status_code == requests.codes.ok:
			print response.headers.get('content-length')
			size = int(response.headers.get('content-length'))
			threads = []
			chunk = size / self.thread_number
			for thread in range(0, self.thread_number):
				start = chunk * thread
				if thread == self.thread_number-1:
					end = size-1
				else:
					end = (chunk * (thread+1)) - 1
				print "(start: %s and end: %s)" % (start, end)
				t = DownloadThread(url, start, end)
				threads.append(t)
			for thread in threads:
				thread.start()
			with open('file.txt', 'wb') as f:				
				for thread in threads:
					thread.join()
					f.write(thread.response.content);
					print 'Download Complete...'								
		else:
			print 'Error: ' + str(response.status_code)
			
class DownloadThread(threading.Thread):
	def __init__(self, url, beginning, end):
		threading.Thread.__init__(self)
		self.url = url
		self.beginning = beginning
		self.end = end
	def run(self):
		custom_header = {'Range':"bytes=%s-%s" % (self.beginning, self.end)}
		print custom_header
		response = requests.get(self.url, stream=True, headers=custom_header)
		self.response = response
			
if __name__ == '__main__':
	d = Downloader()	
		
		
		
